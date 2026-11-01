"""
Tests for the ADR-0012 operator registry (ASP-837).

Covers:
- Enroll new operator with required fields
- Enroll with aliases
- Duplicate enrollment raises
- Alias collision across operators raises
- Revoke active operator
- Revoke already-revoked operator is idempotent
- Get operator by human_id
- Find operator by alias
- List active operators (excludes revoked)
- List all operators (includes revoked)
- Persistence across registry load
- Empty registry loads cleanly
"""

import json
import os
import sys
import tempfile

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PYTHON = os.path.join(REPO_ROOT, "src", "python")
sys.path.insert(0, SRC_PYTHON)

from services.operator_registry import OperatorRegistry, Operator


class TestEnroll:
    def test_enroll_basic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            op = reg.enroll("op-001", "Alice Smith", enrolled_by="admin")
            assert op.human_id == "op-001"
            assert op.display_name == "Alice Smith"
            assert op.status == "active"
            assert op.enrolled_by == "admin"
            assert "+00:00" in op.enrolled_at or op.enrolled_at.endswith("Z")

    def test_enroll_with_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            op = reg.enroll(
                "op-002", "Bob Jones",
                aliases=["bob@plant", "@bob:matrix"],
                plant_id="chae-cell-01",
            )
            assert op.plant_id == "chae-cell-01"
            assert "bob@plant" in op.aliases

    def test_enroll_empty_human_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            with pytest.raises(ValueError, match="must not be empty"):
                reg.enroll("  ", "No name")

    def test_enroll_duplicate_active_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith")
            with pytest.raises(ValueError, match="already enrolled"):
                reg.enroll("op-001", "Alice Again")

    def test_enroll_alias_collision_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith", aliases=["alice@plant"])
            with pytest.raises(ValueError, match="already bound"):
                reg.enroll("op-002", "Bob Jones", aliases=["alice@plant"])

    def test_enroll_revoked_then_re_enroll(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith")
            reg.revoke("op-001")
            op = reg.enroll("op-001", "Alice Smith v2")
            assert op.status == "active"
            assert op.display_name == "Alice Smith v2"


class TestRevoke:
    def test_revoke_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith")
            assert reg.revoke("op-001") is True
            op = reg.get("op-001")
            assert op.status == "revoked"

    def test_revoke_unknown_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            assert reg.revoke("no-such-op") is False

    def test_revoke_twice_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith")
            reg.revoke("op-001")
            assert reg.revoke("op-001") is True


class TestLookup:
    def test_get_returns_operator(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith")
            op = reg.get("op-001")
            assert op is not None
            assert op.display_name == "Alice Smith"

    def test_get_unknown_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            assert reg.get("no-such-op") is None

    def test_find_by_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith", aliases=["alice@plant"])
            op = reg.find_by_alias("alice@plant")
            assert op is not None
            assert op.human_id == "op-001"

    def test_find_by_alias_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith", aliases=["Alice@Plant"])
            op = reg.find_by_alias("alice@plant")
            assert op is not None

    def test_find_by_alias_unknown_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith", aliases=["alice@plant"])
            assert reg.find_by_alias("bob@plant") is None


class TestList:
    def test_list_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            assert reg.list() == []

    def test_list_active_excludes_revoked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith")
            reg.enroll("op-002", "Bob Jones")
            reg.revoke("op-002")
            active = reg.list(active_only=True)
            assert len(active) == 1
            assert active[0].human_id == "op-001"

    def test_list_all_includes_revoked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith")
            reg.revoke("op-001")
            all_ops = reg.list(active_only=False)
            assert len(all_ops) == 1


class TestPersistence:
    def test_persists_and_reloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith", aliases=["alice@plant"])

            reg2 = OperatorRegistry(db_path=path)
            op = reg2.get("op-001")
            assert op is not None
            assert op.display_name == "Alice Smith"
            assert op.aliases == ["alice@plant"]
            assert op.status == "active"

    def test_reloads_revoked_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            reg.enroll("op-001", "Alice Smith")
            reg.revoke("op-001")

            reg2 = OperatorRegistry(db_path=path)
            op = reg2.get("op-001")
            assert op.status == "revoked"

    def test_empty_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            reg = OperatorRegistry(db_path=path)
            assert reg.list() == []

    def test_corrupt_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registry.json")
            with open(path, "w") as f:
                f.write("not json")
            reg = OperatorRegistry(db_path=path)
            assert reg.list() == []