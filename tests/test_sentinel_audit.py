"""
Tests for the Aspen Sentinel audit event publisher (ADR-0007 / H-015 / ASP-537).

Covers:
- ADR-0007 event schema: {event_id, actor, action, target, result, ts}
- JSONL journal: unconditional durable append, tail, query
- JetStream mirror: subject + Nats-Msg-Id dedup header + stream bootstrap
- Offline resilience: events buffered and replayed idempotently
- Gatekeeper shim wiring: log_audit fans into the published trail
- CLI subcommands present
"""

import asyncio
import json
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PYTHON = os.path.join(REPO_ROOT, "src", "python")
sys.path.insert(0, SRC_PYTHON)

from sentinel import AuditEventPublisher, SUBJECT_AUDIT_EVENT, build_event  # noqa: E402
from sentinel.audit import REQUIRED_FIELDS  # noqa: E402


def _make_log(tmp_path) -> str:
    return str(tmp_path / "sentinel" / "audit.jsonl")


def _make_publisher(tmp_path, **kwargs):
    return AuditEventPublisher(audit_log=_make_log(tmp_path), **kwargs)


# =========================================================================
# Event schema
# =========================================================================


class TestEventSchema:
    def test_build_event_envelope(self):
        event = build_event("aspen-sentinel", "capability.grant",
                            target="plant:chae-cell-01", result="grant")
        for field in REQUIRED_FIELDS:
            assert field in event, f"missing required field {field}"
        assert isinstance(event["event_id"], str) and event["event_id"]
        assert event["ts"].endswith("Z")
        assert event["actor"] == "aspen-sentinel"
        assert event["action"] == "capability.grant"
        assert event["target"] == "plant:chae-cell-01"
        assert event["result"] == "grant"

    def test_explicit_event_id_param_wins(self):
        event = build_event("a", "b", event_id="custom-id")
        assert event["event_id"] == "custom-id"

    def test_extra_fields_preserved(self):
        event = build_event("a", "b", request_id="req-1", capability="aspen.fleet.>")
        assert event["request_id"] == "req-1"
        assert event["capability"] == "aspen.fleet.>"

    def test_duplicate_event_id_from_none(self):
        a = build_event("a", "b")
        b = build_event("a", "b")
        assert a["event_id"] != b["event_id"]

    def test_from_event_maps_gatekeeper_legacy(self):
        event = AuditEventPublisher.from_event({
            "type": "capability.grant",
            "agent_id": "aspen-fleet-edge",
            "capability": "aspen.fleet.node.heartbeat:read",
            "request_id": "req-99",
        })
        assert event["actor"] == "aspen-fleet-edge"
        assert event["action"] == "capability.grant"
        assert event["target"] == ""
        assert event["result"] == "ok"
        assert event["capability"] == "aspen.fleet.node.heartbeat:read"
        assert event["request_id"] == "req-99"


# =========================================================================
# JSONL journal
# =========================================================================


class TestJsonlJournal:
    def test_record_always_writes_jsonl_offline(self, tmp_path):
        pub = _make_publisher(tmp_path)
        asyncio.run(pub.record("svc", "agent.run", "job-1", "ok"))
        lines = pub.audit_log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert set(REQUIRED_FIELDS).issubset(event)

    def test_tail_returns_newest_first(self, tmp_path):
        pub = _make_publisher(tmp_path)
        for i in range(5):
            asyncio.run(pub.record("svc", f"step.{i}", f"target-{i}", "ok"))
        tail = pub.tail(3)
        assert [e["action"] for e in tail] == ["step.4", "step.3", "step.2"]

    def test_query_filters(self, tmp_path):
        pub = _make_publisher(tmp_path)
        asyncio.run(pub.record("u1", "view", "doc-1", "ok"))
        asyncio.run(pub.record("u2", "edit", "doc-1", "deny"))
        asyncio.run(pub.record("u1", "edit", "doc-2", "ok"))
        matched = pub.query(actor="u1", result="ok")
        assert {e["target"] for e in matched} == {"doc-1", "doc-2"}
        denied = pub.query(result="deny")
        assert len(denied) == 1 and denied[0]["actor"] == "u2"

    def test_empty_journal_tail(self, tmp_path):
        pub = _make_publisher(tmp_path)
        assert pub.tail(10) == []
        assert pub.query() == []

    def test_record_sync_writes_jsonl(self, tmp_path):
        pub = _make_publisher(tmp_path)
        event = pub.record_sync("svc", "shim.action", "res-1", "deny")
        assert event["actor"] == "svc"
        assert pub.tail(1)[0]["event_id"] == event["event_id"]

    def test_record_event_sync_maps_legacy(self, tmp_path):
        pub = _make_publisher(tmp_path)
        event = pub.record_event_sync({
            "type": "capability.deny",
            "agent_id": "aspen-fleet-edge",
            "capability": "aspen.fleet.mission.start",
            "reason": "capability_not_granted",
        })
        stored = pub.tail(1)[0]
        assert stored["actor"] == "aspen-fleet-edge"
        assert stored["action"] == "capability.deny"
        assert stored["result"] == "ok"
        assert stored["capability"] == "aspen.fleet.mission.start"


