#!/usr/bin/env python3
"""Fleet bus smoke test — in-process E2E via aspen-edge-rrm + aspen-swarm-manager."""
import os
import sys

os.environ.setdefault("ASPEN_SIM", "1")

PASS = 0
FAIL = 0

def check(name, ok):
    global PASS, FAIL
    if ok:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}")
        FAIL += 1

print("=== Fleet bus smoke test ===")

try:
    from aspen_edge import FleetBus, OpsManager, EdgeRRM
    check("aspen_edge import", True)
except ImportError as e:
    check(f"aspen_edge import — {e}", False)
    sys.exit(1)

bus = FleetBus()

received = []
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
sys.exit(0 if FAIL == 0 else 1)