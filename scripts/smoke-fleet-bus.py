#!/usr/bin/env python3
"""Fleet bus smoke test — in-process E2E via aspen-edge-rrm + aspen-swarm-manager."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("ASPEN_SIM", "1")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

# Discover sibling repos: aspen-edge-rrm and aspen-swarm-manager.
# CI clones them at ../ relative to the checkout; dev setups may use
# /home/tech/repos/ or other conventions.  Try several candidates.
_RRM_NAME = "aspen-edge-rrm"
_SWARM_NAME = "aspen-swarm-manager"
for _candidate in [
    REPO_ROOT.parent / _RRM_NAME,
    REPO_ROOT.parent / _SWARM_NAME,
    Path("/home/tech/repos") / _RRM_NAME,
    Path("/home/tech/repos") / _SWARM_NAME,
    SCRIPT_DIR / ".." / _RRM_NAME,
    SCRIPT_DIR / ".." / _SWARM_NAME,
]:
    _resolved = _candidate.resolve()
    if _resolved.is_dir() and str(_resolved) not in sys.path:
        sys.path.insert(0, str(_resolved))

PASS = 0
FAIL = 0


def check(name: str, ok: bool) -> None:
    global PASS, FAIL
    if ok:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}")
        FAIL += 1


def main() -> int:
    print("=== Fleet bus smoke test ===")

    try:
        from aspen_edge import FleetBus, OpsManager, EdgeRRM
        check("aspen_edge import", True)
    except ImportError as e:
        print(f"  SKIP  aspen_edge import — {e}")
        print()
        print("Dependencies not available (aspen-edge-rrm, aspen-swarm-manager); skipping.")
        return 0

    bus = FleetBus()

    received: list[dict] = []
    bus.subscribe("test.subject", lambda env: received.append(env))
    env = bus.publish("test.subject", {"msg": "hello"}, source="smoke")
    check("fleet bus publish returns envelope", env is not None)
    check("fleet bus subscribe delivers", len(received) == 1)
    check("fleet bus payload matches", received[0]["data"]["msg"] == "hello")

    ops = OpsManager(bus)
    check("ops manager subscribe", "aspen.fleet.node.register" in bus._subs)
    check("ops manager hb subscribe", "aspen.fleet.node.heartbeat" in bus._subs)

    rrm = EdgeRRM(node_id="smoke-node-1", bus=bus, plant="plant-edge", caps=["mock_cobot"])
    rrm.start()
    check("edge rrm start", "smoke-node-1" in ops.nodes)

    rrm.heartbeat()
    check("edge rrm registered", ops.nodes["smoke-node-1"].get("status") in ("online", "registered", "ok"))

    status_events = [e for e in bus.history if e["subject"] == "aspen.fleet.ops.status"]
    check("ops.status published after hb", len(status_events) >= 1)

    agent = rrm.add_agent("micro-1")
    proposal = agent.tick({"target": "pose_home"})
    accepted = any(a.get("result") == "accepted_sim" for a in rrm.audit)
    check("micro-agent propose accepted", accepted)

    bus.publish("aspen.safety.estop", {"reason": "test", "source": "operator"}, source="safety")
    check("estop latched", rrm.estop is True)

    proposal2 = agent.tick({"target": "pose_a"})
    refused = any(a.get("result") == "refused_estop" for a in rrm.audit)
    check("estop blocks proposal", refused)

    bus.publish("aspen.safety.clear", {"source": "operator"}, source="safety")
    check("estop cleared", rrm.estop is False)

    try:
        from aspen_swarm import SwarmManager, MemberRegistry
        check("aspen_swarm import", True)
        reg = MemberRegistry()
        reg.register("cobot-1", ["mock_cobot"], plant="plant-edge")
        sm = SwarmManager(registry=reg, default_origin="plant-edge")
        m = sm.submit("move to home", ["mock_cobot"], plant="plant-edge")
        check("swarm submit returns mission", m is not None)
        check("swarm mission started", m.state.value == "running")
        sm.complete(m.id)
        check("swarm mission completed", m.state.value == "done")
        mission_events = [e for e in sm.bus.history if e["type"].startswith("aspen.fleet.mission.")]
        check("swarm mission events published", len(mission_events) >= 3)
    except ImportError as e:
        check(f"aspen_swarm import — {e}", False)

    print()
    print(f"Result: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())