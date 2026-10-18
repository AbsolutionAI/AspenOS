"""
Live tool-audit anomaly consumer (F-015 / ASP-687 — wiring the ASP-379 detector).

Subscribes to the ADR-0007 tool-audit subject ``aspen.sentinel.audit.event``,
feeds each event through :class:`ToolAnomalyDetector.feed`, and publishes every
:class:`~sentinel.tool_anomaly.Finding` to ``aspen.sentinel.tools.anomaly`` so
ops can **page on R1 (high)** and template the rest (R2–R4).

Write topology (mirrors :mod:`sentinel.audit` and :mod:`sentinel.fleet_overview`):

* **JSONL journal (always)** — append + flush + fsync at
  ``/var/lib/aspen/sentinel/tool-anomaly.jsonl``. The write runs in a worker
  thread (never on the event loop) so a slow disk cannot stall the NATS
  subscription. Findings are durable even fully offline.
* **JetStream (best-effort)** — the same finding envelope is published to
  ``aspen.sentinel.tools.anomaly`` when a broker is reachable, with
  ``Nats-Msg-Id: finding_id`` for idempotent delivery. ``finding_id`` is
  deterministic (hash of rule, actor and source event ids), so a replay or a
  repeated rule hit dedupes instead of paging twice.

Hardening (ASP-780, PR #76 follow-ups):

* Connect uses the shared credential/TLS helper (``agents/nats_connect.py``:
  user/pass, token, nkey seed, ``STARSHIP_NATS_TLS`` + CA/cert/key) plus an
  optional JWT creds file (``ASPEN_NATS_CREDS``). URLs are logged redacted.
* The consumer **does not create** the ``ASPEN_SENTINEL`` stream (stream
  settings belong to the operator / ``sentinel.audit`` publisher). It checks
  the stream exists and binds the finding subject; if not, it logs an ERROR
  and runs journal-only. ``create_stream=True`` is for dev/test brokers only.

The threat model (``docs/SECURITY_THREAT_MODEL_v2.2.md`` §8 P1 #14) names the
finding subject ``sentinel.tools.anomaly``; that is the short form under the
``aspen.sentinel.`` namespace used by the durable ``ASPEN_SENTINEL`` stream
(which binds ``aspen.sentinel.>``), so the concrete subject here is
``aspen.sentinel.tools.anomaly`` (override with ``ASPEN_TOOLS_ANOMALY_SUBJECT``).

Fail-open end to end: the detector never raises on malformed input and never
returns a blocking verdict; a bad message or a failed publish is logged and
swallowed, so this consumer can never block ``propose_act``.

Usage (async)::

    consumer = ToolAnomalyConsumer(nats_url="nats://localhost:4222")
    await consumer.start()
    ...  # live findings paginate via the subscription
    await consumer.close()

Offline replay::

    consumer = ToolAnomalyConsumer(anomaly_log=...)
    await consumer.ingest_journal()   # scan the audit JSONL, emit findings

CLI: ``scripts/tool-anomaly.py watch [--once]``.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
from collections import OrderedDict, deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sentinel.audit import (
    DEFAULT_STREAM_NAME,
    DEFAULT_STREAM_SUBJECTS,
    SUBJECT_AUDIT_EVENT,
    utc_now,
)
from sentinel.tool_anomaly import Finding, ToolAnomalyDetector, read_jsonl

logger = logging.getLogger("sentinel.tool_anomaly_consumer")

# Finding subject (short form in the threat model: sentinel.tools.anomaly).
SUBJECT_TOOL_ANOMALY = "aspen.sentinel.tools.anomaly"

DEFAULT_ANOMALY_LOG = "/var/lib/aspen/sentinel/tool-anomaly.jsonl"

# Findings at or above this severity are paging signals (notify: true).
DEFAULT_PAGE_SEVERITY = "high"
_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}


# Upper bound on the initial broker connect (seconds).
_CONNECT_DEADLINE_S = 15.0

# How many recent finding ids are remembered for in-process dedupe.
_SEEN_IDS_CAP = 4096


def _subject_matches(pattern: str, subject: str) -> bool:
    """NATS subject wildcard match (``*`` = one token, ``>`` = the rest)."""
    p_tokens = pattern.split(".")
    s_tokens = subject.split(".")
    for i, tok in enumerate(p_tokens):
        if tok == ">":
            return len(s_tokens) > i
        if i >= len(s_tokens):
            return False
        if tok != "*" and tok != s_tokens[i]:
            return False
    return len(p_tokens) == len(s_tokens)


def _event_key(event: Any) -> str:
    """Stable identity for a source event: its ``event_id`` or a content hash."""
    if isinstance(event, dict):
        eid = event.get("event_id") or event.get("id")
        if eid:
            return str(eid)
    try:
        blob = json.dumps(event, sort_keys=True, default=str)
    except (TypeError, ValueError):
        blob = repr(event)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def finding_id_for(finding: Finding) -> str:
    """Deterministic 32-hex finding id: hash of (rule, actor, source event ids).

    The same rule firing on the same events always yields the same id, so the
    JetStream ``Nats-Msg-Id`` dedupe and the in-process seen-set suppress
    duplicates on replay or on a repeated rule hit.
    """
    keys = sorted(_event_key(e) for e in (finding.events or []))
    material = "\x1f".join([str(finding.rule), str(finding.actor), *keys])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _load_nats_helper() -> Any:
    """Import the shared ``nats_connect`` helper (``agents/``), or ``None``."""
    try:
        import nats_connect  # type: ignore[import-not-found]

        return nats_connect
    except ImportError:
        pass
    agents_dir = Path(__file__).resolve().parents[3] / "agents"
    if (agents_dir / "nats_connect.py").is_file():
        sys.path.insert(0, str(agents_dir))
        try:
            import nats_connect  # type: ignore[import-not-found]

            return nats_connect
        except ImportError:  # pragma: no cover - defensive
            return None
    return None


def nats_connect_options(url: str) -> Tuple[str, Dict[str, Any], str]:
    """Resolve (url, extra nats.connect kwargs, redacted url) for ``url``.

    Reuses ``agents/nats_connect.py`` (creds in env, nkey seed, TLS context)
    so this consumer is exactly as secure as the rest of the fleet bus, and
    adds ``ASPEN_NATS_CREDS`` (JWT ``.creds`` file) when set.
    """
    helper = _load_nats_helper()
    kwargs: Dict[str, Any] = {}
    final_url = url
    redacted = url
    if helper is not None:
        final_url = helper.build_nats_url(url)
        kwargs.update(helper.connect_kwargs())
        redacted = helper.safe_url(url)
        if kwargs.get("nkeys_seed_str") and "@" in final_url.split("://", 1)[-1]:
            # nkey auth wins; drop URL userinfo to avoid conflicting auth.
            scheme, rest = final_url.split("://", 1)
            final_url = f"{scheme}://{rest.rsplit('@', 1)[1]}"
    else:
        logger.warning(
            "nats_connect helper not importable — connecting with the bare URL "
            "(no env creds/TLS)"
        )
        if "@" in url.split("://", 1)[-1]:
            scheme, rest = url.split("://", 1)
            redacted = f"{scheme}://***@{rest.rsplit('@', 1)[1]}"
    creds = os.environ.get("ASPEN_NATS_CREDS", "").strip()
    if creds:
        if os.path.isfile(creds):
            kwargs["user_credentials"] = creds
        else:
            logger.warning("ASPEN_NATS_CREDS=%s does not exist — ignored", creds)
    has_auth = (
        "@" in final_url.split("://", 1)[-1]
        or "nkeys_seed_str" in kwargs
        or "user_credentials" in kwargs
    )
    has_tls = final_url.startswith("tls://") or "tls" in kwargs
    host = final_url.split("://", 1)[-1].rsplit("@", 1)[-1]
    local = host.startswith(("127.", "localhost", "[::1]"))
    if not local and not (has_auth and has_tls):
        logger.warning(
            "Tool-anomaly consumer connecting to %s without %s — set "
            "STARSHIP_NATS_TLS / creds (H-024)",
            redacted,
            " and ".join(
                x for x, ok in (("auth", has_auth), ("TLS", has_tls)) if not ok
            ),
        )
    return final_url, kwargs, redacted


class ToolAnomalyConsumer:
    """Feed the live audit stream through the detector and emit findings.

    Args:
        nats_url: Broker URL (``None``/empty = offline). Falls back to
            ``ASPEN_NATS_URL``.
        audit_log: Path to the audit JSONL journal used by
            :meth:`ingest_journal`. Defaults to ``ASPEN_AUDIT_LOG`` or
            ``/var/lib/aspen/sentinel/audit.jsonl``.
        anomaly_log: Path to the findings JSONL journal. Defaults to
            ``ASPEN_ANOMALY_LOG`` or
            ``/var/lib/aspen/sentinel/tool-anomaly.jsonl``.
        subject: Finding subject. Defaults to ``ASPEN_TOOLS_ANOMALY_SUBJECT``
            or ``aspen.sentinel.tools.anomaly``.
        stream: JetStream stream name. Defaults to ``ASPEN_AUDIT_STREAM`` or
            ``ASPEN_SENTINEL``.
        stream_subjects: Subjects bound to the stream (default
            ``aspen.sentinel.>``).
        detector: Optional pre-built :class:`ToolAnomalyDetector`.
        window_s: Detector window seconds when building the default detector.
        page_severity: Severity at/above which ``notify`` is true (default
            ``high``).
        max_age_seconds: Stream retention window, only used when
            ``create_stream`` is true (default 30 days).
        create_stream: Dev/test only — create the stream when it is missing.
            Production leaves stream settings to the operator; a missing or
            misconfigured stream is logged at ERROR and the consumer runs
            journal-only.
    """

    def __init__(
        self,
        *,
        nats_url: Optional[str] = None,
        audit_log: Optional[str] = None,
        anomaly_log: Optional[str] = None,
        subject: Optional[str] = None,
        stream: Optional[str] = None,
        stream_subjects: Optional[Iterable[str]] = None,
        detector: Optional[ToolAnomalyDetector] = None,
        window_s: float = 120.0,
        page_severity: str = DEFAULT_PAGE_SEVERITY,
        max_age_seconds: int = 30 * 24 * 3600,
        create_stream: bool = False,
    ) -> None:
        self._nats_url = nats_url or os.environ.get("ASPEN_NATS_URL", "")
        env_audit = os.environ.get("ASPEN_AUDIT_LOG", "")
        self._audit_log_path = Path(
            audit_log or env_audit or "/var/lib/aspen/sentinel/audit.jsonl"
        ).expanduser()
        env_anomaly = os.environ.get("ASPEN_ANOMALY_LOG", "")
        self._anomaly_log_path = Path(
            anomaly_log or env_anomaly or DEFAULT_ANOMALY_LOG
        ).expanduser()
        self._subject = (
            subject
            or os.environ.get("ASPEN_TOOLS_ANOMALY_SUBJECT", "")
            or SUBJECT_TOOL_ANOMALY
        )
        self._stream = (
            stream
            or os.environ.get("ASPEN_AUDIT_STREAM", "")
            or DEFAULT_STREAM_NAME
        )
        self._stream_subjects = (
            list(stream_subjects)
            if stream_subjects
            else list(DEFAULT_STREAM_SUBJECTS)
        )
        self._detector = detector or ToolAnomalyDetector(window_s=window_s)
        self._page_severity = (page_severity or DEFAULT_PAGE_SEVERITY).lower()
        self._max_age_seconds = max_age_seconds
        self._create_stream = bool(create_stream)

        self._nc: Any = None
        self._js: Any = None
        self._connected = False
        self._stream_ok = False
        self._subs: List[Any] = []
        self._findings_emitted = 0
        self._journal_lock: Optional[asyncio.Lock] = None
        self._seen_ids: OrderedDict[str, None] = OrderedDict()
        self._seen_loaded = False

    # ---- introspection ---------------------------------------------------

    @property
    def is_online(self) -> bool:
        return self._connected and self._nc is not None and self._nc.is_connected

    @property
    def anomaly_log_path(self) -> Path:
        return self._anomaly_log_path

    @property
    def audit_log_path(self) -> Path:
        return self._audit_log_path

    @property
    def subject(self) -> str:
        return self._subject

    @property
    def findings_emitted(self) -> int:
        return self._findings_emitted

    @property
    def stream_ok(self) -> bool:
        """True when the JetStream stream was verified and publishes are on."""
        return self._stream_ok

    def _is_page(self, severity: str) -> bool:
        """True when a finding's severity meets the paging threshold."""
        return (
            _SEVERITY_ORDER.get(severity.lower(), 0)
            >= _SEVERITY_ORDER.get(self._page_severity, 2)
        )

    # ---- lifecycle -------------------------------------------------------

    async def start(self) -> bool:
        """Connect to NATS (best-effort), ensure the stream, subscribe.

        Returns True when the live subscription is active; offline mode returns
        False without raising.
        """
        if not self._nats_url:
            logger.info(
                "No NATS URL configured — anomaly consumer offline (journal only)"
            )
            return False
        url, extra, redacted = nats_connect_options(self._nats_url)
        try:
            import nats

            # Bound the whole initial connect: nats-py can retry a refused
            # TLS/auth handshake for a long time, and start() must not hang.
            self._nc = await asyncio.wait_for(
                nats.connect(
                    url,
                    max_reconnect_attempts=3,
                    reconnect_time_wait=2,
                    name="aspen-sentinel-tool-anomaly",
                    ping_interval=20,
                    max_outstanding_pings=5,
                    connect_timeout=5,
                    allow_reconnect=True,
                    **extra,
                ),
                timeout=_CONNECT_DEADLINE_S,
            )
            self._connected = True
            self._js = self._nc.jetstream()
            await self._ensure_stream()
            await self._subscribe()
            logger.info(
                "Tool-anomaly consumer subscribed to %s at %s (JetStream %s)",
                SUBJECT_AUDIT_EVENT,
                redacted,
                "on" if self._stream_ok else "off — journal only",
            )
            return True
        except Exception as exc:  # pragma: no cover - broker-dependent
            self._connected = False
            self._nc = None
            logger.warning(
                "NATS unavailable at %s (%s) — anomaly consumer offline",
                redacted,
                exc,
            )
            return False

    async def close(self) -> None:
        """Drain NATS and stop the live subscription."""
        for sub in self._subs:
            try:
                await sub.unsubscribe()
            except Exception:  # pragma: no cover - best-effort teardown
                pass
        self._subs = []
        if self._nc is not None:
            try:
                await self._nc.drain()
                await self._nc.close()
            except Exception:  # pragma: no cover - best-effort teardown
                pass
        self._nc = None
        self._js = None
        self._connected = False
        self._stream_ok = False

    async def _ensure_stream(self) -> None:
        """Verify the durable sentinel stream exists and binds our subject.

        The consumer never silently creates the stream: whichever process
        started first would otherwise pick the retention settings. A missing
        or misconfigured stream is an ERROR and turns JetStream publishing off
        (the journal stays authoritative). ``create_stream=True`` restores
        creation for dev/test brokers.
        """
        self._stream_ok = False
        if self._js is None:
            return
        try:
            info = await self._js.stream_info(self._stream)
        except Exception as exc:  # noqa: BLE001 - NotFoundError or broker error
            if self._create_stream:
                try:
                    await self._js.add_stream(
                        name=self._stream,
                        subjects=self._stream_subjects,
                        storage="file",
                        max_age=self._max_age_seconds,
                        duplicate_window=600,
                    )
                    logger.warning(
                        "Created stream %s (create_stream=True, dev/test only)",
                        self._stream,
                    )
                    self._stream_ok = True
                except Exception as add_exc:  # noqa: BLE001 - dev/test path
                    logger.error(
                        "Could not create stream %s: %s — journal only",
                        self._stream,
                        add_exc,
                    )
                return
            logger.error(
                "JetStream stream %s not found (%s) — findings will be journaled "
                "only. Provision the stream (sentinel.audit / ops) and restart.",
                self._stream,
                exc,
            )
            return
        subjects = list(getattr(getattr(info, "config", None), "subjects", None) or [])
        if not any(_subject_matches(pat, self._subject) for pat in subjects):
            logger.error(
                "Stream %s subjects %s do not bind %s — findings will be journaled "
                "only.",
                self._stream,
                subjects,
                self._subject,
            )
            return
        self._stream_ok = True

    async def _subscribe(self) -> None:
        """Subscribe to the ADR-0007 tool-audit subject."""
        if self._nc is None or not self._nc.is_connected:
            return
        self._subs = [
            await self._nc.subscribe(SUBJECT_AUDIT_EVENT, cb=self._on_message)
        ]

    async def _on_message(self, msg: Any) -> None:
        """Subscription callback: decode, feed, emit. Never raises."""
        try:
            event = json.loads(msg.data.decode())
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            logger.debug("Ignoring non-JSON audit message")
            return
        try:
            await self.handle_event(event)
        except Exception as exc:  # noqa: BLE001 - fail-open contract
            logger.warning("Anomaly consumer swallowed event error: %s", exc)

    # ---- ingestion -------------------------------------------------------

    async def handle_event(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Feed one audit event to the detector and emit any findings.

        Returns the emitted finding envelopes (JSON-ready dicts). Fail-open:
        malformed input yields ``[]`` and never raises.
        """
        try:
            findings = self._detector.feed(event)
        except Exception as exc:  # noqa: BLE001 - detector is fail-open, belt-and-braces
            logger.warning("Detector raised on event — ignored: %s", exc)
            return []
        emitted: List[Dict[str, Any]] = []
        for finding in findings:
            payload = await self._emit_finding(finding)
            if payload is not None:
                emitted.append(payload)
        return emitted

    async def ingest_journal(self) -> List[Dict[str, Any]]:
        """Offline replay: scan the audit JSONL and emit the findings.

        Uses the detector's batch :meth:`~sentinel.tool_anomaly.ToolAnomalyDetector.scan`
        so a shuffled/rolled journal yields the same findings. Returns the
        emitted finding envelopes.
        """
        if not self._audit_log_path.exists():
            return []
        events = read_jsonl(str(self._audit_log_path))
        findings = self._detector.scan(events)
        emitted: List[Dict[str, Any]] = []
        for finding in findings:
            payload = await self._emit_finding(finding)
            if payload is not None:
                emitted.append(payload)
        return emitted

    # ---- emit ------------------------------------------------------------

    def _envelope(self, finding: Finding) -> Dict[str, Any]:
        payload = finding.to_dict()
        payload["finding_id"] = finding_id_for(finding)
        payload["ts"] = utc_now()
        payload["source"] = "sentinel.tool_anomaly_consumer"
        payload["notify"] = self._is_page(str(finding.severity))
        return payload

    def _append_journal(self, payload: Dict[str, Any]) -> None:
        """Blocking append + fsync. Called from a worker thread only."""
        self._anomaly_log_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False, default=str) + "\n"
        with open(self._anomaly_log_path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def _remember(self, finding_id: str) -> None:
        self._seen_ids[finding_id] = None
        self._seen_ids.move_to_end(finding_id)
        while len(self._seen_ids) > _SEEN_IDS_CAP:
            self._seen_ids.popitem(last=False)

    def _load_seen_ids(self) -> None:
        """Seed the dedupe set from the journal tail (survives restarts)."""
        self._seen_loaded = True
        for entry in reversed(self.tail(_SEEN_IDS_CAP)):
            fid = entry.get("finding_id")
            if isinstance(fid, str) and fid:
                self._remember(fid)

    async def _write_journal(self, payload: Dict[str, Any]) -> bool:
        """Journal off the event loop, serialized to keep line order."""
        if self._journal_lock is None:
            self._journal_lock = asyncio.Lock()
        try:
            async with self._journal_lock:
                await asyncio.to_thread(self._append_journal, payload)
            return True
        except OSError as exc:
            logger.warning(
                "Journal write failed for finding %s (%s) — publishing anyway",
                payload.get("finding_id"),
                exc,
            )
            return False

    async def _emit_finding(self, finding: Finding) -> Optional[Dict[str, Any]]:
        """Journal a finding (always) then mirror it to JetStream (best-effort).

        Returns ``None`` when the finding is a duplicate of one already
        emitted (same deterministic ``finding_id``).
        """
        payload = self._envelope(finding)
        fid = payload["finding_id"]
        if not self._seen_loaded:
            try:
                await asyncio.to_thread(self._load_seen_ids)
            except Exception as exc:  # noqa: BLE001 - dedupe seed is best-effort
                self._seen_loaded = True
                logger.warning("Could not seed finding dedupe from journal: %s", exc)
        if fid in self._seen_ids:
            logger.debug("Duplicate finding %s (%s) suppressed", fid, finding.rule)
            return None
        self._remember(fid)
        await self._write_journal(payload)
        self._findings_emitted += 1
        if self.is_online and self._js is not None and self._stream_ok:
            body = json.dumps(payload, ensure_ascii=False, default=str).encode()
            try:
                await self._js.publish(
                    self._subject,
                    body,
                    stream=self._stream,
                    headers={"Nats-Msg-Id": fid},
                )
                logger.debug(
                    "Finding %s (%s) published to %s", fid, finding.rule, self._subject
                )
            except Exception as exc:  # noqa: BLE001 - journal already has it
                logger.warning("JetStream publish failed for finding %s: %s", fid, exc)
        return payload

    def tail(self, n: int = 20) -> List[Dict[str, Any]]:
        """Most recent ``n`` findings from the journal (newest first)."""
        path = self._anomaly_log_path
        if not path.exists():
            return []
        n = max(0, int(n))
        if n == 0:
            return []
        findings: deque[Dict[str, Any]] = deque(maxlen=n)
        try:
            # Stream the file; only the last n parsed findings are kept.
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(entry, dict):
                        findings.append(entry)
        except OSError:
            return []
        return list(reversed(findings))
