"""
Aspen Sentinel fleet overview producer (ADR-0007 / ASP-597).

Publishes the aggregate plants/nodes/status overview (``degraded[]``) on
``aspen.sentinel.fleet.overview`` by fanning in from the existing fleet subjects:

* ``aspen.fleet.node.heartbeat`` — node liveness/status; a node whose
  ``last_seen`` is older than ``stale_after_seconds`` is reported degraded.
* ``aspen.fleet.node.register`` — transient nodes seed the registry.
* ``aspen.fleet.ops.status`` — ops-manager aggregate (known nodes / exercise)
  seeds the registry when a node has not heartbeated yet.

Write topology (mirrors :mod:`sentinel.audit`):

* **JSONL journal (always)** — append + flush + fsync at
  ``/var/lib/aspen/sentinel/fleet-overview.jsonl``. The latest overview is
  durable even fully offline.
* **JetStream (best-effort)** — the same snapshot is published to
  ``aspen.sentinel.fleet.overview`` when a broker is reachable, with
  ``Nats-Msg-Id: overview_id`` for idempotent delivery.

Only the newest aggregation matters to consumers, so there is no replay/backfill
path: stale snapshots would be noise. Consumers read the journal or the live
subject (``sentinel.consumer``).

Usage (async)::

    producer = FleetOverviewProducer(nats_url="nats://localhost:4222")
    await producer.start()      # connect + subscribe fan-in subjects
    await producer.run_loop()   # periodic publish (Ctrl-C to stop)
    await producer.close()

One-shot::

    await producer.start()
    await producer.publish_now()
    await producer.close()

Sync/offline callers append the journal directly via
``producer.journal_latest()`` reads or ``publish_now()`` (async one-shot).

CLI: ``scripts/sentinel-fleet-overview.py`` (emit / daemon / tail / check).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger("sentinel.fleet_overview")

# ADR-0007 subject + fan-in sources
SUBJECT_FLEET_OVERVIEW = "aspen.sentinel.fleet.overview"
SUBJECT_FLEET_HEARTBEAT = "aspen.fleet.node.heartbeat"
SUBJECT_FLEET_REGISTER = "aspen.fleet.node.register"
SUBJECT_FLEET_OPS_STATUS = "aspen.fleet.ops.status"

# Sentinel stream (mirrors sentinel.audit)
DEFAULT_STREAM_NAME = "ASPEN_SENTINEL"
DEFAULT_STREAM_SUBJECTS = ["aspen.sentinel.>"]
DEFAULT_MAX_AGE_SECONDS = 30 * 24 * 3600

DEFAULT_OVERVIEW_LOG = "/var/lib/aspen/sentinel/fleet-overview.jsonl"
DEFAULT_INTERVAL_SECONDS = 30  # matches fleet daemon heartbeat cadence
DEFAULT_STALE_AFTER_SECONDS = 70  # >2 missed heartbeats at 30s → degraded


def utc_now() -> str:
    """UTC timestamp in the ADR-0007 ISO-8601 form (``...Z``)."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class FleetOverviewProducer:
    """Fan-in fleet liveness → aggregate overview on ``aspen.sentinel.fleet.overview``.

    Args:
        nats_url: Broker URL (``None``/empty = offline until connected). Falls
            back to ``ASPEN_NATS_URL``.
        overview_log: Path to the JSONL journal. Defaults to
            ``ASPEN_FLEET_OVERVIEW_LOG`` or
            ``/var/lib/aspen/sentinel/fleet-overview.jsonl``.
        stream: JetStream stream name. Defaults to ``ASPEN_AUDIT_STREAM`` or
            ``ASPEN_SENTINEL``.
        stream_subjects: Subjects bound to the JetStream stream. Defaults to
            ``aspen.sentinel.>``.
        interval_seconds: Publish cadence for ``run_loop()`` (default 30).
        stale_after_seconds: Max node age before it reports ``degraded``
            (default 70).
        max_age_seconds: Stream retention window (default 30 days).
    """

    def __init__(
        self,
        nats_url: Optional[str] = None,
        overview_log: Optional[str] = None,
        stream: Optional[str] = None,
        stream_subjects: Optional[Iterable[str]] = None,
        interval_seconds: Optional[int] = None,
        stale_after_seconds: Optional[int] = None,
        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    ) -> None:
        self._nats_url = nats_url or os.environ.get("ASPEN_NATS_URL", "")
        env_log = os.environ.get("ASPEN_FLEET_OVERVIEW_LOG", "")
        self._log_path = Path(
            overview_log or env_log or DEFAULT_OVERVIEW_LOG
        ).expanduser()
        self._stream = stream or os.environ.get("ASPEN_AUDIT_STREAM", "") or DEFAULT_STREAM_NAME
        self._stream_subjects = list(stream_subjects) if stream_subjects else list(DEFAULT_STREAM_SUBJECTS)
        self._interval_seconds = (
            interval_seconds
            or _env_int("ASPEN_FLEET_OVERVIEW_INTERVAL", DEFAULT_INTERVAL_SECONDS)
        )
        self._stale_after_seconds = (
            stale_after_seconds
            or _env_int("ASPEN_FLEET_OVERVIEW_STALE_AFTER", DEFAULT_STALE_AFTER_SECONDS)
        )
        self._max_age_seconds = max_age_seconds

        self._nc: Any = None
        self._js: Any = None
        self._connected = False
        self._subs: List[Any] = []
        self._nodes: Dict[str, Dict[str, Any]] = {}

    # ---- lifecycle -------------------------------------------------------

    @property
    def is_online(self) -> bool:
        return self._connected and self._nc is not None and self._nc.is_connected

    @property
    def overview_log_path(self) -> Path:
        return self._log_path

    @property
    def registered_nodes(self) -> int:
        return len(self._nodes)

    async def start(self) -> bool:
        """Connect to NATS (best-effort), ensure the stream, subscribe fan-in.

        Returns True when connected; offline mode returns False without raising.
        """
        if not self._nats_url:
            logger.info("No NATS URL configured — fleet overview producer offline")
            return False
        try:
            import nats

            self._nc = await nats.connect(
                self._nats_url,
                max_reconnect_attempts=3,
                reconnect_time_wait=2,
                name="aspen-sentinel-fleet-overview",
                ping_interval=20,
                max_outstanding_pings=5,
            )
            self._connected = True
            self._js = self._nc.jetstream()
            await self._ensure_stream()
            await self._subscribe()
            logger.info("Fleet overview producer connected to JetStream at %s", self._nats_url)
            return True
        except Exception as exc:  # pragma: no cover - broker-dependent
            self._connected = False
            logger.warning("NATS unavailable (%s) — fleet overview producer offline", exc)
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
            logger.debug("JetStream stream %s ensured on %s", self._stream, self._stream_subjects)
        except Exception as exc:
            logger.debug("Stream %s may already exist (%s) — continuing", self._stream, exc)

    async def _subscribe(self) -> None:
        if self._nc is None or not self._nc.is_connected:
            return

        async def _on_node_msg(msg: Any) -> None:
            try:
                data = json.loads(msg.data.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return
            if msg.subject in (SUBJECT_FLEET_HEARTBEAT, SUBJECT_FLEET_REGISTER):
                self._sync_node(data)
            elif msg.subject == SUBJECT_FLEET_OPS_STATUS:
                self._merge_ops_status(data)

        for subject in (SUBJECT_FLEET_HEARTBEAT, SUBJECT_FLEET_REGISTER, SUBJECT_FLEET_OPS_STATUS):
            self._subs.append(await self._nc.subscribe(subject, cb=_on_node_msg))

    # ---- fan-in registry ---------------------------------------------------

    def _sync_node(self, payload: Dict[str, Any]) -> None:
        node_id = payload.get("node_id")
        if not node_id:
            return
        node = self._nodes.setdefault(node_id, {})
        node.update(
            {
                "node_id": node_id,
                "plant": payload.get("plant", node.get("plant", "unknown")),
                "roles": payload.get("roles", node.get("roles", [])),
                "team": payload.get("team", node.get("team", "unknown")),
                "status": payload.get("status", node.get("status", "online")),
                "last_seen": payload.get("last_seen") or utc_now(),
                "hostname": payload.get("hostname", node.get("hostname", "")),
            }
        )
        if payload.get("capabilities"):
            node["capabilities"] = payload["capabilities"]
        self._nodes[node_id] = node

    def _merge_ops_status(self, payload: Dict[str, Any]) -> None:
        """Seed known node ids from ``aspen.fleet.ops.status`` (no per-node detail).

        Individual heartbeats refine plant/roles later; this only prevents an
        empty overview when only the ops summary has been observed.
        """
        known = payload.get("nodes")
        if not isinstance(known, list):
            return
        for node_id in known:
            if node_id in self._nodes:
                continue
            self._nodes[node_id] = {
                "node_id": node_id,
                "plant": "unknown",
                "status": "online",
                "last_seen": payload.get("timestamp") or utc_now(),
            }

    # ---- aggregation ------------------------------------------------------

    def build_overview(self) -> Dict[str, Any]:
        """Build the aggregate overview (ADR-0007 shape)."""
        now = datetime.now(timezone.utc)
        nodes: List[Dict[str, Any]] = []
        degraded: List[str] = []
        plants: Dict[str, Dict[str, Any]] = {}

        for node_id in sorted(self._nodes):
            node = self._nodes[node_id]
            last_seen = node.get("last_seen")
            stale = False
            if last_seen:
                try:
                    last_dt = datetime.fromisoformat(
                        str(last_seen).replace("Z", "+00:00")
                    )
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    stale = (now - last_dt).total_seconds() > self._stale_after_seconds
                except (TypeError, ValueError):
                    stale = True
            status = node.get("status") or "online"
            if stale:
                status = "degraded"
            is_degraded = stale or status != "online"
            if is_degraded:
                degraded.append(node_id)

            plant_id = node.get("plant") or "unknown"
            plant = plants.setdefault(plant_id, {"id": plant_id, "status": "ok", "nodes": 0})
            plant["nodes"] += 1
            if is_degraded:
                plant["status"] = "degraded"

            nodes.append(
                {
                    "node_id": node_id,
                    "plant": plant_id,
                    "status": status,
                    "roles": node.get("roles", []),
                    "team": node.get("team", ""),
                    "last_seen": last_seen,
                    "hostname": node.get("hostname", ""),
                    "degraded": is_degraded,
                }
            )

        if not nodes:
            overall = "offline"
        elif degraded:
            overall = "degraded"
        else:
            overall = "ok"

        return {
            "overview_id": uuid.uuid4().hex,
            "ts": utc_now(),
            "source": "sentinel-fleet-overview",
            "status": overall,
            "total_nodes": len(nodes),
            "degraded": degraded,
            "nodes": nodes,
            "plants": sorted(plants.values(), key=lambda p: p["id"]),
            "interval_seconds": self._interval_seconds,
            "stale_after_seconds": self._stale_after_seconds,
        }

    # ---- publish ----------------------------------------------------------

    async def publish_now(self) -> Dict[str, Any]:
        """Build + journal one overview; mirror to JetStream when online."""
        overview = self.build_overview()
        self._append_journal(overview)
        if self.is_online and self._js is not None:
            subject = SUBJECT_FLEET_OVERVIEW
            payload = json.dumps(overview, ensure_ascii=False, default=str).encode()
            try:
                await self._js.publish(
                    subject,
                    payload,
                    stream=self._stream,
                    headers={"Nats-Msg-Id": overview["overview_id"]},
                )
                logger.debug("Overview %s published to %s", overview["overview_id"], subject)
            except Exception as exc:
                logger.warning("JetStream publish failed for overview %s: %s", overview["overview_id"], exc)
        return overview

    async def run_loop(self) -> None:
        """Publish an overview every ``interval_seconds`` until cancelled."""
        while True:
            await self.publish_now()
            await asyncio.sleep(self._interval_seconds)

    # ---- journal ----------------------------------------------------------

    def _ensure_log_dir(self) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def _append_journal(self, overview: Dict[str, Any]) -> None:
        self._ensure_log_dir()
        line = json.dumps(overview, ensure_ascii=False, default=str) + "\n"
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        logger.debug("Overview %s appended to %s", overview["overview_id"], self._log_path)

    def _read_journal(self) -> List[Dict[str, Any]]:
        if not self._log_path.exists():
            return []
        events: List[Dict[str, Any]] = []
        try:
            with open(self._log_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed overview line in %s", self._log_path)
        except OSError:
            return []
        return events

    def latest(self) -> Optional[Dict[str, Any]]:
        """Newest overview from the journal, or None when empty."""
        events = self._read_journal()
        return events[-1] if events else None

    def tail(self, n: int = 20) -> List[Dict[str, Any]]:
        """Most recent ``n`` overviews from the journal (newest first)."""
        events = self._read_journal()
        return list(reversed(events[-max(0, n):]))

    async def check(self) -> Dict[str, Any]:
        """Report journal + registry + JetStream state."""
        events = self._read_journal()
        report: Dict[str, Any] = {
            "journal": str(self._log_path),
            "overviews_on_disk": len(events),
            "first_ts": events[0].get("ts") if events else None,
            "last_ts": events[-1].get("ts") if events else None,
            "stream": self._stream,
            "subject": SUBJECT_FLEET_OVERVIEW,
            "online": self.is_online,
            "registered_nodes": len(self._nodes),
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


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, ""))
    except (TypeError, ValueError):
        return default