"""
Tests for the Aspen Sentinel fleet overview producer (ADR-0007 / ASP-597).

Covers:
- Aggregate shape: plants/nodes/status + ``degraded[]``
- Fan-in: heartbeat/register/ops.status registry ingest
- Staleness → degraded + overall status transitions
- JSONL journal durability (append, latest, tail)
- Best-effort JetStream publish (mocked) with ``Nats-Msg-Id`` dedup header
- Consumer: ``fleet_overview()`` prefers live → producer journal → preview stub
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PYTHON = os.path.join(REPO_ROOT, "src", "python")
sys.path.insert(0, SRC_PYTHON)

from sentinel.fleet_overview import (
    DEFAULT_OVERVIEW_LOG,
    SUBJECT_FLEET_HEARTBEAT,
    SUBJECT_FLEET_OPS_STATUS,
    SUBJECT_FLEET_OVERVIEW,
    SUBJECT_FLEET_REGISTER,
    FleetOverviewProducer,
)
from sentinel.consumer import AuditEventConsumer


def _make_producer(tmp_path, **kwargs):
    kwargs.setdefault("overview_log", str(tmp_path / "sentinel" / "fleet-overview.jsonl"))
    return FleetOverviewProducer(**kwargs)


def _heartbeat(node_id, plant="plant-alpha", last_seen=None, status="online"):
    return {
        "node_id": node_id,
        "hostname": f"{node_id}.local",
        "plant": plant,
        "roles": ["proxy"],
        "team": "ops",
        "status": status,
        "last_seen": last_seen or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "capabilities": {"arch": "arm64"},
    }


# =========================================================================
# build_overview aggregate shape
# =========================================================================


class TestBuildOverview:
    def test_empty_registry_offline(self, tmp_path):
        producer = _make_producer(tmp_path)
        overview = producer.build_overview()
        assert overview["status"] == "offline"
        assert overview["total_nodes"] == 0
        assert overview["degraded"] == []
        assert overview["plants"] == []
        assert overview["source"] == "sentinel-fleet-overview"
        assert "overview_id" in overview
        assert "ts" in overview

    def test_healthy_node_aggregate(self, tmp_path):
        producer = _make_producer(tmp_path)
        producer._sync_node(_heartbeat("node-a"))
        producer._sync_node(_heartbeat("node-b", plant="plant-beta"))
        overview = producer.build_overview()
        assert overview["status"] == "ok"
        assert overview["total_nodes"] == 2
        assert overview["degraded"] == []
        assert sorted(p["id"] for p in overview["plants"]) == ["plant-alpha", "plant-beta"]
        assert overview["plants"][0]["nodes"] == 1
        node = overview["nodes"][0]
        assert node["degraded"] is False
        assert node["plant"] in ("plant-alpha", "plant-beta")

    def test_stale_node_is_degraded(self, tmp_path):
        producer = _make_producer(tmp_path, stale_after_seconds=70)
        old = (datetime.now(timezone.utc) - timedelta(seconds=200)).isoformat().replace("+00:00", "Z")
        producer._sync_node(_heartbeat("node-a", last_seen=old))
        overview = producer.build_overview()
        assert overview["status"] == "degraded"
        assert "node-a" in overview["degraded"]
        node = overview["nodes"][0]
        assert node["status"] == "degraded"
        assert node["degraded"] is True

    def test_explicit_non_online_status_is_degraded(self, tmp_path):
        producer = _make_producer(tmp_path)
        producer._sync_node(_heartbeat("node-a"))
        producer._sync_node(_heartbeat("node-b", status="offline"))
        overview = producer.build_overview()
        assert overview["status"] == "degraded"
        assert "node-b" in overview["degraded"]

    def test_fresh_and_stale_mixed(self, tmp_path):
        producer = _make_producer(tmp_path, stale_after_seconds=70)
        stale = (datetime.now(timezone.utc) - timedelta(seconds=500)).isoformat().replace("+00:00", "Z")
        producer._sync_node(_heartbeat("node-fresh"))
        producer._sync_node(_heartbeat("node-stale", last_seen=stale))
        overview = producer.build_overview()
        assert overview["status"] == "degraded"
        fresh = next(n for n in overview["nodes"] if n["node_id"] == "node-fresh")
        assert fresh["status"] == "online"
        assert fresh["degraded"] is False


# =========================================================================
# Fan-in registry
# =========================================================================


class TestFanIn:
    def test_ops_status_seeds_known_nodes(self, tmp_path):
        producer = _make_producer(tmp_path)
        producer._merge_ops_status({
            "nodes": ["node-x", "node-y"],
            "plants": ["plant-alpha"],
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        })
        assert producer.registered_nodes == 2
        overview = producer.build_overview()
        assert overview["total_nodes"] == 2

    def test_ops_status_does_not_override_existing(self, tmp_path):
        producer = _make_producer(tmp_path)
        producer._sync_node(_heartbeat("node-x", plant="plant-alpha"))
        producer._merge_ops_status({"nodes": ["node-x", "node-y"], "plants": []})
        node = producer._nodes["node-x"]
        assert node["plant"] == "plant-alpha"
        assert producer.registered_nodes == 2

    def test_register_syncs_node(self, tmp_path):
        producer = _make_producer(tmp_path)
        producer._sync_node(_heartbeat("node-new"))
        assert producer._nodes["node-new"]["plant"] == "plant-alpha"


# =========================================================================
# Journal durability (offline-first)
# =========================================================================


class TestJournal:
    @pytest.mark.asyncio
    async def test_publish_now_appends_journal(self, tmp_path):
        producer = _make_producer(tmp_path)
        producer._sync_node(_heartbeat("node-a"))
        overview = await producer.publish_now()
        assert producer.overview_log_path.exists()
        assert overview["status"] == "ok"
        latest = producer.latest()
        assert latest["overview_id"] == overview["overview_id"]

    @pytest.mark.asyncio
    async def test_latest_none_when_empty(self, tmp_path):
        producer = _make_producer(tmp_path)
        assert producer.latest() is None
        assert producer.tail(5) == []

    @pytest.mark.asyncio
    async def test_tail_returns_newest_first(self, tmp_path):
        producer = _make_producer(tmp_path)
        producer._sync_node(_heartbeat("node-a"))
        await producer.publish_now()
        await producer.publish_now()
        tail = producer.tail(2)
        assert len(tail) == 2
        assert tail[0]["ts"] >= tail[1]["ts"]


# =========================================================================
# Best-effort JetStream publish (mocked)
# =========================================================================


@pytest.fixture
def mock_nats():
    mock_mod = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.is_connected = True
    mock_conn.drain = AsyncMock()
    mock_conn.close = AsyncMock()

    mock_js = MagicMock()
    mock_js.add_stream = AsyncMock()
    mock_js.publish = AsyncMock()

    mock_info = MagicMock()
    mock_info.state.messages = 3
    mock_info.state.bytes = 120
    mock_info.state.first_seq = 1
    mock_info.state.last_seq = 3
    mock_js.stream_info = AsyncMock(return_value=mock_info)

    mock_conn.jetstream = MagicMock(return_value=mock_js)
    mock_mod.connect = AsyncMock(return_value=mock_conn)
    return mock_mod, mock_conn, mock_js


@pytest.mark.asyncio
class TestNatSPublish:
    async def test_start_offline_no_url(self, tmp_path):
        producer = _make_producer(tmp_path)
        assert await producer.start() is False
        assert producer.is_online is False
        await producer.close()

    async def test_publish_subject_and_dedup_header(self, tmp_path, mock_nats):
        mock_mod, mock_conn, mock_js = mock_nats
        producer = _make_producer(tmp_path, nats_url="nats://localhost:4222")
        producer._sync_node(_heartbeat("node-a"))
        with patch.dict("sys.modules", {"nats": mock_mod}):
            ok = await producer.start()
        assert ok is True
        overview = await producer.publish_now()
        mock_js.publish.assert_called_once()
        call = mock_js.publish.call_args
        assert call[0][0] == SUBJECT_FLEET_OVERVIEW
        assert call.kwargs["stream"] == "ASPEN_SENTINEL"
        assert call.kwargs["headers"]["Nats-Msg-Id"] == overview["overview_id"]
        await producer.close()

    async def test_daemon_subscribes_fan_in_subjects(self, tmp_path, mock_nats):
        mock_mod, mock_conn, _ = mock_nats
        producer = _make_producer(tmp_path, nats_url="nats://localhost:4222")
        with patch.dict("sys.modules", {"nats": mock_mod}):
            await producer.start()
        subjects = [c.args[0] for c in mock_conn.subscribe.call_args_list]
        assert SUBJECT_FLEET_HEARTBEAT in subjects
        assert SUBJECT_FLEET_REGISTER in subjects
        assert SUBJECT_FLEET_OPS_STATUS in subjects
        await producer.close()

    async def test_offline_publish_never_raises(self, tmp_path):
        producer = _make_producer(tmp_path)
        producer._sync_node(_heartbeat("node-a"))
        overview = await producer.publish_now()
        assert overview["status"] == "ok"
        assert producer.latest()["overview_id"] == overview["overview_id"]

    async def test_registry_state_reported_by_check(self, tmp_path, mock_nats):
        mock_mod, mock_conn, _ = mock_nats
        producer = _make_producer(tmp_path, nats_url="nats://localhost:4222")
        producer._sync_node(_heartbeat("node-a"))
        with patch.dict("sys.modules", {"nats": mock_mod}):
            await producer.start()
        report = await producer.check()
        assert report["subject"] == SUBJECT_FLEET_OVERVIEW
        assert report["registered_nodes"] == 1
        assert report["online"] is True
        assert report["jetstream"]["messages"] >= 0
        await producer.close()


# =========================================================================
# Consumer producer-aware fleet_overview()
# =========================================================================


@pytest.fixture
def mock_consumer_nats():
    mock_mod = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.is_connected = True
    mock_conn.drain = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_js = MagicMock()
    mock_js.add_stream = AsyncMock()
    mock_conn.jetstream = MagicMock(return_value=mock_js)
    mock_mod.connect = AsyncMock(return_value=mock_conn)
    mock_conn.subscribe = AsyncMock(return_value=MagicMock(unsubscribe=AsyncMock()))
    return mock_mod, mock_conn


def _write_producer_journal(tmp_path, status="ok"):
    path = tmp_path / "sentinel"
    path.mkdir(parents=True, exist_ok=True)
    log = path / "fleet-overview.jsonl"
    overview = {
        "overview_id": "ov-1",
        "ts": "2026-09-17T10:00:00Z",
        "source": "sentinel-fleet-overview",
        "status": status,
        "total_nodes": 1,
        "degraded": [],
        "nodes": [{"node_id": "n1", "plant": "plant-alpha", "status": "online"}],
        "plants": [{"id": "plant-alpha", "status": "ok", "nodes": 1}],
    }
    log.write_text(json.dumps(overview) + "\n")
    return str(log)


class TestConsumerOverviewPreference:
    def test_prefers_producer_journal(self, tmp_path):
        log = _write_producer_journal(tmp_path, status="degraded")
        consumer = AuditEventConsumer(
            audit_log=str(tmp_path / "sentinel" / "audit.jsonl"),
            overview_log=log,
        )
        overview = consumer.fleet_overview()
        assert overview["overview_id"] == "ov-1"
        assert overview["status"] == "degraded"
        assert overview["source"] == "sentinel-fleet-overview"
        assert "_stub" not in overview

    def test_falls_back_to_preview_stub(self, tmp_path):
        consumer = AuditEventConsumer(
            audit_log=str(tmp_path / "sentinel" / "audit.jsonl"),
            overview_log=str(tmp_path / "sentinel" / "missing.jsonl"),
        )
        overview = consumer.fleet_overview()
        assert overview["_stub"] is True
        assert "producer not yet live" in overview["_note"]

    @pytest.mark.asyncio
    async def test_prefers_live_overview(self, tmp_path, mock_consumer_nats):
        mock_mod, mock_conn = mock_consumer_nats
        captured: dict = {}
        sub = MagicMock(unsubscribe=AsyncMock())

        async def _capture_sub(subject, cb=None):
            captured[subject] = cb
            return sub

        mock_conn.subscribe = _capture_sub
        consumer = AuditEventConsumer(
            audit_log=str(tmp_path / "sentinel" / "audit.jsonl"),
            overview_log=str(tmp_path / "sentinel" / "fleet-overview.jsonl"),
            nats_url="nats://localhost:4222",
        )
        with patch.dict("sys.modules", {"nats": mock_mod}):
            await consumer.start()

        live = {
            "overview_id": "ov-live",
            "ts": "2026-09-17T11:00:00Z",
            "source": "sentinel-fleet-overview",
            "status": "ok",
            "total_nodes": 3,
            "degraded": [],
        }
        mock_msg = MagicMock()
        mock_msg.data = json.dumps(live).encode()
        mock_msg.subject = SUBJECT_FLEET_OVERVIEW
        mock_msg.metadata = None

        overview_cb = captured.get(SUBJECT_FLEET_OVERVIEW)
        if overview_cb:
            await overview_cb(mock_msg)

        overview = consumer.fleet_overview()
        assert overview["overview_id"] == "ov-live"
        assert overview["status"] == "ok"
        await consumer.close()