"""
Tests for the Aspen Sentinel audit event consumer (ADR-0007 / ASP-566).

Covers:
- ADR-0007 event schema: journal tail, query, filter
- Offline-first: no broker dependency for journal reads
- Fleet overview stub returns consistent envelope
- Live NATS subscription (mocked) feeds ring buffer
- Dedup between journal and live events
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PYTHON = os.path.join(REPO_ROOT, "src", "python")
sys.path.insert(0, SRC_PYTHON)

from sentinel.consumer import AuditEventConsumer, SUBJECT_AUDIT_EVENT


# =========================================================================
# Helpers
# =========================================================================


def _make_log(tmp_path) -> str:
    return str(tmp_path / "sentinel" / "audit.jsonl")


def _make_consumer(tmp_path, **kwargs):
    return AuditEventConsumer(audit_log=_make_log(tmp_path), **kwargs)


def _seed_events(tmp_path, count: int = 5):
    """Write *count* test events to the journal path."""
    path = tmp_path / "sentinel"
    path.mkdir(parents=True, exist_ok=True)
    log = path / "audit.jsonl"
    events = []
    for i in range(count):
        ev = {
            "event_id": f"ev-{i:04d}",
            "actor": "test-agent",
            "action": f"action.{i}",
            "target": f"res-{i}",
            "result": "ok" if i % 2 == 0 else "deny",
            "ts": f"2026-09-0{(i % 9) + 1}T10:00:0{i}Z",
        }
        events.append(ev)
    log.write_text("\n".join(json.dumps(e) for e in events))
    return events


# =========================================================================
# Journal reads (offline-first, no broker)
# =========================================================================


class TestJournalReads:
    def test_tail_returns_newest_first(self, tmp_path):
        events = _seed_events(tmp_path, 5)
        consumer = _make_consumer(tmp_path)
        tail = consumer.tail(3)
        assert len(tail) == 3
        # Newest first: event_id ev-0004, ev-0003, ev-0002
        assert [e["event_id"] for e in tail] == ["ev-0004", "ev-0003", "ev-0002"]

    def test_tail_empty_journal(self, tmp_path):
        consumer = _make_consumer(tmp_path)
        assert consumer.tail(10) == []

    def test_tail_respects_n(self, tmp_path):
        _seed_events(tmp_path, 10)
        consumer = _make_consumer(tmp_path)
        assert len(consumer.tail(3)) == 3
        assert len(consumer.tail(100)) == 10

    def test_query_actor_filter(self, tmp_path):
        _seed_events(tmp_path, 5)
        consumer = _make_consumer(tmp_path)
        matched = consumer.query(actor="test-agent")
        assert len(matched) == 5

    def test_query_result_filter(self, tmp_path):
        _seed_events(tmp_path, 5)
        consumer = _make_consumer(tmp_path)
        ok_events = consumer.query(result="ok")
        deny_events = consumer.query(result="deny")
        assert len(ok_events) == 3  # i=0,2,4
        assert len(deny_events) == 2  # i=1,3

    def test_query_since_filter(self, tmp_path):
        _seed_events(tmp_path, 5)
        consumer = _make_consumer(tmp_path)
        # events have ts 2026-09-01 through 2026-09-05
        matched = consumer.query(since="2026-09-04T00:00:00Z")
        assert len(matched) == 2  # ev-0003 (sep 4), ev-0004 (sep 5) newest first

    def test_query_combined_filters(self, tmp_path):
        path = tmp_path / "sentinel"
        path.mkdir(parents=True, exist_ok=True)
        log = path / "audit.jsonl"
        events = [
            {"event_id": "e1", "actor": "u1", "action": "view", "target": "doc-1", "result": "ok", "ts": "2026-09-01T00:00:00Z"},
            {"event_id": "e2", "actor": "u2", "action": "edit", "target": "doc-1", "result": "deny", "ts": "2026-09-02T00:00:00Z"},
            {"event_id": "e3", "actor": "u1", "action": "edit", "target": "doc-2", "result": "ok", "ts": "2026-09-03T00:00:00Z"},
        ]
        log.write_text("\n".join(json.dumps(e) for e in events))
        consumer = _make_consumer(tmp_path)
        matched = consumer.query(actor="u1", result="ok")
        assert len(matched) == 2
        # Both u1 events are "ok", but newest first
        assert matched[0]["target"] == "doc-2"  # ts 2026-09-03
        assert matched[1]["target"] == "doc-1"  # ts 2026-09-01

    def test_query_no_match(self, tmp_path):
        _seed_events(tmp_path, 5)
        consumer = _make_consumer(tmp_path)
        assert consumer.query(actor="nonexistent") == []

    def test_query_limit(self, tmp_path):
        _seed_events(tmp_path, 20)
        consumer = _make_consumer(tmp_path)
        assert len(consumer.query(limit=5)) == 5


# =========================================================================
# Stats
# =========================================================================


class TestStats:
    def test_stats_empty_journal(self, tmp_path):
        consumer = _make_consumer(tmp_path)
        stats = consumer.stats()
        assert stats["total"] == 0
        assert stats["total_by_actor"] == {}
        assert stats["journal_exists"] is False

    def test_stats_with_events(self, tmp_path):
        _seed_events(tmp_path, 5)
        consumer = _make_consumer(tmp_path)
        stats = consumer.stats()
        assert stats["total"] == 5
        assert stats["total_by_actor"]["test-agent"] == 5
        assert stats["total_by_action"].get("action.0") == 1
        assert stats["oldest_ts"] is not None
        assert stats["newest_ts"] is not None
        assert stats["journal_exists"] is True
        assert stats["is_online"] is False


# =========================================================================
# Fleet overview stub
# =========================================================================


class TestFleetOverviewStub:
    def test_overview_envelope(self, tmp_path):
        consumer = _make_consumer(tmp_path)
        overview = consumer.fleet_overview()
        assert overview["_stub"] is True
        assert "hostname" in overview
        assert "observer" in overview
        assert overview["observer"] == "sentinel-consumer"
        assert "ts" in overview
        assert overview["audit_events_total"] == 0
        assert overview["local_activity_count"] == 0

    def test_overview_includes_audit_event_count(self, tmp_path):
        _seed_events(tmp_path, 10)
        consumer = _make_consumer(tmp_path)
        overview = consumer.fleet_overview()
        assert overview["audit_events_total"] == 10

    def test_overview_has_stub_note(self, tmp_path):
        consumer = _make_consumer(tmp_path)
        overview = consumer.fleet_overview()
        assert "producer not yet live" in overview["_note"]
        assert "ADR-0007" in overview["_note"]


# =========================================================================
# Live NATS subscription (mocked)
# =========================================================================


@pytest.fixture
def mock_nats():
    """Mock NATS connection for consumer live subscription tests."""
    mock_mod = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.is_connected = True
    mock_conn.drain = AsyncMock()
    mock_conn.close = AsyncMock()

    mock_js = MagicMock()
    mock_js.add_stream = AsyncMock()
    mock_js.publish = AsyncMock()

    mock_conn.jetstream = MagicMock(return_value=mock_js)

    # subscribe returns a subscription mock
    mock_sub = MagicMock()
    mock_sub.unsubscribe = AsyncMock()
    mock_conn.subscribe = AsyncMock(return_value=mock_sub)

    mock_mod.connect = AsyncMock(return_value=mock_conn)
    return mock_mod, mock_conn, mock_js, mock_sub


@pytest.mark.asyncio
class TestLiveSubscription:
    async def test_start_offline_no_url(self, tmp_path):
        consumer = _make_consumer(tmp_path)
        assert await consumer.start() is False
        assert consumer.is_online is False

    async def test_start_connects_and_subscribes(self, tmp_path, mock_nats):
        mock_mod, mock_conn, _, mock_sub = mock_nats
        consumer = _make_consumer(
            tmp_path, nats_url="nats://localhost:4222",
        )
        with patch.dict("sys.modules", {"nats": mock_mod}):
            ok = await consumer.start()
        assert ok is True
        assert consumer.is_online is True
        mock_conn.subscribe.assert_called_once()
        subj = mock_conn.subscribe.call_args[0][0]
        assert subj == SUBJECT_AUDIT_EVENT
        await consumer.close()

    async def test_live_event_feeds_ring_buffer(self, tmp_path, mock_nats):
        mock_mod, mock_conn, _, _ = mock_nats

        # Capture the callback passed to subscribe
        captured_cb = None

        async def _capture_sub(subject, cb=None):
            nonlocal captured_cb
            captured_cb = cb
            return MagicMock(unsubscribe=AsyncMock())

        mock_conn.subscribe = _capture_sub

        consumer = _make_consumer(
            tmp_path, nats_url="nats://localhost:4222",
        )
        with patch.dict("sys.modules", {"nats": mock_mod}):
            await consumer.start()

        # Simulate an incoming NATS message
        event_payload = json.dumps({
            "event_id": "live-001",
            "actor": "nats-agent",
            "action": "live.trigger",
            "target": "res-1",
            "result": "ok",
            "ts": "2026-09-07T12:00:00Z",
        }).encode()

        mock_msg = MagicMock()
        mock_msg.data = event_payload
        mock_msg.subject = SUBJECT_AUDIT_EVENT
        mock_msg.metadata = MagicMock()
        mock_msg.metadata.timestamp.isoformat.return_value = "2026-09-07T12:00:00Z"

        # Call the NATS callback
        if captured_cb:
            await captured_cb(mock_msg)

        assert consumer.live_buffer_size == 1
        live_event = consumer._live[0]
        assert live_event["event_id"] == "live-001"
        assert live_event["actor"] == "nats-agent"
        assert live_event["_nats_ts"] == "2026-09-07T12:00:00Z"

        # tail() should include the live event first
        tail = consumer.tail(5)
        assert tail[0]["event_id"] == "live-001"
        await consumer.close()

    async def test_journal_events_deduplicated_with_live(self, tmp_path, mock_nats):
        """When a live event also exists in the journal, show only the live copy."""
        mock_mod, mock_conn, _, _ = mock_nats

        captured_cb = None

        async def _capture_sub(subject, cb=None):
            nonlocal captured_cb
            captured_cb = cb
            return MagicMock(unsubscribe=AsyncMock())

        mock_conn.subscribe = _capture_sub

        # Seed journal with an event
        path = tmp_path / "sentinel"
        path.mkdir(parents=True, exist_ok=True)
        log = path / "audit.jsonl"
        journal_event = {
            "event_id": "dup-001",
            "actor": "dup-agent",
            "action": "dup.action",
            "target": "dup-res",
            "result": "ok",
            "ts": "2026-09-07T10:00:00Z",
        }
        live_event_alt = dict(journal_event)
        live_event_alt["_nats_ts"] = "2026-09-07T10:01:00Z"  # extra field = live copy
        log.write_text(json.dumps(journal_event) + "\n")

        consumer = _make_consumer(
            tmp_path, nats_url="nats://localhost:4222",
        )
        with patch.dict("sys.modules", {"nats": mock_mod}):
            await consumer.start()

        # Simulate the same event arriving via NATS
        mock_msg = MagicMock()
        mock_msg.data = json.dumps(dict(journal_event, _nats_ts="2026-09-07T10:01:00Z")).encode()
        mock_msg.subject = SUBJECT_AUDIT_EVENT
        mock_msg.metadata = None

        if captured_cb:
            await captured_cb(mock_msg)

        # tail(5) should return one entry (deduped)
        tail = consumer.tail(5)
        deduped = [e for e in tail if e["event_id"] == "dup-001"]
        assert len(deduped) == 1
        assert "_nats_ts" in deduped[0]  # live copy wins
        await consumer.close()

    async def test_invalid_json_message_ignored(self, tmp_path, mock_nats):
        mock_mod, mock_conn, _, _ = mock_nats

        captured_cb = None

        async def _capture_sub(subject, cb=None):
            nonlocal captured_cb
            captured_cb = cb
            return MagicMock(unsubscribe=AsyncMock())

        mock_conn.subscribe = _capture_sub

        consumer = _make_consumer(
            tmp_path, nats_url="nats://localhost:4222",
        )
        with patch.dict("sys.modules", {"nats": mock_mod}):
            await consumer.start()

        # Send garbage
        mock_msg = MagicMock()
        mock_msg.data = b"not-json"
        mock_msg.subject = SUBJECT_AUDIT_EVENT
        mock_msg.metadata = None

        if captured_cb:
            await captured_cb(mock_msg)

        assert consumer.live_buffer_size == 0
        await consumer.close()


# =========================================================================
# CLI integration: dashboard has /api/sentinel/audit routes
# =========================================================================


class TestDashboardRoutes:
    """Verify that the sentinel routes are plumbed into the dashboard server.

    These tests use the existing dashboard server module to confirm the route
    registration and handler wiring — they do not start the web server; they
    introspect the aiohttp Application router.
    """

    def test_sentinel_routes_registered(self):
        # Import the dashboard server module to check routes
        dashboard_path = os.path.join(REPO_ROOT, "dashboard", "server.py")
        import importlib.util
        spec = importlib.util.spec_from_file_location("dashboard_server", dashboard_path)
        if spec is None:
            pytest.skip("dashboard/server.py not loadable as module")
        mod = importlib.util.module_from_spec(spec)
        # Patch sys.path so the lazy import inside get_sentinel_consumer works
        sys.path.insert(0, SRC_PYTHON)
        try:
            spec.loader.exec_module(mod)
        except Exception:
            pytest.skip("dashboard server module import failed (expected in CI without nats-py)")
            return

        routes = mod.app.router
        # Collect registered GET route paths
        paths = []
        for route in routes._routes:
            if hasattr(route, "method") and route.method == "GET":
                paths.append(route.path)

        assert "/api/sentinel/audit" in paths
        assert "/api/sentinel/audit/stats" in paths
        assert "/api/sentinel/overview" in paths