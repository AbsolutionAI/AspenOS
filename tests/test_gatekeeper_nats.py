"""
Tests for ADR-0009 Gatekeeper — NATS wire (ASP-531).

Covers:
- Core decision engine: grant / deny / propose_act paths
- NATS client: publish helpers work with mock NATS
- NATS client: offline fallback buffers events
- NATS client: request handler callback delegates correctly
- Audit event publishing through the NATS client
"""

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src/python to sys.path for local imports
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PYTHON = os.path.join(REPO_ROOT, "src", "python")
sys.path.insert(0, SRC_PYTHON)

# Module-level fixtures — these survive across tests
GATEKEEPER = None


def _import_gatekeeper():
    """Import the gatekeeper module (once, with side effects)."""
    global GATEKEEPER
    if GATEKEEPER is None:
        from gatekeeper import (
            request_capability,
            log_audit,
            AUDIT_LOG,
            CAPABILITY_STORE,
            NATSGateClient,
            minimal_shim,
        )
        GATEKEEPER = {
            "request_capability": request_capability,
            "log_audit": log_audit,
            "AUDIT_LOG": AUDIT_LOG,
            "CAPABILITY_STORE": CAPABILITY_STORE,
            "NATSGateClient": NATSGateClient,
            "minimal_shim": minimal_shim,
        }
        # Clear audit log from previous runs
        AUDIT_LOG.clear()
    return GATEKEEPER


def _reset_audit_log():
    from gatekeeper import AUDIT_LOG, minimal_shim
    AUDIT_LOG.clear()
    minimal_shim._OFFLINE_BUFFER.clear()


# =========================================================================
# Decision Engine Tests
# =========================================================================


