"""
Tests for the ADR-0009 gatekeeper dual-human authorization (ASP-540).

Covers the Phase-1 hardening DoD:
- Safety-adjacent proposal interception (aspen.safety.*, aspen.edge.*.command,
  aspen.fleet.mission.start) — never forwarded until authorized.
- Dual-human: two distinct human IDs via aspen.authz.gate.decision before a
  grant/forward; one human or a bare forward is refused.
- Every propose / authorize / duplicate / refuse / grant lands in the audit
  log and in an AuditEventPublisher JSONL journal (ADR-0007 envelope).
- NATS wiring: gate.decision subscription applies human approvals; non-human
  decision traffic is ignored; grants mirror to aspen.authz.capability.grant.
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

from gatekeeper.minimal_shim import (
    AUTH_WINDOW_SECONDS,
    DUAL_HUMAN_REQUIRED,
    PROPOSALS,
    _is_expired,
    _reset_rate_limits,
    authorize_gate_request,
    forward_proposal,
    is_safety_capability,
    request_capability,
    set_audit_publisher,
)
from gatekeeper.nats_client import NATSGateClient
from sentinel import AuditEventPublisher
from sentinel.audit import REQUIRED_FIELDS

SAFETY_CAP = "aspen.safety.estop:execute"
SAFE_CAPABILITY_STORE = [
    "aspen.safety.estop:execute",
    "aspen.edge.cell-01.command:write",
    "aspen.fleet.mission.start:execute",
]


@pytest.fixture(autouse=True)
def _clean_state():
    from gatekeeper import AUDIT_LOG

    AUDIT_LOG.clear()
    PROPOSALS.clear()
    _reset_rate_limits()
    set_audit_publisher(None)
    yield
    AUDIT_LOG.clear()
    PROPOSALS.clear()
    _reset_rate_limits()
    set_audit_publisher(None)


@pytest.fixture
def fleet_safety_store():
    """Grant aspen-fleet-edge the intercepted safety capabilities."""
    from gatekeeper import CAPABILITY_STORE

    store = CAPABILITY_STORE["aspen-fleet-edge"]
    added = [c for c in SAFE_CAPABILITY_STORE if c not in store]
    store.extend(added)
    yield
    for c in added:
        CAPABILITY_STORE["aspen-fleet-edge"].remove(c)


def _safety_request(capability=SAFETY_CAP):
    return request_capability(
        "aspen-fleet-edge",
        capability,
        "plant:chae-cell-01",
        {"profile": "full-plant"},
    )


# =========================================================================
# Safety subject classification
# =========================================================================


class TestSafetyClassification:
    def test_matches_doD_safety_subjects(self):
        assert is_safety_capability("aspen.safety.estop:execute")
        assert is_safety_capability("aspen.safety.any.thing:execute")
        assert is_safety_capability("aspen.edge.cell-01.command:write")
        assert is_safety_capability("aspen.edge.robot-a.command:execute")
        assert is_safety_capability("aspen.fleet.mission.start:execute")
        assert is_safety_capability("aspen.fleet.mission.start")

    def test_non_safety_capabilities_pass(self):
        assert not is_safety_capability("aspen.fleet.node.heartbeat:read")
        assert not is_safety_capability("aspen.sentinel.audit.event:read")
        assert not is_safety_capability("aspen.fleet.mission.status:read")
        assert not is_safety_capability("aspen.edge.cell-01.heartbeat:read")
        assert not is_safety_capability("aspen.fleet.mission.start_report")


# =========================================================================
# Proposal interception — never forward until authorized
# =========================================================================


class TestProposalInterception:
    def test_safety_request_returns_propose_act_no_token(self, fleet_safety_store):
        result = _safety_request()
        assert result["decision"] == "propose_act"
        assert result["requires"] == "dual_human"
        assert result["status"] == "awaiting_authorization"
        assert result["humans_required"] == DUAL_HUMAN_REQUIRED == 2
        assert result["humans"] == []
        assert "token" not in result  # no capability grant before authorization

    def test_safety_request_registers_pending_proposal(self, fleet_safety_store):
        result = _safety_request()
        proposal = PROPOSALS[result["request_id"]]
        assert proposal["state"] == "pending"
        assert proposal["humans"] == []
        assert proposal["capability"] == SAFETY_CAP
        assert proposal["resource"] == "plant:chae-cell-01"

    def test_bare_forward_never_passes(self, fleet_safety_store):
        result = _safety_request()
        outcome = forward_proposal(result["request_id"])
        assert outcome["decision"] == "refuse"
        assert outcome["reason"] == "insufficient_humans"
        assert PROPOSALS[result["request_id"]]["state"] == "refused"

    def test_each_safety_subject_is_intercepted(self, fleet_safety_store):
        for cap in SAFE_CAPABILITY_STORE:
            result = _safety_request(cap)
            assert result["decision"] == "propose_act", cap
            assert "token" not in result, cap


# =========================================================================
# Dual-human authorization threshold
# =========================================================================


class TestDualHumanThreshold:
    def test_single_human_never_grants(self, fleet_safety_store):
        result = _safety_request()
        req_id = result["request_id"]
        outcome = authorize_gate_request(req_id, "operator-1")
        assert outcome["decision"] == "awaiting"
        assert outcome["humans"] == ["operator-1"]
        assert outcome["humans_required"] == 2
        assert PROPOSALS[req_id]["state"] == "pending"

        forward = forward_proposal(req_id)
        assert forward["decision"] == "refuse"
        assert forward["reason"] == "insufficient_humans"
        assert forward["humans"] == ["operator-1"]

    def test_two_distinct_humans_grant(self, fleet_safety_store):
        result = _safety_request()
        req_id = result["request_id"]
        assert authorize_gate_request(req_id, "operator-1")["decision"] == "awaiting"
        outcome = authorize_gate_request(req_id, "operator-2")
        assert outcome["decision"] == "grant"
        assert outcome["humans"] == ["operator-1", "operator-2"]
        token = outcome["token"]
        assert "token_id" in token
        assert token["capability"] == SAFETY_CAP
        assert token["scope"] == "full-plant"
        assert "expires" in token
        assert token["authorized_by"] == ["operator-1", "operator-2"]
        assert PROPOSALS[req_id]["state"] == "granted"

    def test_same_human_twice_equals_one(self, fleet_safety_store):
        result = _safety_request()
        req_id = result["request_id"]
        assert authorize_gate_request(req_id, "operator-1")["decision"] == "awaiting"
        dup = authorize_gate_request(req_id, "operator-1")
        assert dup["decision"] == "awaiting"
        assert dup.get("note") == "duplicate_human_ignored"
        assert dup["humans"] == ["operator-1"]  # still only one distinct human
        forward = forward_proposal(req_id)
        assert forward["decision"] == "refuse"
        assert forward["reason"] == "insufficient_humans"

    def test_duplicate_then_second_human_grants(self, fleet_safety_store):
        result = _safety_request()
        req_id = result["request_id"]
        authorize_gate_request(req_id, "operator-1")
        authorize_gate_request(req_id, "operator-1")  # duplicate, ignored
        outcome = authorize_gate_request(req_id, "operator-2")
        assert outcome["decision"] == "grant"
        assert outcome["humans"] == ["operator-1", "operator-2"]

    def test_forward_after_grant_is_idempotent(self, fleet_safety_store):
        result = _safety_request()
        req_id = result["request_id"]
        authorize_gate_request(req_id, "operator-1")
        granted = authorize_gate_request(req_id, "operator-2")
        again = forward_proposal(req_id)
        assert again["decision"] == "grant"
        assert again["token"]["token_id"] == granted["token"]["token_id"]

    def test_refused_stays_refused(self, fleet_safety_store):
        result = _safety_request()
        req_id = result["request_id"]
        assert forward_proposal(req_id)["decision"] == "refuse"
        outcome = authorize_gate_request(req_id, "operator-1")
        assert outcome["decision"] == "refuse"
        assert PROPOSALS[req_id]["state"] == "refused"

    def test_expired_window_refused_on_auth_and_forward(self, fleet_safety_store):
        result = _safety_request()
        req_id = result["request_id"]
        proposal = PROPOSALS[req_id]
        proposal["expires_at"] = "2000-01-01T00:00:00Z"
        assert _is_expired(proposal)
        outcome = authorize_gate_request(req_id, "operator-1")
        assert outcome["decision"] == "refuse"
        assert outcome["reason"] == "authorization_window_expired"
        proposal = PROPOSALS[req_id]
        proposal["expires_at"] = "2000-01-01T00:00:00Z"
        forward = forward_proposal(req_id)
        assert forward["decision"] == "refuse"
        assert forward["reason"] == "authorization_window_expired"

    def test_unknown_request_refused(self, fleet_safety_store):
        outcome = authorize_gate_request("no-such-proposal", "operator-1")
        assert outcome["decision"] == "refuse"
        assert outcome["reason"] == "unknown_request"
        forward = forward_proposal("no-such-proposal")
        assert forward["decision"] == "refuse"
        assert forward["reason"] == "unknown_request"

    def test_auth_window_is_positive_and_finite(self):
        assert isinstance(AUTH_WINDOW_SECONDS, int)
        assert 60 <= AUTH_WINDOW_SECONDS <= 3600

    def test_missing_capability_still_denied(self, fleet_safety_store):
        from gatekeeper.minimal_shim import _handle_gate_request

        result = asyncio.run(
            _handle_gate_request(
                {
                    "agent_id": "aspen-fleet-edge",
                    "capability": "",
                    "resource": "plant:chae-cell-01",
                }
            )
        )
        assert result["decision"] == "deny"
        assert result["reason"] == "missing_capability"


# =========================================================================
# Audit trail — every decision lands in AUDIT_LOG + JSONL journal
# =========================================================================


class TestAuditCoverage:
    def _assert_envelope(self, event):
        for field in REQUIRED_FIELDS:
            assert field in event, f"missing {field}"

    def test_decisions_land_in_audit_log(self, fleet_safety_store):
        from gatekeeper import AUDIT_LOG

        result = _safety_request()
        req_id = result["request_id"]
        authorize_gate_request(req_id, "operator-1")
        authorize_gate_request(req_id, "operator-1")  # duplicate
        authorize_gate_request(req_id, "operator-2")
        forward_proposal(req_id)
        _safety_request("aspen.fleet.node.heartbeat:read")  # deny? no — grant
        request_capability(
            "aspen-unknown-agent", "aspen.fleet.mission.start", "plant:x", {}
        )

        types = [e["type"] for e in AUDIT_LOG]
        assert "propose_act.pending" in types
        assert "gate.authorize" in types
        assert "gate.authorize.duplicate" in types
        assert "capability.grant" in types
        assert "capability.deny" in types

    def test_decisions_land_in_sentinel_jsonl(self, tmp_path, fleet_safety_store):
        pub = AuditEventPublisher(audit_log=str(tmp_path / "audit.jsonl"))
        set_audit_publisher(pub)
        try:
            result = _safety_request()
            req_id = result["request_id"]
            authorize_gate_request(req_id, "operator-1")
            authorize_gate_request(req_id, "operator-1")  # duplicate
            authorize_gate_request(req_id, "operator-2")  # grant
        finally:
            set_audit_publisher(None)

        events = pub.read_events()
        actions = {e["action"] for e in events}
        assert "propose_act.pending" in actions
        assert "gate.authorize" in actions
        assert "gate.authorize.duplicate" in actions
        assert "capability.grant" in actions

        for event in events:
            self._assert_envelope(event)
            assert event["ts"].endswith("Z")

        human_auths = [e for e in events if e["action"] == "gate.authorize"]
        assert {e["actor"] for e in human_auths} == {"operator-1", "operator-2"}
        assert any(
            e["action"] == "gate.authorize.duplicate" and e["actor"] == "operator-1"
            for e in events
        )

        grant = next(e for e in events if e["action"] == "capability.grant")
        assert grant["actor"] == "aspen-fleet-edge"
        assert grant["target"] == "plant:chae-cell-01"
        assert grant["result"] == "grant"


# =========================================================================
# NATS wiring — gate.decision human authorizations
# =========================================================================


@pytest.mark.asyncio
class TestNATSDecisionWiring:
    async def test_handle_gate_decision_happy_path(self, fleet_safety_store):
        from gatekeeper.minimal_shim import _handle_gate_decision

        proposed = _safety_request()
        req_id = proposed["request_id"]

        first = await _handle_gate_decision({"request_id": req_id, "human_id": "op-a"})
        assert first["decision"] == "awaiting"
        second = await _handle_gate_decision(
            {"request_id": req_id, "human_id": "op-b", "note": "approved"}
        )
        assert second["decision"] == "grant"
        assert second["humans"] == ["op-a", "op-b"]

    async def test_handle_gate_decision_ignores_non_human(self, fleet_safety_store):
        from gatekeeper.minimal_shim import _handle_gate_decision

        assert (
            await _handle_gate_decision({"request_id": "x", "decision": "grant"})
            is None
        )
        assert await _handle_gate_decision({"human_id": "op-a"}) is None
        assert await _handle_gate_decision({}) is None

    async def test_decision_subscription_applies_human_approval(
        self, fleet_safety_store
    ):
        mock_nats_mod = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.is_connected = True
        mock_conn.publish = AsyncMock()
        mock_conn.subscribe = AsyncMock()
        mock_conn.drain = AsyncMock()
        mock_conn.close = AsyncMock()
        mock_conn.jetstream = MagicMock()
        mock_nats_mod.connect = AsyncMock(return_value=mock_conn)

        from gatekeeper.minimal_shim import _handle_gate_decision

        proposed = _safety_request()
        req_id = proposed["request_id"]

        client = NATSGateClient(
            nats_url="nats://localhost:4222",
            request_handler=lambda d: {"decision": "deny"},
            decision_handler=_handle_gate_decision,
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await client.connect()

        subscribed = {c[0][0] for c in mock_conn.subscribe.call_args_list}
        assert "aspen.authz.gate.request" in subscribed
        assert "aspen.authz.gate.decision" in subscribed

        def _cb_for(subject):
            for i, c in enumerate(mock_conn.subscribe.call_args_list):
                if c[0][0] == subject:
                    return c[1]["cb"]
            return None

        # Fist human approval drives an awaiting response, nothing on grant.
        cb = _cb_for("aspen.authz.gate.decision")
        fake = MagicMock()
        fake.data = json.dumps({"request_id": req_id, "human_id": "op-a"}).encode()
        await cb(fake)
        last = mock_conn.publish.call_args_list[-1]
        assert last[0][0] == "aspen.authz.gate.decision"
        assert json.loads(last[0][1].decode())["decision"] == "awaiting"

        # Second distinct human → grant token mirrored to capability.grant.
        fake2 = MagicMock()
        fake2.data = json.dumps({"request_id": req_id, "human_id": "op-b"}).encode()
        await cb(fake2)
        subjects = [c[0][0] for c in mock_conn.publish.call_args_list]
        assert "aspen.authz.capability.grant" in subjects
        grant_pub = next(
            c
            for c in mock_conn.publish.call_args_list
            if c[0][0] == "aspen.authz.capability.grant"
        )
        grant = json.loads(grant_pub[0][1].decode())
        assert grant["agent_id"] == "aspen-fleet-edge"
        assert grant["caps"] == [SAFETY_CAP]
        assert grant["scope"] == "full-plant"

        await client.close()

    async def test_decision_subscription_ignores_own_emits(self, fleet_safety_store):
        """Gatekeeper emits (no singular human_id) never register as approvals."""
        mock_nats_mod = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.is_connected = True
        mock_conn.publish = AsyncMock()
        mock_conn.subscribe = AsyncMock()
        mock_conn.drain = AsyncMock()
        mock_conn.close = AsyncMock()
        mock_conn.jetstream = MagicMock()
        mock_nats_mod.connect = AsyncMock(return_value=mock_conn)

        captured = []

        async def spy_decision_handler(data):
            captured.append(data)

        client = NATSGateClient(
            nats_url="nats://localhost:4222",
            decision_handler=spy_decision_handler,
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await client.connect()

        cb = None
        for i, c in enumerate(mock_conn.subscribe.call_args_list):
            if c[0][0] == "aspen.authz.gate.decision":
                cb = c[1]["cb"]
        assert cb is not None

        own_emit = MagicMock()
        own_emit.data = json.dumps(
            {
                "request_id": "r1",
                "decision": "propose_act",
                "humans": ["a", "b"],
            }
        ).encode()
        await cb(own_emit)
        assert captured == []  # no human_id → never handled

        await client.close()
