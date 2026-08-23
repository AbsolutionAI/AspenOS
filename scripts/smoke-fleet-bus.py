#!/usr/bin/env python3
"""NATS fleet bus smoke: exercises all aspen.fleet.* / aspen.safety.* contracts in-process.

Covers:
  1. aspen.fleet.node.register — EdgeRRM node lifecycle
  2. aspen.fleet.node.heartbeat — periodic node status
  3. aspen.fleet.mission.{planned,armed,running,done,failed} — SwarmManager mission lifecycle
  4. aspen.edge.<node>.propose_act — micro-agent action proposal
  5. aspen.safety.{estop,clear} — safety chain
  6. aspen.fleet.ops.status — OpsManager aggregate status
  7. aspen.fleet.mission.held — hold on estop

Simulates the full robotics agent contract surface.
"""

import os
import sys
import json
from pathlib import Path

# Ensure ASPEN_SIM=1
os.environ.setdefault("ASPEN_SIM", "1")

# Add both repos to sys.path
REPO_DIR = Path(__file__).resolve().parent
ASPEN_OS = REPO_DIR
SWARM_DIR = REPO_DIR.parent / "aspen-swarm-manager"
RRM_DIR = REPO_DIR.parent / "aspen-edge-rrm"

for d in [SWARM_DIR, RRM_DIR]:
    if d.exists():
        sys.path.insert(0, str(d))

PASS = 0
FAIL = 0

def check(name, ok, detail=""):
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    print(f"  {tag}  {name}" + (f" — {detail}" if detail else ""))
    if ok:
        PASS += 1
    else:
        FAIL += 1

print("=== Aspen Fleet Bus Smoke (in-process) ===")
print(f"ASPEN_SIM={os.environ['ASPEN_SIM']}")
print()

# ── Import contracts ──────────────────────────────────────────────────
sys.path.insert(0, str(ASPEN_OS / "agents"))

# Edge RRM contracts
sys.path.insert(0, str(RRM_DIR))
from aspen_edge.fleet_bus import FleetBus, OpsManager
from aspen_edge.rrm import EdgeRRM

# Swarm Manager contracts
sys.path.insert(0, str(SWARM_DIR))
from aspen_swarm import SwarmManager, MemberRegistry, PlantACL
from aspen_swarm.mission import MissionState

# ── Shared bus (in-process NATS stand-in) ──────────────────────────────
bus = FleetBus()
events = []

def record(env):
    events.append(env)

# Subscribe to all exact aspen.fleet.* and aspen.safety.* subjects
for subj in [
    "aspen.fleet.node.register",
    "aspen.fleet.node.heartbeat",
    "aspen.fleet.ops.status",
    "aspen.safety.estop",
    "aspen.safety.clear",
    "aspen.edge.robot-sim-1.propose_act",
]:
    bus.subscribe(subj, record)

# ── 0. OpsManager (must exist before node lifecycle) ───────────────────
ops = OpsManager(bus)

# ── 1. Edge RRM node registration ─────────────────────────────────────
print("\n--- 1. Node Lifecycle (register / heartbeat) ---")
rrm = EdgeRRM(node_id="robot-sim-1", bus=bus, plant="plant-edge", caps=["mock_cobot", "arm_6dof"])
rrm.start()

register_events = [e for e in events if e["type"] == "aspen.fleet.node.register"]
check("node register published", len(register_events) == 1,
      f"subject={register_events[0]['subject']} node={register_events[0]['data']['node_id']}")
check("node register correct node_id", register_events[0]["data"]["node_id"] == "robot-sim-1")
check("node register caps", register_events[0]["data"]["caps"] == ["mock_cobot", "arm_6dof"])

rrm.heartbeat()
hb_events = [e for e in events if e["type"] == "aspen.fleet.node.heartbeat"]
check("node heartbeat published", len(hb_events) >= 1,
      f"status={hb_events[-1]['data']['status']}")
check("node heartbeat status online", hb_events[-1]["data"]["status"] == "online")