class TestDecisionEngine:
    """Tests for the core request_capability() function."""

    def setup_method(self):
        gk = _import_gatekeeper()
        from gatekeeper import AUDIT_LOG
        AUDIT_LOG.clear()

    def test_grant_known_capability(self):
        """A known agent with a matching capability should get a grant."""
        gk = _import_gatekeeper()
        result = gk["request_capability"](
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        assert result["decision"] == "grant"
        assert "token" in result
        assert result["token"]["agent_id"] == "aspen-fleet-edge"
        assert result["token"]["capability"] == "aspen.fleet.node.heartbeat:read"
        assert "expires" in result["token"]
        assert "token_id" in result["token"]

    def test_grant_wildcard_capability(self):
        """A capability store entry ending with '.*' should match sub-paths."""
        gk = _import_gatekeeper()
        result = gk["request_capability"](
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        assert result["decision"] == "grant"

        # Verify wildcards work: aspen-sentinel has aspen.sentinel.*:read
        result2 = gk["request_capability"](
            "aspen-sentinel",
            "aspen.sentinel.audit.event:read",
            "plant:sentinel-01",
            {"profile": "full-plant"},
        )
        assert result2["decision"] == "grant"

    def test_deny_unknown_agent(self):
        """An agent not in the capability store should be denied."""
        gk = _import_gatekeeper()
        result = gk["request_capability"](
            "aspen-unknown-agent",
            "aspen.fleet.mission.start",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        assert result["decision"] == "deny"
        assert "reason" in result

    def test_deny_insufficient_capability(self):
        """A known agent requesting an unassigned capability should be denied."""
        gk = _import_gatekeeper()
        # aspen-fleet-edge does NOT have aspen.fleet.mission.start
        result = gk["request_capability"](
            "aspen-fleet-edge",
            "aspen.fleet.mission.start",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        assert result["decision"] == "deny"

    def test_propose_act_for_safety(self):
        """Safety-adjacent capabilities should return propose_act."""
        gk = _import_gatekeeper()
        # aspen-sentinel has aspen.sentinel.*:read but aspen.safety.estop is NOT in its store
        # So it will be denied first. Let's use aspen-fleet-edge which has heartbeat:read
        # but aspen.safety.estop is not in its store either.
        # Actually, the SAFETY_SUBJECTS check happens BEFORE the capability check.
        # Wait, no - looking at the code: capability check first, then safety check.
        # Let me check what happens with aspen-fleet-edge requesting a safety action.

        # Actually the safety check is AFTER the capability check. So if the agent
        # doesn't have the capability at all, it's denied before we check if it's safety-adjacent.
        # Let me use an agent that HAS the capability in question.
        # For the propose_act test, we need an agent + capability that:
        # 1. Passes the cap check
        # 2. Triggers the safety check
        # aspen-fleet-edge has "aspen.edge.*.propose_act:write" which would match
        # but aspen.safety.estop:execute is not in its store, so it gets denied.
        # Let me just verify that propose_act is returned when capability matches
        # and safety subjects check triggers.

        # Since the capability store does NOT have a safety capability for any agent,
        # all safety requests will be denied at the capability check.
        # Let me add one temporarily to test the propose_act path.
        original_store = dict(gk["CAPABILITY_STORE"])
        gk["CAPABILITY_STORE"]["aspen-fleet-edge"].append("aspen.safety.estop:execute")
        result = gk["request_capability"](
            "aspen-fleet-edge",
            "aspen.safety.estop:execute",
            "plant:chae-cell-01",
            {"profile": "full-plant"},
        )
        assert result["decision"] == "propose_act"
        assert result["requires"] == "dual_human"
        # Restore
        gk["CAPABILITY_STORE"]["aspen-fleet-edge"].remove("aspen.safety.estop:execute")

    def test_audit_log_entries(self):
        """Each decision should produce an audit log entry."""
        gk = _import_gatekeeper()
        from gatekeeper import AUDIT_LOG
        AUDIT_LOG.clear()

        gk["request_capability"](
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        # Should have at least one audit entry (the grant)
        assert len(AUDIT_LOG) >= 1
        assert AUDIT_LOG[0]["type"] == "capability.grant"

    def test_token_scoped_by_profile(self):
        """Token scope should match the requested profile."""
        gk = _import_gatekeeper()
        result = gk["request_capability"](
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        assert result["token"]["scope"] == "light-cell"

        result2 = gk["request_capability"](
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "full-plant"},
        )
        assert result2["token"]["scope"] == "full-plant"


# =========================================================================
# NATSClient Unit Tests (with mocked NATS)
# =========================================================================


@pytest.fixture
def mock_nats():
    """Provide a mock nats module patched into NATSGateClient."""
    mock_nats_mod = MagicMock()
    mock_connection = AsyncMock()
    mock_connection.is_connected = True
    mock_connection.publish = AsyncMock()
    mock_connection.subscribe = AsyncMock()
    mock_connection.drain = AsyncMock()
    mock_connection.close = AsyncMock()
    mock_connection.jetstream = MagicMock()
    mock_nats_mod.connect = AsyncMock(return_value=mock_connection)
    return mock_nats_mod, mock_connection


class TestNATSGateClient:
    """Tests for the NATS client wrapper."""

    @pytest.mark.asyncio
    async def test_connect_online(self, mock_nats):
        """Connecting with a valid URL should succeed."""
        mock_nats_mod, mock_conn = mock_nats
        from gatekeeper.nats_client import NATSGateClient

        client = NATSGateClient(nats_url="nats://localhost:4222")

        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            connected = await client.connect()

        assert connected is True
        assert client.is_online is True
        mock_nats_mod.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_offline_no_url(self):
        """Connecting with no URL should stay in offline mode."""
        from gatekeeper.nats_client import NATSGateClient

        client = NATSGateClient(nats_url=None)
        connected = await client.connect()

        assert connected is False
        assert client.is_online is False

    @pytest.mark.asyncio
    async def test_publish_audit_online(self, mock_nats):
        """publish_audit should call NATS publish with correct subject."""
        mock_nats_mod, mock_conn = mock_nats
        from gatekeeper.nats_client import NATSGateClient

        client = NATSGateClient(nats_url="nats://localhost:4222")

        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await client.connect()
            await client.publish_audit({
                "type": "capability.grant",
                "request_id": "test-req-1",
                "agent_id": "aspen-fleet-edge",
            })

        mock_conn.publish.assert_called_once()
        subject, data = mock_conn.publish.call_args[0]
        assert subject == "aspen.sentinel.audit.event"
        payload = json.loads(data.decode())
        assert payload["type"] == "capability.grant"
        assert "ts" in payload

    @pytest.mark.asyncio
    async def test_publish_decision_online(self, mock_nats):
        """publish_decision should go to aspen.authz.gate.decision."""
        mock_nats_mod, mock_conn = mock_nats
        from gatekeeper.nats_client import NATSGateClient

        client = NATSGateClient(nats_url="nats://localhost:4222")

        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await client.connect()
            await client.publish_decision(
                request_id="test-req-1",
                decision="grant",
                humans=["operator-1"],
                note="Approved",
            )

        subject, data = mock_conn.publish.call_args[0]
        assert subject == "aspen.authz.gate.decision"
        payload = json.loads(data.decode())
        assert payload["request_id"] == "test-req-1"
        assert payload["decision"] == "grant"
        assert payload["humans"] == ["operator-1"]
        assert payload["note"] == "Approved"

    @pytest.mark.asyncio
    async def test_publish_grant_online(self, mock_nats):
        """publish_grant should go to aspen.authz.capability.grant."""
        mock_nats_mod, mock_conn = mock_nats
        from gatekeeper.nats_client import NATSGateClient

        client = NATSGateClient(nats_url="nats://localhost:4222")

        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await client.connect()
            await client.publish_grant(
                agent_id="aspen-fleet-edge",
                caps=["aspen.fleet.node.heartbeat:read"],
                expires="2026-09-01T00:00:00Z",
                scope="light-cell",
            )

        subject, data = mock_conn.publish.call_args[0]
        assert subject == "aspen.authz.capability.grant"
        payload = json.loads(data.decode())
        assert payload["agent_id"] == "aspen-fleet-edge"
        assert len(payload["caps"]) == 1
        assert payload["scope"] == "light-cell"
        assert payload["expires"] == "2026-09-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_offline_buffer(self, mock_nats):
        """When offline, events should buffer locally and flush on reconnect."""
        mock_nats_mod, mock_conn = mock_nats
        from gatekeeper.nats_client import NATSGateClient

        client = NATSGateClient(nats_url="nats://localhost:4222")

        # Don't connect — stay offline
        await client.publish_audit({"type": "capability.grant", "request_id": "offline-test"})
        assert client.offline_buffer_size >= 1

        # Now connect — _flush_offline_buffer runs inside connect()
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await client.connect()
            # Buffer should be flushed automatically during connect
            assert client.offline_buffer_size == 0
        assert client.is_online is True

    @pytest.mark.asyncio
    async def test_request_handler_callback(self, mock_nats):
        """The request handler should be called when gate.request messages arrive."""
        mock_nats_mod, mock_conn = mock_nats

        # Simulate the subscribe callback
        captured = []

        async def handler(data):
            captured.append(data)
            return {"decision": "grant", "request_id": "handled-1", "token": {"cap": "test"}}

        from gatekeeper.nats_client import NATSGateClient

        client = NATSGateClient(
            nats_url="nats://localhost:4222",
            request_handler=handler,
        )

        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await client.connect()

        # Verify subscribe was called with the right subject
        mock_conn.subscribe.assert_called_once()
        subject = mock_conn.subscribe.call_args[0][0]
        assert subject == "aspen.authz.gate.request"

        # Now simulate a NATS message arriving
        sub_cb = mock_conn.subscribe.call_args[1]["cb"]
        fake_msg = MagicMock()
        fake_msg.data = json.dumps({
            "agent_id": "aspen-fleet-edge",
            "capability": "aspen.fleet.node.heartbeat:read",
            "resource": "plant:chae-cell-01",
            "context": {"profile": "light-cell"},
        }).encode()

        await sub_cb(fake_msg)

        # Handler should have been called
        assert len(captured) == 1
        assert captured[0]["capability"] == "aspen.fleet.node.heartbeat:read"

        # Decision should have been published
        assert mock_conn.publish.called
        # The last publish call should be the decision
        last_args = mock_conn.publish.call_args_list[-1]
        last_subject = last_args[0][0]
        assert last_subject == "aspen.authz.gate.decision"

    @pytest.mark.asyncio
    async def test_close_cleanup(self, mock_nats):
        """Close should drain and close NATS connection."""
        mock_nats_mod, mock_conn = mock_nats
        from gatekeeper.nats_client import NATSGateClient

        client = NATSGateClient(nats_url="nats://localhost:4222")

        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await client.connect()
            await client.close()

        mock_conn.drain.assert_called_once()
        mock_conn.close.assert_called_once()
        assert client.is_online is False


# =========================================================================
# Integration: Shim + NATS Client
# =========================================================================


class TestShimNATSIntegration:
    """Tests that the shim and NATS client work together."""

    def test_log_audit_with_nats_client(self):
        """log_audit should use the NATS client when one is registered."""
        gk = _import_gatekeeper()
        from gatekeeper import minimal_shim, AUDIT_LOG
        AUDIT_LOG.clear()

        # Register a mock NATS client
        mock_client = MagicMock()
        mock_client.publish_audit = AsyncMock()
        minimal_shim.set_nats_client(mock_client)

        # Call log_audit
        minimal_shim.log_audit({"type": "capability.test", "request_id": "integ-test"})

        # Local buffer should have the entry
        assert any(e["type"] == "capability.test" for e in AUDIT_LOG)

        # Clean up
        minimal_shim.set_nats_client(None)
        AUDIT_LOG.clear()

    def test_request_capability_produces_audit(self):
        """Every request_capability call should produce an audit log entry."""
        gk = _import_gatekeeper()
        from gatekeeper import AUDIT_LOG
        AUDIT_LOG.clear()

        gk["request_capability"](
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        types = [e["type"] for e in AUDIT_LOG]
        assert "capability.grant" in types

        AUDIT_LOG.clear()
        gk["request_capability"](
            "aspen-unknown-agent",
            "aspen.fleet.mission.start",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        types = [e["type"] for e in AUDIT_LOG]
        assert "capability.deny" in types

    @pytest.mark.asyncio
    async def test_handle_gate_request_delegates_to_decision_engine(self):
        """The _handle_gate_request callback should call request_capability."""
        gk = _import_gatekeeper()
        from gatekeeper import minimal_shim, AUDIT_LOG
        AUDIT_LOG.clear()

        result = await minimal_shim._handle_gate_request({
            "agent_id": "aspen-fleet-edge",
            "capability": "aspen.fleet.node.heartbeat:read",
            "resource": "plant:chae-cell-01",
            "context": {"profile": "light-cell"},
        })
        assert result["decision"] == "grant"
        assert "token" in result

    @pytest.mark.asyncio
    async def test_handle_gate_request_propose_act_path(self):
        """The handler should return propose_act for safety-adjacent caps."""
        gk = _import_gatekeeper()
        from gatekeeper import minimal_shim, AUDIT_LOG
        AUDIT_LOG.clear()

        # Temporarily add a safety capability to the store
        gk["CAPABILITY_STORE"]["aspen-fleet-edge"].append("aspen.fleet.mission.start:execute")
        result = await minimal_shim._handle_gate_request({
            "agent_id": "aspen-fleet-edge",
            "capability": "aspen.fleet.mission.start:execute",
            "resource": "plant:chae-cell-01",
            "context": {"profile": "full-plant"},
        })
        assert result["decision"] == "propose_act"
        gk["CAPABILITY_STORE"]["aspen-fleet-edge"].remove("aspen.fleet.mission.start:execute")

    @pytest.mark.asyncio
    async def test_handle_gate_request_denies_missing_capability(self):
        """A request with no capability field should be denied."""
        gk = _import_gatekeeper()
        from gatekeeper import minimal_shim

        result = await minimal_shim._handle_gate_request({
            "agent_id": "aspen-fleet-edge",
            "capability": "",
            "resource": "plant:chae-cell-01",
            "context": {"profile": "light-cell"},
        })
        assert result["decision"] == "deny"
        assert result["reason"] == "missing_capability"


# =========================================================================
# Smoke — standalone shim demo
# =========================================================================


class TestShimStandalone:
    """Tests for the standalone demo mode."""

    def test_shim_imports_and_runs(self):
        """The shim should run as a module without error."""
        gk = _import_gatekeeper()
        from gatekeeper import minimal_shim

        # Run the core decision engine (the demo part of the shim)
        minimal_shim.request_capability(
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        # No exception = pass


if __name__ == "__main__":
    pytest.main(["-v", __file__])