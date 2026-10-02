"""
Aspen Sentinel tool-anomaly consumer — live wiring for ASP-379 (ADR-0007).

Closes the deferral recorded in ``docs/solutions/asp-379-tool-anomaly.md``:
``ToolAnomalyDetector`` shipped as a pure library + offline CLI, so nothing in
the running system ever called ``feed()``. This module is the missing edge:

    aspen.sentinel.audit.event  ──▶  ToolAnomalyDetector.feed()
                                            │
                                            ▼
                              aspen.sentinel.tools.anomaly

Findings are **fail-open and log-only**, exactly as the detector is. Nothing here
can block a tool call, deny an action, or alter a verdict — the worst outcome is a
finding nobody reads.

Write topology (mirrors :mod:`sentinel.audit` and :mod:`sentinel.fleet_overview`):

* **JSONL journal (always)** — append + flush + fsync at
  ``/var/lib/aspen/sentinel/anomaly.jsonl``. Findings survive a broker outage.
* **JetStream (best-effort)** — the same finding is published to
  ``aspen.sentinel.tools.anomaly`` with ``Nats-Msg-Id: finding_id`` when a broker
  is reachable. The id is derived from the incident content, so a replayed
  finding is deduplicated by the stream rather than paging twice.

**Delivery is at-most-once.** This subscribes with ``nc.subscribe`` like
:class:`sentinel.consumer.AuditEventConsumer` and
:class:`sentinel.fleet_overview.FleetOverviewProducer`, rather than a durable
JetStream pull consumer. A restart therefore loses whatever arrived while the
process was down. That is a deliberate trade, recorded in
``docs/plans/ASP-687.md``: at-most-once cannot half-apply a finding or storm the
page queue on redelivery, and a durable consumer cannot be verified without a
live broker. The audit journal is the replay source if that trade needs
revisiting.

Usage (async)::

    consumer = AnomalyConsumer(nats_url="nats://localhost:4222")
    await consumer.start()          # subscribe (best-effort; False = offline)
    await consumer.close()

One-shot over an existing journal, no broker::

    findings = AnomalyConsumer(anomaly_log="/tmp/anomaly.jsonl").scan(events)

CLI: ``scripts/sentinel-tool-anomaly.py`` (daemon / scan / tail / check).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sentinel.tool_anomaly import Finding, ToolAnomalyDetector

logger = logging.getLogger("sentinel.anomaly_consumer")

# ADR-0007 subject: audit events in, findings out.
SUBJECT_AUDIT_EVENT = "aspen.sentinel.audit.event"
SUBJECT_TOOLS_ANOMALY = "aspen.sentinel.tools.anomaly"

# Same stream/subjects as sentinel.audit — `aspen.sentinel.>` already covers the
# new subject, so the generated ACLs need no change (verified, not assumed).
DEFAULT_STREAM_NAME = "ASPEN_SENTINEL"
DEFAULT_STREAM_SUBJECTS = ["aspen.sentinel.>"]
DEFAULT_MAX_AGE_SECONDS = 30 * 24 * 3600

DEFAULT_ANOMALY_LOG = "/var/lib/aspen/sentinel/anomaly.jsonl"
DEFAULT_TAIL = 20


def utc_now() -> str:
    """UTC timestamp in the ADR-0007 ISO-8601 form (``...Z``)."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def finding_id(finding: Finding, event_id: str = "") -> str:
    """Content-derived id for a finding, used as the ``Nats-Msg-Id``.

    Derived from the incident rather than random so that replaying the same
    finding after a restart or a journal re-scan collapses onto one JetStream
    message instead of paging again. ``event_id`` (the correlated audit event)
    separates two otherwise-identical findings from the same actor.
    """
    digest = hashlib.sha256(
        json.dumps(
            {
                "rule": finding.rule,
                "actor": finding.actor,
                "message": finding.message,
                "window_s": finding.window_s,
                "events": [
                    str(e.get("event_id") or "") for e in finding.events
                ],
                "event_id": event_id,
            },
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    return digest[:32]


def build_finding_envelope(
    finding: Finding, *, event_id: str = "", source: str = "sentinel-tool-anomaly"
) -> Dict[str, Any]:
    """Wrap a :class:`Finding` in the ADR-0007 envelope."""
    payload = finding.to_dict()
    payload.update(
        {
            "finding_id": finding_id(finding, event_id),
            "ts": utc_now(),
            "source": source,
            "event_id": event_id or uuid.uuid4().hex,
        }
    )
    return payload


class AnomalyConsumer:
    """Audit events in → behavioral findings out, fail-open end to end.

    Args:
        nats_url: Broker URL (``None``/empty = journal-only). Falls back to
            ``ASPEN_NATS_URL``.
        anomaly_log: JSONL findings journal. Defaults to
            ``ASPEN_ANOMALY_LOG`` or ``/var/lib/aspen/sentinel/anomaly.jsonl``.
        audit_log: Audit JSONL used by the offline ``scan()`` path. Defaults to
            ``ASPEN_AUDIT_LOG`` or ``/var/lib/aspen/sentinel/audit.jsonl``.
        stream: JetStream stream name. Defaults to ``ASPEN_AUDIT_STREAM`` or
            ``ASPEN_SENTINEL``.
        stream_subjects: Subjects bound to the stream. Defaults to
            ``aspen.sentinel.>``.
        max_age_seconds: Stream retention (default 30 days).
        detector: Pre-built detector. Mostly for tests; defaults to a
            ``ToolAnomalyDetector()`` with the standard thresholds.
    """

    def __init__(
        self,
        nats_url: Optional[str] = None,
        anomaly_log: Optional[str] = None,
        audit_log: Optional[str] = None,
        stream: Optional[str] = None,
        stream_subjects: Optional[Iterable[str]] = None,
        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
        detector: Optional[ToolAnomalyDetector] = None,
    ) -> None:
        self._nats_url = nats_url or os.environ.get("ASPEN_NATS_URL", "")
        self._log_path = Path(
            anomaly_log
            or os.environ.get("ASPEN_ANOMALY_LOG", "")
            or DEFAULT_ANOMALY_LOG
        ).expanduser()
        self._audit_log_path = Path(
            audit_log
            or os.environ.get("ASPEN_AUDIT_LOG", "")
            or "/var/lib/aspen/sentinel/audit.jsonl"
        ).expanduser()
        self._stream = (
            stream or os.environ.get("ASPEN_AUDIT_STREAM", "") or DEFAULT_STREAM_NAME
        )
        self._stream_subjects = (
            list(stream_subjects)
            if stream_subjects
            else list(DEFAULT_STREAM_SUBJECTS)
        )
        self._max_age_seconds = max_age_seconds
        self._detector = detector or ToolAnomalyDetector()

        self._nc: Any = None
        self._js: Any = None
        self._connected = False
        self._subs: List[Any] = []

        self._events_seen = 0
        self._events_rejected = 0
        self._findings_emitted = 0
        self._findings_published = 0

    # ---- lifecycle -------------------------------------------------------

    @property
    def is_online(self) -> bool:
        return self._connected and self._nc is not None and self._nc.is_connected

    @property
    def anomaly_log_path(self) -> Path:
        return self._log_path

    @property
    def detector(self) -> ToolAnomalyDetector:
        return self._detector

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "events_seen": self._events_seen,
            "events_rejected": self._events_rejected,
            "findings_emitted": self._findings_emitted,
            "findings_published": self._findings_published,
        }

    async def start(self) -> bool:
        """Connect and subscribe (best-effort). False means offline.

        Never raises: this consumer is a detector on the audit path, and a
        broken detector must not take down audit publication.
        """
        if not self._nats_url:
            logger.info("No NATS URL — anomaly consumer in journal-only mode")
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
                "Anomaly consumer subscribed to %s at %s",
                SUBJECT_AUDIT_EVENT,
                self._nats_url,
            )
            return True
        except Exception as exc:  # pragma: no cover - broker-dependent
            self._connected = False
            logger.warning(
                "NATS unavailable (%s) — anomaly consumer offline", exc
            )
            self._nc = None
            return False

    async def close(self) -> None:
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
            logger.debug("Stream %s may already exist (%s) — continuing", self._stream, exc)

    async def _subscribe(self) -> None:
        if self._nc is None or not self._nc.is_connected:
            return
        self._subs = [
            await self._nc.subscribe(SUBJECT_AUDIT_EVENT, cb=self._on_audit)
        ]

    # ---- ingest ----------------------------------------------------------

    async def _on_audit(self, msg: Any) -> None:
        """NATS callback. Any failure here is counted, never raised."""
        try:
            event = json.loads(msg.data.decode())
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            self._events_rejected += 1
            logger.debug("Ignoring non-JSON message on %s", getattr(msg, "subject", "?"))
            return
        if not isinstance(event, dict):
            self._events_rejected += 1
            return
        await self.ingest(event)

    async def ingest(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Feed one audit event through the detector; journal + publish findings.

        Returns the envelopes written (empty when the event trips nothing). This
        is the offline entry point too — ``ingest()`` is the whole feature, and
        the subscription is only a way to feed it.
        """
        try:
            findings = self._detector.feed(event)
        except Exception as exc:  # noqa: BLE001 - fail-open by contract
            self._events_rejected += 1
            logger.warning("Detector raised on event (ignored): %s", exc)
            return []
        self._events_seen += 1

        envelopes: List[Dict[str, Any]] = []
        for finding in findings:
            try:
                envelope = build_finding_envelope(
                    finding, event_id=str(event.get("event_id") or "")
                )
                self._append_journal(envelope)
                if self.is_online and self._js is not None:
                    await self._publish_js(envelope)
                self._findings_emitted += 1
                envelopes.append(envelope)
            except Exception as exc:  # noqa: BLE001 - fail-open by contract
                logger.warning("Could not record anomaly finding: %s", exc)
        return envelopes

    def scan(self, events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Offline batch: run ``events`` through the detector, journal findings.

        No broker involved. Uses ``ToolAnomalyDetector.scan()``, which sorts by
        timestamp first, so an unordered journal yields the same findings the
        live path would have produced.
        """
        events = [e for e in events if isinstance(e, dict)]
        findings = self._detector.scan(events)
        self._events_seen += len(events)
        envelopes = []
        for finding in findings:
            try:
                envelope = build_finding_envelope(finding)
                self._append_journal(envelope)
                self._findings_emitted += 1
                envelopes.append(envelope)
            except Exception as exc:  # noqa: BLE001 - fail-open by contract
                logger.warning("Could not record anomaly finding: %s", exc)
        return envelopes

    def scan_journal(self, limit: int = 100000) -> List[Dict[str, Any]]:
        """Offline batch over the audit JSONL journal."""
        events = self._read_events(self._audit_log_path)
        if limit and len(events) > limit:
            events = events[-limit:]
        return self.scan(events)

    # ---- journal ---------------------------------------------------------

    def _append_journal(self, envelope: Dict[str, Any]) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(envelope, ensure_ascii=False, default=str) + "\n"
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def _read_events(self, path: Path) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return []
        events: List[Dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed line in %s", path)
                continue
            if isinstance(parsed, dict):
                events.append(parsed)
        return events

    def findings(self) -> List[Dict[str, Any]]:
        """All findings from the journal, oldest first."""
        return self._read_events(self._log_path)

    def tail(self, n: int = DEFAULT_TAIL) -> List[Dict[str, Any]]:
        """Most recent ``n`` findings, newest first."""
        if n <= 0:
            return []
        events = self._read_events(self._log_path)
        return list(reversed(events[-n:]))

    # ---- publish ---------------------------------------------------------

    async def _publish_js(self, envelope: Dict[str, Any]) -> None:
        try:
            await self._js.publish(
                SUBJECT_TOOLS_ANOMALY,
                json.dumps(envelope, ensure_ascii=False, default=str).encode("utf-8"),
                stream=self._stream,
                headers={"Nats-Msg-Id": envelope["finding_id"]},
            )
            self._findings_published += 1
        except Exception as exc:
            logger.warning(
                "JetStream publish failed for finding %s: %s",
                envelope.get("finding_id"),
                exc,
            )

    # ---- reporting -------------------------------------------------------

    async def check(self) -> Dict[str, Any]:
        """Journal + stream + counters. Safe with or without a broker."""
        events = self._read_events(self._log_path)
        by_severity: Dict[str, int] = {}
        by_rule: Dict[str, int] = {}
        for finding in events:
            sev = str(finding.get("severity") or "unknown")
            rule = str(finding.get("rule") or "unknown")
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_rule[rule] = by_rule.get(rule, 0) + 1
        report: Dict[str, Any] = {
            "journal": str(self._log_path),
            "findings_on_disk": len(events),
            "by_severity": by_severity,
            "by_rule": by_rule,
            "first_ts": events[0].get("ts") if events else None,
            "last_ts": events[-1].get("ts") if events else None,
            "source_subject": SUBJECT_AUDIT_EVENT,
            "findings_subject": SUBJECT_TOOLS_ANOMALY,
            "stream": self._stream,
            "online": self.is_online,
        }
        report.update(self.stats)
        if self.is_online and self._js is not None:
            try:
                info = await self._js.stream_info(self._stream)
                report["jetstream"] = {
                    "messages": int(info.state.messages),
                    "bytes": int(info.state.bytes),
                }
            except Exception as exc:
                report["jetstream"] = {"error": str(exc)}
        return report