"""
Gatekeeper durable vault approval gate for physical cell acts (H-022 / ASP-432).

A physical cell act (e.g. ``aspen.edge.cell-01.act``) is granted only after:
- two *distinct* humans authorize on ``aspen.authz.gate.decision``, AND
- the durable HITL vault approval record exists with status ``approved``.

All tests are hermetic: ``HITL_DB`` / ``HITL_VAULT_DIR`` point at per-test tmp
dirs, no real hardware is touched, and ``ASPEN_SIM`` is never required.
"""

import os
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PYTHON = os.path.join(REPO_ROOT, "src", "python")
sys.path.insert(0, SRC_PYTHON)

from gatekeeper import AUDIT_LOG, CAPABILITY_STORE  # noqa: E402
from gatekeeper.minimal_shim import (  # noqa: E402
    DUAL_HUMAN_REQUIRED,
    PROPOSALS,
    _reset_rate_limits,
    authorize_gate_request,
    forward_proposal,
    is_physical_cell_act,
    is_safety_capability,
    request_capability,
)
from gatekeeper import vault_gate  # noqa: E402

PHYSICAL_CAP = "aspen.edge.cell-01.act:execute"
PLAIN_CELL_CAP = "aspen.safety.estop:execute"  # safety but NOT a physical act


@pytest.fixture(autouse=True)
def _hitl_tmp_paths(tmp_path):
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


@pytest.fixture(autouse=True)
def _clean_state():
    AUDIT_LOG.clear()
    PROPOSALS.clear()
    _reset_rate_limits()
    yield
    AUDIT_LOG.clear()
    PROPOSALS.clear()
    _reset_rate_limits()


@pytest.fixture
def physical_store():
    added = [c for c in (PHYSICAL_CAP, PLAIN_CELL_CAP) if c not in CAPABILITY_STORE["aspen-fleet-edge"]]
    CAPABILITY_STORE["aspen-fleet-edge"].extend(added)
    yield
    for c in added:
        CAPABILITY_STORE["aspen-fleet-edge"].remove(c)


def _physical_request(profile="full-plant"):
    return request_capability(
        "aspen-fleet-edge",
        PHYSICAL_CAP,
        "plant:chae-cell-01",
        {"profile": profile},
    )


def _approve_vault_for(hitl_request_id, decided_by="op-1"):
    vault_gate.make_vault().approve(hitl_request_id, decided_by=decided_by, reason="plant clear")


# =========================================================================
# Physical cell act classification
# =========================================================================


class TestPhysicalClassification:
    def test_physical_act_subjects_match(self):
        assert is_physical_cell_act("aspen.edge.cell-01.act:execute", "full-plant")
        assert is_physical_cell_act("aspen.edge.robot-a.act:execute", "full-plant")
        assert is_physical_cell_act("aspen.safety.estop.act:execute", "full-plant")
        assert is_physical_cell_act("aspen.edge.cell-01.command:write", "full-plant")

    def test_physical_is_also_safety(self):
        assert is_safety_capability("aspen.edge.cell-01.act:execute")
        assert is_safety_capability("aspen.safety.estop.act:execute")

    def test_non_physical_capabilities_do_not_match(self):
        # Estop keeps the plan dual-human path (must stay fast).
        assert not is_physical_cell_act("aspen.safety.estop:execute", "full-plant")
        assert not is_physical_cell_act("aspen.fleet.mission.start:execute", "full-plant")
        assert not is_physical_cell_act("aspen.fleet.node.heartbeat:read", "full-plant")
        assert not is_physical_cell_act("aspen.sentinel.audit.event:read", "full-plant")

    def test_light_cell_profile_excluded(self):
        assert not is_physical_cell_act("aspen.edge.cell-01.act:execute", "light-cell")
        assert not is_physical_cell_act("aspen.safety.estop:execute", "light-cell")
        # Unknown profiles are treated as potentially physical (fail closed):
        # only an explicit light-cell profile opts out of the vault gate.
        assert is_physical_cell_act("aspen.edge.cell-01.act:execute", "light-cel")