# =========================================================================
# JetStream mirror (mocked NATS)
# =========================================================================


@pytest.fixture
def mock_jetstream():
    """Full mock NATS connection with an async JetStream context."""
    mock_nats_mod = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.is_connected = True
    mock_conn.drain = AsyncMock()
    mock_conn.close = AsyncMock()

    mock_js = MagicMock()
    mock_js.add_stream = AsyncMock()
    mock_js.publish = AsyncMock()

    mock_conn.jetstream = MagicMock(return_value=mock_js)
    mock_nats_mod.connect = AsyncMock(return_value=mock_conn)
    return mock_nats_mod, mock_conn, mock_js


@pytest.mark.asyncio
class TestJetStreamMirror:
    async def test_start_ensures_stream_and_connects(self, tmp_path, mock_jetstream):
        mock_nats_mod, mock_conn, mock_js = mock_jetstream
        pub = AuditEventPublisher(
            nats_url="nats://localhost:4222", audit_log=_make_log(tmp_path),
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            connected = await pub.start()
        assert connected is True
        assert pub.is_online is True
        mock_js.add_stream.assert_called_once()
        kwargs = mock_js.add_stream.call_args[1] or mock_js.add_stream.call_args.kwargs
        assert kwargs["name"] == "ASPEN_SENTINEL"
        assert "aspen.sentinel.>" in kwargs["subjects"]
        assert kwargs["storage"] == "file"
        await pub.close()

    async def test_start_offline_no_url(self, tmp_path):
        pub = AuditEventPublisher(audit_log=_make_log(tmp_path))
        assert await pub.start() is False
        assert pub.is_online is False

    async def test_record_publishes_to_audit_subject(self, tmp_path, mock_jetstream):
        mock_nats_mod, mock_conn, mock_js = mock_jetstream
        pub = AuditEventPublisher(
            nats_url="nats://localhost:4222", audit_log=_make_log(tmp_path),
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await pub.start()
            event = await pub.record("svc", "agent.run", "job-1", "ok")

        subject, payload = mock_js.publish.call_args[0]
        assert subject == SUBJECT_AUDIT_EVENT
        decoded = json.loads(payload.decode())
        assert decoded["event_id"] == event["event_id"]
        headers = mock_js.publish.call_args[1].get("headers") or mock_js.publish.call_args.kwargs.get("headers")
        assert headers == {"Nats-Msg-Id": event["event_id"]}
        # Journal still written even when online
        disk_event = json.loads(pub.audit_log_path.read_text().splitlines()[0])
        assert disk_event["event_id"] == event["event_id"]
        await pub.close()

    async def test_offline_records_buffer_and_replays(self, tmp_path, mock_jetstream):
        mock_nats_mod, mock_conn, mock_js = mock_jetstream
        pub = AuditEventPublisher(
            nats_url="nats://localhost:4222", audit_log=_make_log(tmp_path),
        )
        # No connect — offline: records buffer in memory
        await pub.record("svc", "a1", "t1", "ok")
        await pub.record("svc", "a2", "t2", "ok")
        assert pub.pending_count == 2
        assert len(pub.tail(10)) == 2  # durable on disk regardless

        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await pub.start()
            replayed = await pub.replay_pending()

        assert replayed == 2
        assert pub.pending_count == 0
        assert mock_js.publish.await_count == 2
        await pub.close()

    async def test_replay_is_idempotent_via_marker(self, tmp_path, mock_jetstream):
        mock_nats_mod, mock_conn, mock_js = mock_jetstream
        pub = AuditEventPublisher(
            nats_url="nats://localhost:4222", audit_log=_make_log(tmp_path),
        )
        await pub.record("svc", "a1", "t1", "ok")
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await pub.start()
            assert await pub.replay_pending() == 1
            marker = pub.audit_log_path.with_suffix(".jsonl.marker")
            assert marker.exists()
            await pub.close()

        # Second publisher on the same journal: no new events -> no republish
        pub2 = AuditEventPublisher(
            nats_url="nats://localhost:4222", audit_log=_make_log(tmp_path),
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await pub2.start()
            assert await pub2.replay_pending() == 0
            assert mock_js.publish.call_count == 1  # only the first replay's publish
            await pub2.close()

    async def test_js_last_pages_stream(self, tmp_path, mock_jetstream):
        mock_nats_mod, mock_conn, mock_js = mock_jetstream
        info = MagicMock()
        info.state.last_seq = 3
        info.state.first_seq = 1
        mock_js.stream_info = AsyncMock(return_value=info)
        mock_js.get_msg = AsyncMock()
        msg = MagicMock()
        msg.data = json.dumps({"event_id": "e3", "ts": "Z"}).encode()
        mock_js.get_msg.return_value = msg

        pub = AuditEventPublisher(
            nats_url="nats://localhost:4222", audit_log=_make_log(tmp_path),
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await pub.start()
            events = await pub.js_last(2)
        assert len(events) == 2
        assert events[0]["event_id"] == "e3"
        await pub.close()

    async def test_js_last_requires_online(self, tmp_path):
        pub = _make_publisher(tmp_path)
        with pytest.raises(RuntimeError):
            await pub.js_last(5)


# =========================================================================
# Gatekeeper shim wiring
# =========================================================================


class TestGatekeeperWiring:
    def test_log_audit_fans_into_publisher(self, tmp_path):
        from gatekeeper import AUDIT_LOG, minimal_shim
        AUDIT_LOG.clear()

        pub = _make_publisher(tmp_path)
        minimal_shim.set_audit_publisher(pub)
        try:
            minimal_shim.log_audit({"type": "capability.grant", "agent_id": "aspen-fleet-edge"})
        finally:
            minimal_shim.set_audit_publisher(None)

        # In-memory AUDIT_LOG unchanged (back-compat)
        assert any(e["type"] == "capability.grant" for e in AUDIT_LOG)
        # Durable JSONL trail got an ADR-0007 envelope
        stored = pub.tail(1)[0]
        assert stored["actor"] == "aspen-fleet-edge"
        assert stored["action"] == "capability.grant"
        assert set(REQUIRED_FIELDS).issubset(stored)
        AUDIT_LOG.clear()

    def test_set_audit_publisher_none_is_noop(self, tmp_path):
        from gatekeeper import minimal_shim
        minimal_shim.set_audit_publisher(None)
        minimal_shim.log_audit({"type": "capability.test"})  # must not raise


# =========================================================================
# CLI surface
# =========================================================================


class TestCliSurface:
    def test_subcommands_present(self):
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        try:
            import sentinel_audit_cli as cli_mod
        except ImportError:
            # scripts/sentinel-audit.py is not a module name; import by path
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "sentinel_audit_cli", os.path.join(REPO_ROOT, "scripts", "sentinel-audit.py"),
            )
            cli_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cli_mod)

        parser = cli_mod.build_parser()
        sub_actions = set(parser._subparsers._group_actions[0].choices.keys())
        for expected in ("emit", "tail", "query", "replay", "js-last", "check"):
            assert expected in sub_actions

    def test_cli_emit_and_tail_roundtrip(self, tmp_path):
        log_path = _make_log(tmp_path)
        env = dict(os.environ, ASPEN_AUDIT_LOG=log_path)
        script = os.path.join(REPO_ROOT, "scripts", "sentinel-audit.py")

        import subprocess

        emit = subprocess.run(
            [sys.executable, script, "emit", "--actor", "cli", "--action", "demo.run",
             "--target", "probe-1", "--result", "ok"],
            capture_output=True, text=True, env=env,
        )
        assert emit.returncode == 0, emit.stderr
        emitted = json.loads(emit.stdout)

        tail = subprocess.run(
            [sys.executable, script, "tail", "-n", "5", "--json"],
            capture_output=True, text=True, env=env,
        )
        assert tail.returncode == 0, tail.stderr
        events = json.loads(tail.stdout)
        assert events[0]["event_id"] == emitted["event_id"]
        assert events[0]["actor"] == "cli"
        assert events[0]["action"] == "demo.run"
        assert set(REQUIRED_FIELDS).issubset(events[0])