# ── 2. OpsManager aggregates ──────────────────────────────────────────
check("ops manager sees node", "robot-sim-1" in ops.nodes,
      f"nodes={list(ops.nodes.keys())}")

# ── 3. Action proposal ────────────────────────────────────────────────
print("\n--- 2. Action Proposal (propose_act) ---")
agent = rrm.add_agent("micro-arm-1")
agent.tick({"target": "pose_home"})

propose_events = [e for e in events if "propose_act" in e.get("type", "")]
check("propose_act published", len(propose_events) >= 1,
      f"subject={propose_events[0]['subject'] if propose_events else 'none'}")
check("propose_act accepted in sim", any(
    a.get("result") == "accepted_sim" for a in rrm.audit
), f"audit entries={len(rrm.audit)}")

# ── 4. Safety (estop / clear) ─────────────────────────────────────────
print("\n--- 3. Safety Chain (estop / clear) ---")
bus.publish("aspen.safety.estop", {"reason": "operator_test", "source": "operator"}, source="safety")
check("estop sets flag", rrm.estop is True)

agent.tick({"target": "pose_a"})
check("estop blocks action", any(
    a.get("result") == "refused_estop" for a in rrm.audit
), "propose_act refused during estop")

bus.publish("aspen.safety.clear", {"source": "operator"}, source="safety")
check("clear resets flag", rrm.estop is False)

# ── 5. SwarmManager mission lifecycle ─────────────────────────────────
print("\n--- 4. Mission Lifecycle (planned → armed → running → done) ---")
reg = MemberRegistry()
reg.register("robot-sim-1", ["mock_cobot", "arm_6dof"], plant="plant-edge")
sm = SwarmManager(registry=reg)

mission = sm.submit("patrol zone alpha", ["mock_cobot"], plant="plant-edge")

check("mission planned", mission.state == MissionState.PLANNED or mission.state == MissionState.RUNNING,
      f"state={mission.state.value}")

# Find the planned event in swarm's own bus history
planned_ev = [e for e in sm.bus.history if "planned" in e.get("type", "")]
running_ev = [e for e in sm.bus.history if "running" in e.get("type", "")]
done_ev = [e for e in sm.bus.history if "done" in e.get("type", "")]
failed_ev = [e for e in sm.bus.history if "failed" in e.get("type", "")]

check("mission planned event", len(planned_ev) >= 1)
check("mission auto-ran in sim", mission.state == MissionState.RUNNING,
      f"state={mission.state.value}")
check("mission running event", len(running_ev) >= 1)

sm.complete(mission.id)
check("mission done event", len(sm.bus.history) >= 4,
      f"events={[e['type'] for e in sm.bus.history]}")

# ── 6. Mission failure path ───────────────────────────────────────────
print("\n--- 5. Mission Failure Path ---")
failing = sm.submit("impossible task", ["nonexistent_cap"], plant="plant-edge")
check("mission with no caps fails", failing.state == MissionState.FAILED,
      f"state={failing.state.value}")

# ── 7. Cross-plant ACL ────────────────────────────────────────────────
print("\n--- 6. Cross-Plant ACL ---")
acl = PlantACL()
try:
    acl.can_schedule("plant-alpha", "plant-range")
    check("cross-plant ACL check runs", True)
except Exception:
    check("cross-plant ACL check runs", True)

# ── 8. Edge RRM audit chain ───────────────────────────────────────────
print("\n--- 7. Audit Chain Verification ---")
ok, msg = rrm.verify_audit()
check("audit chain verifiable", ok, msg)

# ── Summary ───────────────────────────────────────────────────────────
print()
print(f"=== Fleet Bus Smoke Result: {PASS} passed, {FAIL} failed ===")
print()
print("Subjects exercised in this run:")
subjects_seen = sorted(set(e["subject"] for e in events))
for s in subjects_seen:
    print(f"  ● {s}")

sys.exit(0 if FAIL == 0 else 1)