# =========================================================================
# Vault record created on request
# =========================================================================


class TestVaultRecordOnRequest:
    def test_physical_request_creates_durable_vault_record(self, physical_store):
        result = _physical_request()
        assert result["decision"] == "propose_act"
        assert result["requires"] == "dual_human"
        hitl_id = result.get("vault_approval_id")
        assert hitl_id

        proposal = PROPOSALS[result["request_id"]]
        assert proposal["vault"]["hitl_request_id"] == hitl_id
        assert proposal["vault"]["status"] == "pending"

        # Durable SQLite row — re-read with a fresh manager (survives "restart").
        fresh = vault_gate.make_manager().get_request(hitl_id)
        assert fresh is not None
        assert fresh.status == "pending"
        assert fresh.tool == "propose_act"
        assert fresh.context.get("physical") is True
        assert fresh.context.get("request_id") == result["request_id"]

        # Human-reviewable Obsidian note materialised in the vault dir.
        note = vault_gate.make_vault().get(hitl_id)
        assert note is not None
        assert note["metadata"]["status"] == "pending"
        assert (Path(os.environ["HITL_VAULT_DIR"]) / f"{hitl_id}.md").exists()

    def test_estop_stays_plain_dual_human(self, physical_store):
        result = request_capability(
            "aspen-fleet-edge", PLAIN_CELL_CAP, "plant:chae-cell-01", {"profile": "full-plant"}
        )
        assert result["decision"] == "propose_act"
        assert "vault_approval_id" not in result
        assert "vault" not in PROPOSALS[result["request_id"]]

    def test_light_cell_request_creates_no_vault(self, physical_store):
        result = _physical_request(profile="light-cell")
        assert result["decision"] == "propose_act"
        assert "vault_approval_id" not in result

    def test_vault_unavailable_fails_closed(self, physical_store, tmp_path):
        # A path whose parent is a FILE can never become a DB -> vault layer
        # raises and the capability path must fail closed instead of granting.
        blocker = tmp_path / "blocker"
        blocker.write_text("i am a file")
        os.environ["HITL_DB"] = str(blocker / "hitl.db")
        result = _physical_request()
        assert result["decision"] == "deny"
        assert result["reason"] == "vault_unavailable"
        assert "gate.vault_unavailable" in [e["type"] for e in AUDIT_LOG]
        # Proposal is refused — a later authorize never grants.
        assert PROPOSALS[result["request_id"]]["state"] == "refused"

    def test_vault_created_audit_event(self, physical_store):
        _physical_request()
        events = [e for e in AUDIT_LOG if e["type"] == "gate.vault_created"]
        assert len(events) == 1
        assert events[0]["profile"] == "full-plant"
        assert events[0]["hitl_request_id"]


# =========================================================================
# Vault gate at the dual-human threshold
# =========================================================================


