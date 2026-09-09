"""
Aspen Sentinel consumer — reads ``aspen.sentinel.audit.event`` (ADR-0007).

**Write topology (mirrors https://github.com/AbsolutionAI/aspen-contracts):**

- **JSONL journal (always):** reads the durable append-only log written by
  :class:`AuditEventPublisher`. No broker required. ``tail()`` / ``query()``
  work fully offline (local-first per ASP-566 constraints).
- **NATS subscription (online, optional):** subscribes to
  ``aspen.sentinel.audit.event`` for real-time event delivery into an in-memory
  ring buffer. Falls back silently when offline.
- **Fleet overview stub:** returns local node/plant aggregate. The producer for
  ``aspen.sentinel.fleet.overview`` does not yet exist; this is an offline-capable
  preview. When the producer lands, switch to NATS subscription.

**Gatekeeper awareness:** the consumer requires no NATS credentials for journal
reads (local-first). Online NATS access uses the same unprivileged role as the
dashboard — no broad credentials (ADR-0009, H-015 / H-018).

Usage::

    consumer = AuditEventConsumer(audit_log="/var/lib/aspen/sentinel/audit.jsonl")
    consumer.start()   # optional NATS connect for live subscription
    events = consumer.tail(n=20)
    filtered = consumer.query(actor="aspen-fleet-edge", result="deny")
    overview = consumer.fleet_overview()
    consumer.close()
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sentinel.consumer")

# ADR-0007 envelope
SUBJECT_AUDIT_EVENT = "aspen.sentinel.audit.event"
SUBJECT_FLEET_OVERVIEW = "aspen.sentinel.fleet.overview"

DEFAULT_AUDIT_LOG = "/var/lib/aspen/sentinel/audit.jsonl"
DEFAULT_RING_SIZE = 500  # in-memory live-event buffer

# Required envelope fields (ADR-0007)
REQUIRED_FIELDS = ("event_id", "actor", "action", "target", "result", "ts")

# Sentinel stream (mirrors AuditEventPublisher)
DEFAULT_STREAM_NAME = "ASPEN_SENTINEL"


# =========================================================================
# Audit event consumer
# =========================================================================


class AuditEventConsumer:
    """Local-first consumer for ``aspen.sentinel.audit.event``.

    Reads the JSONL journal unconditionally (zero broker dependency) and
    optionally subscribes to NATS for live events.

    Args:
        audit_log: Path to the JSONL journal. Defaults to ``ASPEN_AUDIT_LOG``
            or ``/var/lib/aspen/sentinel/audit.jsonl``.
        nats_url: Broker URL (None/empty = journal-only). Falls back to
            ``ASPEN_NATS_URL``.
        ring_size: Max in-memory live events (default 500).
        stream: JetStream stream name for subscription.
    """

    def __init__(
        self,
        audit_log: Optional[str] = None,
        nats_url: Optional[str] = None,
        ring_size: int = DEFAULT_RING_SIZE,
        stream: Optional[str] = None,
    ) -> None:
        env_log = os.environ.get("ASPEN_AUDIT_LOG", "")
        self._log_path = Path(
            audit_log or env_log or DEFAULT_AUDIT_LOG
        ).expanduser()
        self._nats_url = nats_url or os.environ.get("ASPEN_NATS_URL", "") or None
        self._ring_size = ring_size
        self._stream = stream or os.environ.get(
            "ASPEN_AUDIT_STREAM", ""
        ) or DEFAULT_STREAM_NAME

        # NATS state
        self._nc: Any = None
        self._sub: Any = None
        self._consumer_task: Any = None

        # In-memory ring buffer for live NATS events (newest first)
        self._live: deque = deque(maxlen=ring_size)

    # ---- lifecycle -------------------------------------------------------

    @property
    def is_online(self) -> bool:
        return self._nc is not None and self._nc.is_connected

    @property
    def audit_log_path(self) -> Path:
        return self._log_path

    @property
    def live_buffer_size(self) -> int:
        """Number of events in the live NATS ring buffer."""
        return len(self._live)

    async def start(self) -> bool:
        """Connect to NATS (best-effort) and subscribe to audit events.

        Returns True when the live subscription is active; journal reads
        always work regardless.
        """
        if not self._nats_url:
            logger.info(
                "No NATS URL — consumer in journal-only mode"
            )
            return False
        try:
            import nats

            self._nc = await nats.connect(
                self._nats_url,
                max_reconnect_attempts=3,
                reconnect_time_wait=2,
                name="aspen-sentinel-consumer",
                ping_interval=20,
                max_outstanding_pings=5,
                connect_timeout=5,
            )

            self._js = self._nc.jetstream()
            await self._ensure_stream()
            await self._subscribe()
            logger.info(
                "Audit consumer subscribed to %s at %s",
                SUBJECT_AUDIT_EVENT,
                self._nats_url,
            )
            return True
        except Exception as exc:
            logger.warning(
                "NATS unavailable (%s) — consumer in journal-only mode", exc
            )
            self._nc = None
            return False

    async def _ensure_stream(self) -> None:
        """Idempotently ensure the ASPEN_SENTINEL stream exists."""
        if self._js is None:
            return
        try:
            await self._js.add_stream(
                name=self._stream,
                subjects=["aspen.sentinel.>"],
                storage="file",
                max_age=30 * 24 * 3600,
                duplicate_window=600,
            )
        except Exception:
            pass  # stream already exists — ok

    async def _subscribe(self) -> None:
        """Subscribe to the audit event subject and feed the ring buffer."""
        if self._nc is None or not self._nc.is_connected:
            return

        async def _on_msg(msg: Any) -> None:
            try:
                data = json.loads(msg.data.decode())
                data["_nats_ts"] = msg.metadata.timestamp.isoformat() if msg.metadata else None
                self._live.appendleft(data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                logger.debug("Ignoring non-JSON message on %s", msg.subject)

        self._sub = await self._nc.subscribe(SUBJECT_AUDIT_EVENT, cb=_on_msg)

    async def close(self) -> None:
        """Drain NATS connection and stop the live subscription."""
        if self._sub is not None:
            try:
                await self._sub.unsubscribe()
            except Exception:
                pass
            self._sub = None
        if self._nc is not None:
            try:
                await self._nc.drain()
                await self._nc.close()
            except Exception:
                pass
            self._nc = None

    async def subscribe_consumer(self, cb):
        """Register an external callback for every incoming audit event.

        Args:
            cb: Async callable ``(event_dict) -> None`` called for each
                message on ``aspen.sentinel.audit.event``.

        This is a convenience for wiring into the dashboard's SSE or
        alternative real-time sinks. Only active after ``start()``.
        """
        if self._nc is None:
            logger.warning("Cannot subscribe callback — consumer not started")
            return
        if not self._nc.is_connected:
            return

        async def _wrapped(msg):
            try:
                data = json.loads(msg.data.decode())
                await cb(data)
            except Exception:
                pass

        await self._nc.subscribe(SUBJECT_AUDIT_EVENT, cb=_wrapped)

    # ---- journal reads (always available) --------------------------------

    def _read_journal(self) -> List[Dict[str, Any]]:
        """Return all events from the JSONL journal, newest first."""
        if not self._log_path.exists():
            return []
        try:
            raw = self._log_path.read_text()
        except OSError:
            return []
        events = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        events.reverse()  # newest first
        return events

    def tail(self, n: int = 20) -> List[Dict[str, Any]]:
        """Return the last *n* audit events, newest first.

        Merges live NATS events (if any) with journal events, preferring
        live entries and deduplicating by ``event_id``.
        """
        journal = self._read_journal()
        seen: set = set()

        merged: List[Dict[str, Any]] = []
        # Live events first (hot path)
        for ev in self._live:
            eid = ev.get("event_id", "")
            if eid and eid in seen:
                continue
            if eid:
                seen.add(eid)
            merged.append(ev)
            if len(merged) >= n:
                break

        # Fill remaining from journal
        if len(merged) < n:
            for ev in journal:
                eid = ev.get("event_id", "")
                if eid and eid in seen:
                    continue
                if eid:
                    seen.add(eid)
                merged.append(ev)
                if len(merged) >= n:
                    break

        return merged[:n]

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
        """Filtered event query over the full journal.

        All filters are case-sensitive substring matches. Supply only
        the fields you want to filter on.

        Returns up to *limit* events, newest first.
        """
        journal = self._read_journal()
        matched: List[Dict[str, Any]] = []
        for ev in journal:
            if self._matches(ev, actor, action, target, result, since):
                matched.append(ev)
                if len(matched) >= limit:
                    break
        return matched

    @staticmethod
    def _matches(
        ev: Dict[str, Any],
        actor: Optional[str] = None,
        action: Optional[str] = None,
        target: Optional[str] = None,
        result: Optional[str] = None,
        since: Optional[str] = None,
    ) -> bool:
        if actor and actor not in str(ev.get("actor", "")):
            return False
        if action and action not in str(ev.get("action", "")):
            return False
        if target and target not in str(ev.get("target", "")):
            return False
        if result and result not in str(ev.get("result", "")):
            return False
        if since and str(ev.get("ts", "")) < since:
            return False
        return True

    def stats(self) -> Dict[str, Any]:
        """Aggregate counts from the journal.

        Returns:
            dict with total, total_by_actor, total_by_action, oldest_ts,
            newest_ts, live_buffer_size, journal_path, is_online.
        """
        journal = self._read_journal()
        if not journal:
            return {
                "total": 0,
                "total_by_actor": {},
                "total_by_action": {},
                "oldest_ts": None,
                "newest_ts": None,
                "live_buffer_size": self.live_buffer_size,
                "journal_path": str(self._log_path),
                "journal_exists": self._log_path.exists(),
                "is_online": self.is_online,
            }

        actors: Counter = Counter()
        actions: Counter = Counter()
        for ev in journal:
            actors[ev.get("actor", "?")] += 1
            actions[ev.get("action", "?")] += 1

        return {
            "total": len(journal),
            "total_by_actor": dict(actors.most_common()),
            "total_by_action": dict(actions.most_common()),
            "oldest_ts": journal[-1].get("ts") if journal else None,
            "newest_ts": journal[0].get("ts") if journal else None,
            "live_buffer_size": self.live_buffer_size,
            "journal_path": str(self._log_path),
            "journal_exists": self._log_path.exists(),
            "is_online": self.is_online,
        }

    # ---- fleet overview stub (offline-capable) ---------------------------

    def fleet_overview(self) -> Dict[str, Any]:
        """Return a **stub** fleet overview.

        The ``aspen.sentinel.fleet.overview`` producer does not yet exist
        (ADR-0007 "Next"). This method provides an offline-capable preview
        built from local state:

        - Local machine hostname, uptime, plant (from fleet.yaml if present)
        - Count of audit events by plant/actor as a proxy for activity
        - A ``_stub: true`` marker so consumers know this is not live
          producer data.

        When the fleet overview producer lands, this method should either
        be replaced by a NATS subscription or enriched with the producer's
        aggregate payload.
        """
        import platform

        # Local host info
        hostname = platform.node()
        uptime_seconds = 0.0
        try:
            with open("/proc/uptime") as f:
                uptime_seconds = float(f.read().split()[0])
        except Exception:
            pass

        # Plant hint from fleet config
        local_plant = "unknown"
        for candidate in (
            Path("/etc/starship/fleet-node.yaml"),
            Path("/etc/starship/fleet.yaml"),
        ):
            if candidate.exists():
                try:
                    import yaml as _yaml  # noqa: F811
                    raw = _yaml.safe_load(candidate.read_text()) or {}
                    local_plant = (
                        raw.get("node", {}).get("plant")
                        or raw.get("plants", {}).get("default")
                        or local_plant
                    )
                    break
                except Exception:
                    pass

        # Activity proxy from audit journal
        journal = self._read_journal()
        activity_count = len([e for e in journal if e.get("actor", "")])

        return {
            "_stub": True,
            "_note": "Fleet overview producer not yet live (ADR-0007). This is a local preview.",
            "hostname": hostname,
            "uptime_seconds": int(uptime_seconds),
            "local_plant": local_plant,
            "audit_events_total": len(journal),
            "local_activity_count": activity_count,
            "observer": "sentinel-consumer",
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }