"""
Tests for ADR-0012 operator-of-record binding (ASP-777).

Covers:
- Light-cell (sim) profile: free-string human_id passes without registry
- Full-plant profile: registered active operator passes
- Full-plant profile: unregistered human_id is refused
- Full-plant profile: revoked operator is refused
- Missing/corrupt registry on non-sim: fail-closed refusal
"""

import json
import os
import sys
import tempfile

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PYTHON = os.path.join(REPO_ROOT, "src", "python")
sys.path.insert(0, SRC_PYTHON)

from gatekeeper.minimal_shim import (
    AUDIT_LOG,
    DUAL_HUMAN_REQUIRED,
    PROPOSALS,
    _check_operator_binding,
    _reset_rate_limits,
    authorize_gate_request,
    request_capability,
    set_audit_publisher,
)
from services.operator_registry import OperatorRegistry


@pytest.fixture(autouse=True)
def _clean_state():
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
def operator_registry_path(tmp_path):
    return str(tmp_path / "operators.json")


@pytest.fixture
def registered_registry(operator_registry_path):
    reg = OperatorRegistry(db_path=operator_registry_path)
    reg.enroll("op-alice", "Alice Smith", plant_id="chae-cell-01")
    reg.enroll("op-bob", "Bob Jones", plant_id="chae-cell-01")
    reg.enroll("op-revoked", "Charlie Revoked", plant_id="chae-cell-01")
    reg.revoke("op-revoked")
    return operator_registry_path


def _make_proposal(request_id="req-001", profile="light-cell"):
    """Create a minimal proposal in PROPOSALS for testing."""
    from datetime import datetime, timedelta, timezone
    expires = (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat().replace("+00:00", "Z")
    PROPOSALS[request_id] = {
        "request_id": request_id,
        "agent_id": "aspen-fleet-edge",
        "capability": "aspen.safety.estop:execute",
        "resource": "plant:chae-cell-01",
        "profile": profile,
        "state": "pending",
        "humans": [],
        "expires_at": expires,
    }


class TestCheckOperatorBinding:
    def test_light_cell_always_passes(self):
        assert _check_operator_binding("any-free-string", "light-cell") is None

    def test_light_cell_empty_string_passes(self):
        assert _check_operator_binding("", "light-cell") is None

    def test_non_sim_registered_active_passes(self, registered_registry):
        with tempenv("ASPEN_OPERATOR_REGISTRY", registered_registry):
            assert _check_operator_binding("op-alice", "full-plant") is None

    def test_non_sim_registered_active_other_profile(self, registered_registry):
        with tempenv("ASPEN_OPERATOR_REGISTRY", registered_registry):
            assert _check_operator_binding("op-alice", "edge-cell") is None

    def test_non_sim_unregistered_refused(self, registered_registry):
        with tempenv("ASPEN_OPERATOR_REGISTRY", registered_registry):
            reason = _check_operator_binding("op-no-such", "full-plant")
            assert reason == "operator_not_registered"

    def test_non_sim_revoked_refused(self, registered_registry):
        with tempenv("ASPEN_OPERATOR_REGISTRY", registered_registry):
            reason = _check_operator_binding("op-revoked", "full-plant")
            assert reason == "operator_not_active"

    def test_non_sim_missing_registry_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "no-such-file.json")
            with tempenv("ASPEN_OPERATOR_REGISTRY", path):
                reason = _check_operator_binding("op-alice", "full-plant")
                assert reason == "operator_not_registered"

    def test_non_sim_corrupt_registry_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "corrupt.json")
            with open(path, "w") as f:
                f.write("not json")
            with tempenv("ASPEN_OPERATOR_REGISTRY", path):
                reason = _check_operator_binding("op-alice", "full-plant")
                assert reason == "operator_not_registered"


class TestAuthorizeGateRequestBinding:
    def test_light_cell_unregistered_passes(self):
        _make_proposal("req-light", profile="light-cell")
        result = authorize_gate_request("req-light", "unregistered-operator")
        assert result["decision"] == "awaiting"

    def test_non_sim_registered_passes(self, registered_registry):
        _make_proposal("req-registered", profile="full-plant")
        with tempenv("ASPEN_OPERATOR_REGISTRY", registered_registry):
            result = authorize_gate_request("req-registered", "op-alice")
        assert result["decision"] == "awaiting"

    def test_non_sim_unregistered_refused(self, registered_registry):
        _make_proposal("req-unreg", profile="full-plant")
        with tempenv("ASPEN_OPERATOR_REGISTRY", registered_registry):
            result = authorize_gate_request("req-unreg", "no-such-op")
        assert result["decision"] == "refuse"
        assert result["reason"] == "operator_not_registered"

    def test_non_sim_revoked_refused(self, registered_registry):
        _make_proposal("req-revoked", profile="full-plant")
        with tempenv("ASPEN_OPERATOR_REGISTRY", registered_registry):
            result = authorize_gate_request("req-revoked", "op-revoked")
        assert result["decision"] == "refuse"
        assert result["reason"] == "operator_not_active"

    def test_dual_human_both_registered_grants(self, registered_registry):
        _make_proposal("req-dual", profile="full-plant")
        with tempenv("ASPEN_OPERATOR_REGISTRY", registered_registry):
            r1 = authorize_gate_request("req-dual", "op-alice")
            assert r1["decision"] == "awaiting"
            r2 = authorize_gate_request("req-dual", "op-bob")
            assert r2["decision"] == "grant"

    def test_audit_log_on_refuse(self, registered_registry):
        _make_proposal("req-audit", profile="full-plant")
        with tempenv("ASPEN_OPERATOR_REGISTRY", registered_registry):
            authorize_gate_request("req-audit", "no-such-op")
        matching = [e for e in AUDIT_LOG if e.get("type") == "gate.operator_binding.refuse"]
        assert len(matching) == 1
        assert matching[0]["reason"] == "operator_not_registered"
        assert matching[0]["actor"] == "no-such-op"

    def test_light_cell_dual_human_free_string_grants(self):
        _make_proposal("req-light-dual", profile="light-cell")
        r1 = authorize_gate_request("req-light-dual", "alice")
        assert r1["decision"] == "awaiting"
        r2 = authorize_gate_request("req-light-dual", "bob")
        assert r2["decision"] == "grant"
        assert len([e for e in AUDIT_LOG if e.get("type") == "gate.operator_binding.refuse"]) == 0


class TestFullFlowRequestCapability:
    def test_safety_cap_light_cell_accepts_unregistered_authorizer(self):
        """End-to-end: propose_act on light-cell, authorize with free-string."""
        from gatekeeper import CAPABILITY_STORE
        store = CAPABILITY_STORE["aspen-fleet-edge"]
        safe_caps = ["aspen.safety.estop:execute"]
        for c in safe_caps:
            if c not in store:
                store.append(c)

        try:
            result = request_capability(
                "aspen-fleet-edge",
                "aspen.safety.estop:execute",
                "plant:chae-cell-01",
                {"profile": "light-cell"},
            )
            assert result["decision"] == "propose_act"
            req_id = result["request_id"]

            r1 = authorize_gate_request(req_id, "free-string-alice")
            assert r1["decision"] == "awaiting"

            r2 = authorize_gate_request(req_id, "free-string-bob")
            assert r2["decision"] == "grant"
        finally:
            for c in safe_caps:
                if c in store:
                    store.remove(c)

    def test_safety_cap_full_plant_refuses_unregistered(self, registered_registry):
        """End-to-end: propose_act on full-plant, unregistered authorizer is refused."""
        from gatekeeper import CAPABILITY_STORE
        store = CAPABILITY_STORE["aspen-fleet-edge"]
        safe_caps = ["aspen.fleet.mission.start:execute"]
        for c in safe_caps:
            if c not in store:
                store.append(c)

        try:
            with tempenv("ASPEN_OPERATOR_REGISTRY", registered_registry):
                result = request_capability(
                    "aspen-fleet-edge",
                    "aspen.fleet.mission.start:execute",
                    "plant:chae-cell-01",
                    {"profile": "full-plant"},
                )
                assert result["decision"] == "propose_act"
                req_id = result["request_id"]

                r1 = authorize_gate_request(req_id, "no-such-op")
                assert r1["decision"] == "refuse"
                assert r1["reason"] == "operator_not_registered"
        finally:
            for c in safe_caps:
                if c in store:
                    store.remove(c)


@pytest.fixture
def _hitl_tmp_paths(tmp_path):
    """Mirror the hitl fixture from test_gatekeeper_dual_human so vault-gated tests pass."""
    old_db = os.environ.get("HITL_DB")
    old_vault = os.environ.get("HITL_VAULT_DIR")
    os.environ["HITL_DB"] = str(tmp_path / "hitl.db")
    os.environ["HITL_VAULT_DIR"] = str(tmp_path / "vault")
    yield
    if old_db is None:
        os.environ.pop("HITL_DB", None)
    else:
        os.environ["HITL_DB"] = old_db
    if old_vault is None:
        os.environ.pop("HITL_VAULT_DIR", None)
    else:
        os.environ["HITL_VAULT_DIR"] = old_vault





# ---------------------------------------------------------------------------
# Helper context manager for env var
# ---------------------------------------------------------------------------
from contextlib import contextmanager


@contextmanager
def tempenv(key: str, value: str):
    old = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old