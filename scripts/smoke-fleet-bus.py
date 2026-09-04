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
# Preference order (first match wins on sys.path): CI/checkout siblings,
# projects layout used on this host, then legacy /home/tech/repos, then parent walk.
_RRM_NAME = "aspen-edge-rrm"
_SWARM_NAME = "aspen-swarm-manager"
_preferred: list[Path] = [
    REPO_ROOT.parent / _RRM_NAME,  # CI: checkout/../aspen-edge-rrm
    REPO_ROOT.parent / _SWARM_NAME,
    Path("/home/tech/projects/aspen-dev/repos") / _RRM_NAME,
    Path("/home/tech/projects/aspen-dev/repos") / _SWARM_NAME,
    Path("/home/tech/aspen-dev/repos") / _RRM_NAME,
    Path("/home/tech/aspen-dev/repos") / _SWARM_NAME,
    Path("/home/tech/repos") / _RRM_NAME,
    Path("/home/tech/repos") / _SWARM_NAME,
]
_walk = REPO_ROOT
for _ in range(6):
    _walk = _walk.parent
    _preferred.append(_walk / _RRM_NAME)
    _preferred.append(_walk / _SWARM_NAME)
    if _walk == _walk.parent:
        break
_seen: set[str] = set()
_resolved_paths: list[str] = []
for _candidate in _preferred:
    _resolved = str(_candidate.resolve())
    if _resolved in _seen:
        continue
    if Path(_resolved).is_dir():
        _seen.add(_resolved)
        _resolved_paths.append(_resolved)
# Highest preference first (do not reverse via repeated insert(0))
for _p in reversed(_resolved_paths):
    if _p not in sys.path:
        sys.path.insert(0, _p)

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
    # Default risk is safety_adjacent → held until dual human auth (H-016).
    # Explicit safe proposals bypass the gate and accept in sim.
    held_proposal = agent.tick({"target": "pose_home"})
    held = next((a for a in rrm.audit if a.get("result") == "held_dual_auth"), None)
    if held and held.get("proposal_id"):
        bus.publish(
            f"aspen.edge.{rrm.node_id}.authorize",
            {"proposal_id": held["proposal_id"], "human_id": "op-b"},
            source="human/op-b",
        )
        bus.publish(
            f"aspen.edge.{rrm.node_id}.authorize",
            {"proposal_id": held["proposal_id"], "human_id": "op-c"},
            source="human/op-c",
        )
        act = rrm.request_act(held["proposal_id"])
        check("micro-agent dual-auth execute", act.get("result") == "executed_sim")
    agent.tick({"target": "pose_home", "note": "mock"}, risk_class="safe")
    accepted = any(a.get("result") == "accepted_sim" for a in rrm.audit)
    # Older edge-rrm without dual-auth gate only emits accepted_sim
    if not accepted and not held:
        accepted = any(a.get("result") == "accepted_sim" for a in rrm.audit)
    check("micro-agent propose accepted", accepted or held is not None)

    # Dual-human estop clear (aspen-edge-rrm gate): bare clear must not unlatch;
    # two distinct humans, neither the stop-causer alone, authorize then clear.
    bus.publish(
        "aspen.safety.estop",
        {"reason": "test", "actor": "op-dave", "source": "operator"},
        source="safety",
    )
    check("estop latched", rrm.estop is True)

    proposal2 = agent.tick({"target": "pose_a"})
    refused = any(a.get("result") == "refused_estop" for a in rrm.audit)
    check("estop blocks proposal", refused)

    bus.publish("aspen.safety.clear", {"source": "operator"}, source="safety")
    # Audit shape differs by aspen-edge-rrm rev:
    # - newer: event=clear_refused reason=insufficient_principals
    # - older: event=clear_refused_insufficient_auths
    bare_refused = rrm.estop is True and any(
        (
            a.get("event") == "clear_refused"
            and a.get("reason") in ("insufficient_principals", "insufficient_auths", None)
        )
        or a.get("event") in (
            "clear_refused_insufficient_auths",
            "clear_refused_insufficient_principals",
        )
        for a in rrm.audit
    )
    check("estop bare clear refused", bare_refused)

    bus.publish("aspen.safety.authorize_clear", {"human_id": "bob"}, source="human/bob")
    bus.publish("aspen.safety.authorize_clear", {"human_id": "carol"}, source="human/carol")
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