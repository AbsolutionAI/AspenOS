"""ASP-796: D1 plant-range cell profile is simulation-only and policy-consistent.

Hermetic: reads committed config only (fleet loader patched so /etc/starship
cannot shadow it). No hardware, network, or NATS access.
"""
import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "agents"))

import fleet_policy  # noqa: E402

PROFILE = REPO_ROOT / "config" / "cells" / "plant-range-d1.sim.yaml"
FLEET = REPO_ROOT / "config" / "fleet.yaml"

# Keys that would indicate hardware I/O or a live/physical path.
_HARDWARE_KEYS = {
    "gpio", "serial", "usb_serial", "can", "canbus", "fieldbus", "modbus",
    "ethercat", "profinet", "driver", "drivers", "joints", "joint_limits",
    "setpoints", "motion_day", "install_path", "hardware", "estop_gpio",
    "device", "devices", "port",
}


def _load(path):
    return yaml.safe_load(path.read_text()) or {}


def _walk_keys(node, prefix=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield f"{prefix}{k}", str(k).lower()
            yield from _walk_keys(v, f"{prefix}{k}.")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_keys(v, f"{prefix}{i}.")


@pytest.fixture
def profile():
    return _load(PROFILE)


@pytest.fixture
def fleet():
    return _load(FLEET)


@pytest.fixture
def fpy(monkeypatch):
    fleet_policy.clear_cache()
    monkeypatch.setattr(
        fleet_policy, "_load_yaml",
        lambda p: _load(FLEET) if Path(p) == FLEET else {},
    )
    yield fleet_policy
    fleet_policy.clear_cache()


def test_profile_is_sim_only(profile):
    cell = profile["cell"]
    assert cell["sim_only"] is True
    assert cell["aspen_sim"] is True
    assert cell["motion_allowed"] is False
    assert cell.get("physical_profile") in (None, "")
    assert cell["plant"] == "plant-range"
    assert cell["isolation"] is True


def test_no_hardware_io_or_install_path(profile):
    offenders = [path for path, key in _walk_keys(profile) if key in _HARDWARE_KEYS]
    assert offenders == [], f"hardware/physical keys in sim profile: {offenders}"
    raw = PROFILE.read_text()
    assert "/etc/starship/cells" not in raw
    assert "ASPEN_SIM=0" not in raw


def test_arm_and_act_gates(profile):
    arm, act = profile["arm"], profile["act"]
    assert arm["hold_to_enable"] is True
    assert arm["require_human_operator"] is True
    assert arm["auto_arm"] is False
    assert act["path"] == "propose_act_only"
    assert act["dual_human_required"] is True
    assert act["result_on_approve"] == "executed_sim"
    assert {"insufficient_principals", "duplicate_principal", "self_approval",
            "expired"} <= set(act["refuse"])
    assert profile["safety"]["latch"] is True
    assert profile["safety"]["dual_human_clear"] is True


def test_forbidden_list_covers_physical_paths(profile):
    forbidden = set(profile["forbidden"])
    for item in ("physical_cell_install", "aspen_sim_0", "motion_day",
                 "hardware_io_estop_gpio_serial_can", "plant_or_ot_network_change",
                 "hardware_po", "cross_plant_schedule_out"):
        assert item in forbidden


def test_acl_matches_fleet(profile, fleet):
    assert profile["acl"]["outbound_allow"] == fleet["acl"]["allow"]["plant-range"] == []
    assert fleet["plants"]["plant-range"]["isolation"] is True


def test_node_roles_allowed_on_plant_range(profile, fleet):
    allowed = set(fleet["plants"]["plant-range"]["roles_allowed"])
    assert set(profile["node"]["roles"]) <= allowed
    assert profile["node"]["plant"] == "plant-range"


@pytest.mark.parametrize("target", ["plant-alpha", "plant-edge"])
def test_policy_refuses_schedule_out(fpy, profile, target):
    assert target in profile["acl"]["refuse_schedule_to"]
    ctx = {"team": "ops", "roles": profile["node"]["roles"], "plant": "plant-range"}
    reason = fpy.check_cross_plant("plant-range", target, ctx)
    assert reason and "denied" in reason


@pytest.mark.parametrize("source", ["plant-alpha", "plant-edge"])
def test_policy_refuses_inbound_to_isolated_range(fpy, source):
    ctx = {"team": "ops", "roles": ["ops"], "plant": source}
    reason = fpy.check_cross_plant(source, "plant-range", ctx)
    assert reason and "isolated" in reason
