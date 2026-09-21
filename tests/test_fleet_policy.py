"""H-021 / F-022 (ASP-369): plant-edge→plant-alpha ACL pivot removal.

Hermetic unit tests for agents/fleet_policy.py cross-plant ACL. These never
touch the network. The loader is patched so it always reads the committed
config/fleet.yaml from the repo (it cannot be shadowed by /etc/starship),
so the tests prove the shipped ACL rather than a drifting fixture.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agents"))

import fleet_policy

REPO_ROOT = Path(__file__).resolve().parent.parent
SHIPPED_ACL_FILE = REPO_ROOT / "config" / "fleet.yaml"


def _read_yaml(path):
    try:
        import yaml
        return yaml.safe_load(path.read_text()) or {}
    except Exception:
        return {}


@pytest.fixture(autouse=True)
def fresh_fleet_config():
    fleet_policy.clear_cache()
    yield
    fleet_policy.clear_cache()


@pytest.fixture
def fpy(monkeypatch):
    """Force the loader to resolve fleet.yaml from the repo config only."""
    def fake_load_yaml(path: Path) -> dict:
        if Path(path) == SHIPPED_ACL_FILE:
            return _read_yaml(SHIPPED_ACL_FILE)
        return {}

    monkeypatch.setattr(fleet_policy, "_load_yaml", fake_load_yaml)
    yield fleet_policy


def _shipped_acl():
    return _read_yaml(SHIPPED_ACL_FILE).get("acl") or {}


# ---- ACL matrix from the committed fleet.yaml -----------------------------


def test_edge_cannot_reach_alpha(fpy):
    """H-021/F-022: the allow list must NOT contain edge→alpha."""
    allow = _shipped_acl()["allow"]
    assert "plant-edge" not in allow, (
        "plant-edge→plant-alpha pivot must be removed from config/fleet.yaml"
    )


def test_alpha_to_edge_still_allowed(fpy):
    """Ops-initiated alpha→edge must remain allowed (ops management)."""
    assert fpy.check_cross_plant("plant-alpha", "plant-edge") is None


def test_edge_to_alpha_is_denied_by_default(fpy):
    """Removed edge→alpha now falls through to the fail-closed default."""
    denial = fpy.check_cross_plant("plant-edge", "plant-alpha")
    assert denial is not None
    assert "policy:" in denial


def test_range_never_leaves(fpy):
    """plant-range is isolated; empty allow list; not reachable from ops."""
    allow = _shipped_acl()["allow"]
    assert allow.get("plant-range") == []
    assert fpy.check_cross_plant("plant-range", "plant-alpha") is not None
    assert fpy.check_cross_plant("plant-range", "plant-edge") is not None


def test_alpha_cannot_reach_range(fpy):
    """plant-range inbound is denied even from ops."""
    assert fpy.check_cross_plant("plant-alpha", "plant-range") is not None


# ---- Same-plant / structural behavior -------------------------------------


def test_same_plant_allowed(fpy):
    assert fpy.check_cross_plant("plant-alpha", "plant-alpha") is None
    assert fpy.check_cross_plant("plant-edge", "plant-edge") is None


def test_no_target_allowed(fpy):
    assert fpy.check_cross_plant("plant-edge", None) is None


def test_unknown_source_falls_to_default(fpy):
    assert fpy.check_cross_plant("plant-mars", "plant-alpha") is not None


def test_red_team_cross_plant_denied_during_exercise(fpy, monkeypatch):
    """Red-team never crosses plants during an active exercise."""
    monkeypatch.setattr(fleet_policy, "exercise_active", lambda: True)
    denial = fpy.check_cross_plant(
        "plant-alpha",
        "plant-edge",
        {"team": "red", "roles": ["red-team"], "plant": "plant-alpha"},
    )
    assert denial is not None
    assert "red-team" in denial


def test_tool_edges_match_acl(fpy):
    """delegate_to_agent respects the same ACL: alpha→edge ok, edge→alpha no."""
    alpha_ctx = {"team": "ops", "roles": ["proxy"], "plant": "plant-alpha"}
    edge_ctx = {"team": "ops", "roles": ["plant-controller"], "plant": "plant-edge"}
    assert (
        fpy.check_tool("delegate_to_agent", ctx=alpha_ctx, target_plant="plant-edge")
        is None
    )
    assert (
        fpy.check_tool("delegate_to_agent", ctx=edge_ctx, target_plant="plant-alpha")
        is not None
    )


def test_acl_default_is_fail_closed(fpy):
    assert _shipped_acl()["default"] in ("same_plant_only", "deny", "closed")