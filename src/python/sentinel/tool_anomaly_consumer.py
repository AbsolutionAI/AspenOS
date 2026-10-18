"""
Live tool-audit anomaly consumer (F-015 / ASP-687 — wiring the ASP-379 detector).

Subscribes to the ADR-0007 tool-audit subject ``aspen.sentinel.audit.event``,
feeds each event through :class:`ToolAnomalyDetector.feed`, and publishes every
:class:`~sentinel.tool_anomaly.Finding` to ``aspen.sentinel.tools.anomaly`` so
ops can **page on R1 (high)** and template the rest (R2–R4).

Write topology (mirrors :mod:`sentinel.audit` and :mod:`sentinel.fleet_overview`):

* **JSONL journal (always)** — append + flush + fsync at
  ``/var/lib/aspen/sentinel/tool-anomaly.jsonl``. Findings are durable even
  fully offline.
* **JetStream (best-effort)** — the same finding envelope is published to
  ``aspen.sentinel.tools.anomaly`` when a broker is reachable, with
  ``Nats-Msg-Id: finding_id`` for idempotent delivery.

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

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

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


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, ""))
    except (TypeError, ValueError):
        return default


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
        max_age_seconds: Stream retention window (default 30 days).
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

        self._nc: Any = None
        self._js: Any = None
        self._connected = False
        self._subs: List[Any] = []
        self._findings_emitted = 0

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
        try:
            import nats

            self._nc = await nats.connect(
                self._nats_url,
                max_reconnect_attempts=3,
                reconnect_time_wait=2,
                name="aspen-sentinel-tool-anomaly",
                ping_interval=20,
                max_outstanding_pings=5,
                connect_timeout=5,
            )
            self._connected = True
            self._js = self._nc.jetstream()
            await self._ensure_stream()
            await self._subscribe()
            logger.info(
                "Tool-anomaly consumer subscribed to %s at %s",
                SUBJECT_AUDIT_EVENT,
                self._nats_url,
            )
            return True
        except Exception as exc:  # pragma: no cover - broker-dependent
            self._connected = False
            self._nc = None
            logger.warning(
                "NATS unavailable (%s) — anomaly consumer offline", exc
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

    async def _ensure_stream(self) -> None:
        """Idempotently create the durable sentinel stream."""
        if self._js is None:
            return
        try:
            await self._js.add_stream(
                name=self._stream,
                subjects=self._stream_subjects,
                storage="file",
                max_age=self._max_age_seconds,
                duplicate_window=600,
            )
        except Exception as exc:
            logger.debug(
                "Stream %s may already exist (%s) — continuing", self._stream, exc
            )

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
        except Exception:  # noqa: BLE001 - fail-open contract
            logger.debug("Anomaly consumer swallowed event error", exc_info=True)

    # ---- ingestion -------------------------------------------------------

    async def handle_event(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Feed one audit event to the detector and emit any findings.

        Returns the emitted finding envelopes (JSON-ready dicts). Fail-open:
        malformed input yields ``[]`` and never raises.
        """
        try:
            findings = self._detector.feed(event)
        except Exception:  # noqa: BLE001 - detector is fail-open, belt-and-braces
            logger.debug("Detector raised on event — ignored", exc_info=True)
            return []
        emitted: List[Dict[str, Any]] = []
        for finding in findings:
            emitted.append(await self._emit_finding(finding))
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
            emitted.append(await self._emit_finding(finding))
        return emitted

    # ---- emit ------------------------------------------------------------

    def _envelope(self, finding: Finding) -> Dict[str, Any]:
        payload = finding.to_dict()
        payload["finding_id"] = uuid.uuid4().hex
        payload["ts"] = utc_now()
        payload["source"] = "sentinel.tool_anomaly_consumer"
        payload["notify"] = self._is_page(str(finding.severity))
        return payload

    def _append_journal(self, payload: Dict[str, Any]) -> None:
        self._anomaly_log_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False, default=str) + "\n"
        with open(self._anomaly_log_path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    async def _emit_finding(self, finding: Finding) -> Dict[str, Any]:
        """Journal a finding (always) then mirror it to JetStream (best-effort)."""
        payload = self._envelope(finding)
        self._append_journal(payload)
        self._findings_emitted += 1
        if self.is_online and self._js is not None:
            body = json.dumps(payload, ensure_ascii=False, default=str).encode()
            try:
                await self._js.publish(
                    self._subject,
                    body,
                    stream=self._stream,
                    headers={"Nats-Msg-Id": payload["finding_id"]},
                )
                logger.debug(
                    "Finding %s (%s) published to %s",
                    payload["finding_id"],
                    finding.rule,
                    self._subject,
                )
            except Exception as exc:  # noqa: BLE001 - journal already has it
                logger.warning(
                    "JetStream publish failed for finding %s: %s",
                    payload["finding_id"],
                    exc,
                )
        return payload

    def tail(self, n: int = 20) -> List[Dict[str, Any]]:
        """Most recent ``n`` findings from the journal (newest first)."""
        path = self._anomaly_log_path
        if not path.exists():
            return []
        findings: List[Dict[str, Any]] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            return []
        return list(reversed(findings[-max(0, n):]))
