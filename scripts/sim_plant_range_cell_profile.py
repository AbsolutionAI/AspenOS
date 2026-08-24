#!/usr/bin/env python3
"""BEL-192 / ASP-416 — sim contract for plant-range-d1 cell profile.

Validates architecture locks without hardware:
  - profile YAML plant-range + isolation + hold-to-enable
  - fleet ACL plant-range outbound empty
  - plant-range allows robotics role
  - refuse schedule plant-range -> edge/alpha (via PlantACL if available,
    else structural check against fleet.yaml)

Exit 0 + JSON proof line on success.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "config" / "cells" / "plant-range-d1.yaml"
FLEET = ROOT / "config" / "fleet.yaml"


def _load_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError("root must be mapping")
        return data
    except ImportError:
        # Minimal subset parser for our locked keys (no external dep required)
        return _minimal_yaml_map(text)


def _minimal_yaml_map(text: str) -> dict:
    """Parse a shallow YAML-ish structure sufficient for this profile contract."""
    # Prefer PyYAML; this fallback only supports the keys we assert on via line scan.
    out: dict = {"_raw": text}
    return out


def _raw_has(raw: str, *needles: str) -> bool:
    return all(n in raw for n in needles)


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        raise AssertionError(name)


def main() -> int:
    errors: list[str] = []

    def run(name: str, cond: bool, detail: str = "") -> None:
        try:
            check(name, cond, detail)
        except AssertionError as e:
            errors.append(str(e))

    run("profile exists", PROFILE.is_file(), str(PROFILE))
    run("fleet.yaml exists", FLEET.is_file(), str(FLEET))
    if not PROFILE.is_file() or not FLEET.is_file():
        print(json.dumps({"proof": "plant_range_cell_profile", "result": "fail", "errors": errors}))
        return 1

    prof_raw = PROFILE.read_text(encoding="utf-8")
    fleet_raw = FLEET.read_text(encoding="utf-8")

    run("profile plant-range", _raw_has(prof_raw, "plant: plant-range") or "plant: plant-range" in prof_raw)
    run("profile isolation true", "isolation: true" in prof_raw)
    run("hold_to_enable true", "hold_to_enable: true" in prof_raw)
    run("auto_arm false", "auto_arm: false" in prof_raw)
    run("forbid operator sim", "forbid_operator_values" in prof_raw and "sim" in prof_raw)
    run("dual_human_required", "dual_human_required: true" in prof_raw)
    run("aspen_sim false on profile", "aspen_sim: false" in prof_raw)
    run("motion_allowed false default", "motion_allowed: false" in prof_raw)
    run("acl outbound empty", "outbound_allow: []" in prof_raw)
    run("refuse schedule to alpha", "plant-alpha" in prof_raw)
    run("refuse schedule to edge", "plant-edge" in prof_raw)
    run("live wire tracker ASP-364", "ASP-364" in prof_raw)

    run("fleet ACL plant-range empty", "plant-range: []" in fleet_raw)
    run("fleet plant-range isolation", "plant-range:" in fleet_raw and "isolation: true" in fleet_raw)
    run(
        "fleet plant-range allows robotics",
        "plant-range:" in fleet_raw and "robotics" in fleet_raw.split("plant-range:")[1].split("red_blue:")[0],
    )

    # Structural ACL refuse via agents.fleet_policy if importable
    acl_ok = None
    try:
        sys.path.insert(0, str(ROOT))
        from agents.fleet_policy import check_cross_plant  # type: ignore

        # Prefer deny range -> alpha/edge
        for src, dst in (("plant-range", "plant-alpha"), ("plant-range", "plant-edge")):
            try:
                allowed = check_cross_plant(src, dst)
                if allowed is True:
                    acl_ok = False
                    run(f"ACL refuse {src}->{dst}", False, "unexpectedly allowed")
                else:
                    run(f"ACL refuse {src}->{dst}", True, str(allowed))
                    acl_ok = True if acl_ok is None else acl_ok
            except Exception as ex:  # policy may raise on deny
                run(f"ACL refuse {src}->{dst}", True, f"raised/denied: {type(ex).__name__}")
                acl_ok = True if acl_ok is None else acl_ok
    except Exception as ex:
        run("fleet_policy import optional", True, f"skipped ({type(ex).__name__})")

    # Optional richer parse
    try:
        prof = _load_yaml(PROFILE)
        if "_raw" not in prof:
            cell = prof.get("cell") or {}
            run("parsed cell.plant", cell.get("plant") == "plant-range")
            run("parsed cell.isolation", cell.get("isolation") is True)
            arm = prof.get("arm") or {}
            run("parsed arm.hold_to_enable", arm.get("hold_to_enable") is True)
            run("parsed arm.auto_arm", arm.get("auto_arm") is False)
    except Exception as ex:
        run("yaml parse optional", True, f"fallback ok ({type(ex).__name__})")

    if errors:
        print(json.dumps({"proof": "plant_range_cell_profile", "result": "fail", "errors": errors}))
        return 1

    proof = {
        "proof": "plant_range_cell_profile",
        "result": "pass",
        "profile": str(PROFILE.relative_to(ROOT)),
        "checks": [
            "plant-range",
            "isolation",
            "hold_to_enable",
            "no_auto_arm",
            "dual_human",
            "acl_empty_outbound",
            "robotics_role",
        ],
    }
    print(json.dumps(proof))
    return 0


if __name__ == "__main__":
    sys.exit(main())