class TestVaultGateOnAuthorize:
    def test_two_humans_with_pending_vault_refused(self, physical_store):
        result = _physical_request()
        assert authorize_gate_request(result["request_id"], "op-1")["decision"] == "awaiting"
        outcome = authorize_gate_request(result["request_id"], "op-2")
        assert outcome["decision"] == "refuse"
        assert outcome["reason"] == "vault_approval_required"
        assert outcome["humans"] == ["op-1", "op-2"]
        assert outcome["humans_required"] == DUAL_HUMAN_REQUIRED
        assert PROPOSALS[result["request_id"]]["state"] == "refused"
        # Forward after vault-refusal stays refused.
        assert forward_proposal(result["request_id"])["decision"] == "refuse"

    def test_two_humans_with_approved_vault_grant(self, physical_store):
        result = _physical_request()
        _approve_vault_for(result["vault_approval_id"])
        authorize_gate_request(result["request_id"], "op-1")
        outcome = authorize_gate_request(result["request_id"], "op-2")
        assert outcome["decision"] == "grant"
        assert outcome["vault_approval_id"] == result["vault_approval_id"]
        assert outcome["humans"] == ["op-1", "op-2"]
        assert "token_id" in outcome["token"]
        assert PROPOSALS[result["request_id"]]["state"] == "granted"

    def test_vault_approval_order_independent(self, physical_store):
        # Approve the vault record BEFORE any human authorizes.
        result = _physical_request()
        _approve_vault_for(result["vault_approval_id"])
        assert authorize_gate_request(result["request_id"], "op-a")["decision"] == "awaiting"
        outcome = authorize_gate_request(result["request_id"], "op-b")
        assert outcome["decision"] == "grant"

    def test_vault_denied_refused(self, physical_store):
        result = _physical_request()
        vault_gate.make_vault().deny(result["vault_approval_id"], decided_by="op-1", reason="nope")
        authorize_gate_request(result["request_id"], "op-1")
        outcome = authorize_gate_request(result["request_id"], "op-2")
        assert outcome["decision"] == "refuse"
        assert outcome["reason"] == "vault_approval_required"

    def test_missing_vault_mapping_refused(self, physical_store):
        result = _physical_request()
        del PROPOSALS[result["request_id"]]["vault"]
        authorize_gate_request(result["request_id"], "op-1")
        outcome = authorize_gate_request(result["request_id"], "op-2")
        assert outcome["decision"] == "refuse"
        assert outcome["reason"] == "vault_approval_required"

    def test_duplicate_human_still_ignored(self, physical_store):
        result = _physical_request()
        assert authorize_gate_request(result["request_id"], "op-1")["decision"] == "awaiting"
        dup = authorize_gate_request(result["request_id"], "op-1")
        assert dup["decision"] == "awaiting"
        assert dup.get("note") == "duplicate_human_ignored"
        assert [h for h in PROPOSALS[result["request_id"]]["humans"]] == ["op-1"]

    def test_unknown_request_refused(self, physical_store):
        outcome = authorize_gate_request("no-such-request", "op-1")
        assert outcome["decision"] == "refuse"
        assert outcome["reason"] == "unknown_request"

    def test_vault_refuse_audit_event(self, physical_store):
        result = _physical_request()
        authorize_gate_request(result["request_id"], "op-1")
        authorize_gate_request(result["request_id"], "op-2")
        events = [e for e in AUDIT_LOG if e["type"] == "gate.vault_refuse"]
        assert len(events) == 1
        assert events[0]["reason"] == "vault_approval_required"

    def test_missing_note_file_refused(self, physical_store):
        result = _physical_request()
        _approve_vault_for(result["vault_approval_id"])
        # Reopen DB row to approved but delete the reviewable note => fail closed.
        note_path = Path(os.environ["HITL_VAULT_DIR"]) / f"{result['vault_approval_id']}.md"
        note_path.unlink()
        authorize_gate_request(result["request_id"], "op-1")
        outcome = authorize_gate_request(result["request_id"], "op-2")
        assert outcome["decision"] == "refuse"
        assert outcome["reason"] == "vault_approval_required"


# =========================================================================
# Restart persistence
# =========================================================================


class TestRestartPersistence:
    def test_record_survives_restart(self, physical_store):
        result = _physical_request()
        hitl_id = result["vault_approval_id"]

        # Simulate a gatekeeper restart: fresh manager + fresh vault read the
        # same SQLite file and note directory.
        fresh_manager = vault_gate.make_manager()
        fresh_vault = vault_gate.make_vault()

        row = fresh_manager.get_request(hitl_id)
        assert row is not None and row.status == "pending"

        entries = {e["id"] for e in fresh_vault.list()}
        assert hitl_id in entries

        # Approving via a fresh instance persists to the same DB.
        fresh_vault.approve(hitl_id, decided_by="op-1", reason="plant clear")
        assert fresh_manager.get_request(hitl_id).status == "approved"

        db_path = Path(os.environ["HITL_DB"])
        assert db_path.exists()
        conn = sqlite3.connect(str(db_path))
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM approvals WHERE id = ?", (hitl_id,)
            ).fetchone()[0]
        finally:
            conn.close()
        assert count == 1