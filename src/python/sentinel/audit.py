"""
Aspen Sentinel audit event publisher (ADR-0007 / H-015 / ASP-537).

Records agent actions to the durable `aspen.sentinel.audit.event` subject with
the ADR-0007 schema::

    {event_id, actor, action, target, result, ts}

Write topology:

* **JSONL file** — unconditional append-only local write-path (fsync'd). Never
  depends on broker availability, so the audit trail is durable even fully
  offline.
* **JetStream** — best-effort mirror of the same event onto the
  ``aspen.sentinel.audit.event`` subject. Idempotent replay (``Nats-Msg-Id``
  header + local marker file) backfills JSONL into the stream after outages.

Offline contract: a failed/absent broker never drops an event. ``record()``
always writes JSONL; JetStream publish is attempted when a connection exists,
and ``replay_pending()`` closes the gap on reconnect.

Usage (async)::

    publisher = AuditEventPublisher(nats_url="nats://localhost:4222")
    await publisher.start()
    await publisher.record(actor="aspen-sentinel", action="gate.decision",
                           target="plant:chae-cell-01", result="grant")
    await publisher.close()

Sync callers (e.g. the gatekeeper shim's ``log_audit``) use
``publisher.record_sync(...)`` which always writes JSONL and schedules the
JetStream publish when a loop is running.

CLI: ``scripts/sentinel-audit.py`` (emit / tail / query / replay / js-last / check).
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger("sentinel.audit")

# ADR-0007 subject + default durable JetStream stream
SUBJECT_AUDIT_EVENT = "aspen.sentinel.audit.event"
DEFAULT_STREAM_SUBJECTS = ["aspen.sentinel.>"]
DEFAULT_STREAM_NAME = "ASPEN_SENTINEL"
DEFAULT_AUDIT_LOG = "/var/lib/aspen/sentinel/audit.jsonl"

# Required envelope fields (ADR-0007). Extra fields are preserved.
REQUIRED_FIELDS = ("event_id", "actor", "action", "target", "result", "ts")


def utc_now() -> str:
    """UTC timestamp in the ADR-0007 ISO-8601 form (``...Z``)."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_event(
    actor: str,
    action: str,
    target: Optional[str] = None,
    result: Optional[str] = None,
    *,
    event_id: Optional[str] = None,
    ts: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Build an ADR-0007 audit event dict with a complete envelope."""
    event: Dict[str, Any] = {
        "event_id": event_id or uuid.uuid4().hex,
        "actor": actor,
        "action": action,
        "target": target or "",
        "result": result or "ok",
        "ts": ts or utc_now(),
    }
    for key, value in extra.items():
        if key in REQUIRED_FIELDS:
            raise ValueError(f"cannot override reserved audit field '{key}'")
        event[key] = value
    return event


class AuditEventPublisher:
    """Append JSONL + best-effort JetStream publisher for audit events.

    Args:
        nats_url: Broker URL (``None``/empty = offline-only until record() sees
            a live connection). Falls back to ``ASPEN_NATS_URL``.
        audit_log: Path to the JSONL journal. Defaults to ``ASPEN_AUDIT_LOG``
            or ``/var/lib/aspen/sentinel/audit.jsonl``.
        stream: JetStream stream name. Defaults to ``ASPEN_AUDIT_STREAM`` or
            ``ASPEN_SENTINEL``.
        stream_subjects: Subjects bound to the JetStream stream. Defaults to
            ``aspen.sentinel.>``.
        max_age_seconds: Stream retention window (default 30 days).
    """

    def __init__(
        self,
        nats_url: Optional[str] = None,
        audit_log: Optional[str] = None,
        stream: Optional[str] = None,
        stream_subjects: Optional[Iterable[str]] = None,
        max_age_seconds: int = 30 * 24 * 3600,
        duplicate_window_seconds: int = 600,
    ) -> None:
        self._nats_url = nats_url or os.environ.get("ASPEN_NATS_URL", "")
        env_log = os.environ.get("ASPEN_AUDIT_LOG", "")
        self._log_path = Path(
            audit_log or env_log or DEFAULT_AUDIT_LOG
        ).expanduser()
        self._stream = stream or os.environ.get("ASPEN_AUDIT_STREAM", "") or DEFAULT_STREAM_NAME
        self._stream_subjects = list(stream_subjects) if stream_subjects else list(DEFAULT_STREAM_SUBJECTS)
        self._max_age_seconds = max_age_seconds
        self._duplicate_window_seconds = duplicate_window_seconds

        self._nc: Any = None  # nats.aio.client.Client
        self._js: Any = None  # nats.js.JetStreamContext
        self._connected = False
        self._pending: List[Dict[str, Any]] = []  # in-memory backlog (no loop / offline)

    # ---- lifecycle -------------------------------------------------------

    @property
    def is_online(self) -> bool:
        return self._connected and self._nc is not None and self._nc.is_connected

    @property
    def audit_log_path(self) -> Path:
        return self._log_path

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    async def start(self) -> bool:
        """Connect to NATS (best-effort) and ensure the JetStream stream exists.

        Returns True when connected; offline mode returns False without raising.
        """
        if not self._nats_url:
            logger.info("No NATS URL configured — audit publisher in offline mode")
            return False
        try:
            import nats

            self._nc = await nats.connect(
                self._nats_url,
                max_reconnect_attempts=3,
                reconnect_time_wait=2,
                name="aspen-sentinel-audit",
                ping_interval=20,
                max_outstanding_pings=5,
            )
            self._connected = True
            self._js = self._nc.jetstream()
            await self._ensure_stream()
            logger.info("Audit publisher connected to JetStream at %s", self._nats_url)
            return True
        except Exception as exc:  # pragma: no cover - broker-dependent
            self._connected = False
            logger.warning("NATS unavailable (%s) — audit publisher offline", exc)
            return False

    async def close(self) -> None:
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
        """Idempotently create the durable sentinel stream.

        Degrades gracefully when the stream already exists or overlaps another
        operator-defined stream — core publish remains the fallback.
        """
        if self._js is None:
            return
        try:
            await self._js.add_stream(
                name=self._stream,
                subjects=self._stream_subjects,
                storage="file",
                max_age=self._max_age_seconds,
                duplicate_window=self._duplicate_window_seconds,
            )
            logger.debug("JetStream stream %s ensured on %s", self._stream, self._stream_subjects)
        except Exception as exc:
            logger.debug("Stream %s may already exist (%s) — continuing", self._stream, exc)

    # ---- record ----------------------------------------------------------

    async def record(
        self,
        actor: str,
        action: str,
        target: Optional[str] = None,
        result: Optional[str] = None,
        *,
        event_id: Optional[str] = None,
        ts: Optional[str] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Record an audit event. Writes JSONL unconditionally, then mirrors to
        JetStream when connected. Returns the complete event dict."""
        event = build_event(
            actor, action, target=target, result=result,
            event_id=event_id, ts=ts, **extra,
        )
        return await self._record_normalized(event)

    @staticmethod
    def from_event(event: Dict[str, Any]) -> Dict[str, Any]:
        """Map a legacy/post-schema event dict into the ADR-0007 envelope.

        Covers the gatekeeper shim's audit events (``type``/``agent_id``/
        ``resource``/``decision``) plus native ADR-0007 fields, preserving any
        extra fields verbatim.
        """
        result = event.get("result") or event.get("decision") or "ok"
        if isinstance(result, dict):
            result = result.get("decision", "ok")
        return build_event(
            actor=str(event.get("actor") or event.get("agent_id") or event.get("proposer_agent_id") or "unknown"),
            action=str(event.get("action") or event.get("type") or "agent.action"),
            target=str(event.get("target") or event.get("resource") or ""),
            result=str(result),
            event_id=event.get("event_id"),
            ts=event.get("ts") or utc_now(),
            **{k: v for k, v in event.items()
               if k not in ("actor", "agent_id", "proposer_agent_id", "action", "type",
                            "target", "resource", "result", "decision", "event_id", "ts")},
        )

    async def record_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Record a pre-built event dict (legacy or normalized)."""
        normalized = self.from_event(event)
        return await self._record_normalized(normalized)

    async def _record_normalized(self, event: Dict[str, Any]) -> Dict[str, Any]:
        self._append_jsonl(event)
        if self.is_online:
            await self._publish_js(event)
        else:
            self._pending.append(event)
        return event

    def record_sync(
        self,
        actor: str,
        action: str,
        target: Optional[str] = None,
        result: Optional[str] = None,
        *,
        event_id: Optional[str] = None,
        ts: Optional[str] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Synchronous convenience for callers without a running loop (gatekeeper shim).

        Always writes JSONL. If the publish can be scheduled on a running loop
        the JetStream mirror is fire-and-forget; otherwise the event queues in
        the in-memory backlog for ``replay_pending()``.
        """
        event = build_event(
            actor, action, target=target, result=result,
            event_id=event_id, ts=ts, **extra,
        )
        self._append_jsonl(event)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._publish_js_or_buffer(event))
            else:
                self._pending.append(event)
        except RuntimeError:
            self._pending.append(event)
        return event

    def record_event_sync(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous equivalent of :meth:`record_event` for sync callers."""
        normalized = self.from_event(event)
        return self.record_sync(
            normalized["actor"], normalized["action"],
            target=normalized.get("target"), result=normalized.get("result"),
            event_id=normalized.get("event_id"), ts=normalized.get("ts"),
            **{k: v for k, v in normalized.items()
               if k not in ("actor", "action", "target", "result", "event_id", "ts")},
        )

    async def _publish_js_or_buffer(self, event: Dict[str, Any]) -> None:
        if self.is_online:
            await self._publish_js(event)
        else:
            self._pending.append(event)

    # ---- JSONL journal ---------------------------------------------------

    def _ensure_log_dir(self) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def _append_jsonl(self, event: Dict[str, Any]) -> None:
        self._ensure_log_dir()
        line = json.dumps(event, ensure_ascii=False, default=str) + "\n"
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        logger.debug("Audit event %s appended to %s", event["event_id"], self._log_path)

    def read_events(self, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read events from the JSONL journal (newest first)."""
        if not self._log_path.exists():
            return []
        events: List[Dict[str, Any]] = []
        with open(self._log_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed audit log line in %s", self._log_path)
        events.reverse()
        if limit is not None:
            events = events[:limit]
        return events

    def tail(self, n: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent ``n`` events from the JSONL journal."""
        return self.read_events(limit=max(0, n))

    def query(
        self,
        *,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        target: Optional[str] = None,
        result: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Filtered read of the JSONL journal (newest first)."""
        matches: List[Dict[str, Any]] = []
        for event in self.read_events():
            if actor is not None and event.get("actor") != actor:
                continue
            if action is not None and event.get("action") != action:
                continue
            if target is not None and event.get("target") != target:
                continue
            if result is not None and event.get("result") != result:
                continue
            if since is not None and str(event.get("ts", "")) < since:
                continue
            matches.append(event)
            if limit and len(matches) >= limit:
                break
        return matches

    # ---- JetStream mirror ------------------------------------------------

    def _event_subject(self, event: Dict[str, Any]) -> str:
        return SUBJECT_AUDIT_EVENT

    async def _publish_js(self, event: Dict[str, Any]) -> None:
        if self._js is None:
            return
        subject = self._event_subject(event)
        payload = json.dumps(event, ensure_ascii=False, default=str).encode()
        try:
            await self._js.publish(
                subject,
                payload,
                stream=self._stream,
                headers={"Nats-Msg-Id": event["event_id"]},
            )
            logger.debug("Audit event %s mirrored to %s", event["event_id"], subject)
        except Exception as exc:
            logger.warning("JetStream publish failed for audit event %s: %s", event["event_id"], exc)
            self._pending.append(event)

    def _marker_path(self) -> Path:
        return self._log_path.with_suffix(self._log_path.suffix + ".marker")

    def _load_markers(self) -> set:
        marker = self._marker_path()
        if not marker.exists():
            return set()
        try:
            return set(marker.read_text(encoding="utf-8").split())
        except OSError:
            return set()

    def _save_markers(self, event_ids: Iterable[str]) -> None:
        marker = self._marker_path()
        self._ensure_log_dir()
        existing = self._load_markers()
        existing.update(event_ids)
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("\n".join(sorted(existing)))
            if existing:
                fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())

    async def replay_pending(self) -> int:
        """Publish un-mirrored JSONL events to JetStream (idempotent).

        Combines the in-memory backlog with events in the journal whose
        ``event_id`` is not yet present in the marker file. Returns the number
        of events published.
        """
        if not self.is_online or self._js is None:
            return 0
        count = 0
        published: List[str] = []

        pending, self._pending = self._pending, []
        marked = self._load_markers()
        seen = set(marked)

        events: List[Dict[str, Any]] = []
        for event in pending:
            event_id = event.get("event_id") or ""
            if event_id in seen:
                continue
            seen.add(event_id)
            events.append(event)
        for event in reversed(self.read_events()):
            event_id = event.get("event_id") or ""
            if event_id in seen:
                continue
            seen.add(event_id)
            events.append(event)

        for event in events:
            event_id = event.get("event_id")
            if not event_id:
                continue
            try:
                await self._publish_js(event)
                published.append(event_id)
                count += 1
            except Exception:  # pragma: no cover - broker-dependent
                self._pending.append(event)
                break
        if published:
            self._save_markers(published)
        return count

    async def js_last(self, n: int = 20) -> List[Dict[str, Any]]:
        """Tail the JetStream stream (last ``n`` stored messages, newest first)."""
        if not self.is_online or self._js is None:
            raise RuntimeError("Audit publisher is offline — no JetStream access")
        info = await self._js.stream_info(self._stream)
        last_seq = int(info.state.last_seq)
        first_seq = int(info.state.first_seq)
        events: List[Dict[str, Any]] = []
        for seq in range(max(last_seq - n + 1, first_seq), last_seq + 1):
            try:
                msg = await self._js.get_msg(self._stream, seq)
            except Exception:
                continue  # deleted/rolled-up sequence — skip
            try:
                events.append(json.loads(msg.data.decode()))
            except (json.JSONDecodeError, AttributeError):
                continue
        events.reverse()
        return events

    async def check(self) -> Dict[str, Any]:
        """Report JSONL journal + JetStream stream state."""
        journal = self.read_events()
        report: Dict[str, Any] = {
            "journal": str(self._log_path),
            "events_on_disk": len(journal),
            "first_ts": journal[-1].get("ts") if journal else None,
            "last_ts": journal[0].get("ts") if journal else None,
            "stream": self._stream,
            "subject": SUBJECT_AUDIT_EVENT,
            "online": self.is_online,
        }
        if self.is_online and self._js is not None:
            try:
                info = await self._js.stream_info(self._stream)
                report["jetstream"] = {
                    "messages": int(info.state.messages),
                    "bytes": int(info.state.bytes),
                    "first_seq": int(info.state.first_seq),
                    "last_seq": int(info.state.last_seq),
                }
            except Exception as exc:
                report["jetstream"] = {"error": str(exc)}
        return report