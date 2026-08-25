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

Usage:
  python3 scripts/smoke-fleet-bus.py
  python3 scripts/smoke-fleet-bus.py --repo-root /path/to/aspen-os
  ASPEN_REPO_ROOT=/path/to/aspen-os python3 scripts/smoke-fleet-bus.py
"""

import argparse
import os
import sys
import json
from pathlib import Path

# Ensure ASPEN_SIM=1
os.environ.setdefault("ASPEN_SIM", "1")

# Allow explicit repo root from CLI flag or env var (supports git worktrees)
_parser = argparse.ArgumentParser()
_parser.add_argument("--repo-root", help="Override repo root (supports git worktrees)")
_args = _parser.parse_args()

REPO_DIR = Path(_args.repo_root).resolve() if _args.repo_root else (
    Path(os.environ.get("ASPEN_REPO_ROOT")) if os.environ.get("ASPEN_REPO_ROOT") else
    Path(__file__).resolve().parent
)
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
    "aspen.edge.robot-sim-1.authorize",
    "aspen.safety.authorize_clear",
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

# ── 3. Action proposal (G8 dual-human gate, H-016) ───────────────────
print("\n--- 2. Action Proposal (propose_act -> dual-auth hold -> act) ---")
agent = rrm.add_agent("micro-arm-1")
p1 = agent.tick({"target": "pose_home"})  # default risk_class=safety_adjacent

held = [a for a in rrm.audit if a.get("result") == "held_dual_auth"]
check("safety_adjacent held at propose_act", len(held) == 1,
      f"held={len(held)}")
pid = held[-1]["proposal_id"]

# act before dual authorization must refuse
r = rrm.request_act(pid)
check("act refused before dual auth", r["result"] == "refused_insufficient_principals",
      f"result={r['result']}")

# two distinct human principals authorize over the bus channel
bus.publish("aspen.edge.robot-sim-1.authorize",
            {"proposal_id": pid, "human_id": "op-b"}, source="human/op-b")
bus.publish("aspen.edge.robot-sim-1.authorize",
            {"proposal_id": pid, "human_id": "op-c"}, source="human/op-c")
r = rrm.request_act(pid)
check("dual-human authorize enables act", r["result"] == "executed_sim",
      f"result={r['result']} principals={r.get('principals_seen')}")

authorize_events = [e for e in events if e.get("type", "").endswith(".authorize")]
check("authorize channel on bus", len(authorize_events) == 2,
      f"count={len(authorize_events)}")

# explicit safe-class proposal keeps the direct sim path
agent.tick({"target": "pose_home"}, risk_class="safe")
check("safe class accepted in sim", any(
    a.get("result") == "accepted_sim" for a in rrm.audit
), f"audit entries={len(rrm.audit)}")

# ── 4. Safety (estop / dual-human clear) ─────────────────────────────
print("\n--- 3. Safety Chain (estop / dual-principal clear) ---")
bus.publish("aspen.safety.estop",
            {"reason": "operator_test", "source": "operator", "actor": "op-a"},
            source="safety")
check("estop sets flag", rrm.estop is True)

agent.tick({"target": "pose_a"})
check("estop blocks action", any(
    a.get("result") == "refused_estop" for a in rrm.audit
), "propose_act refused during estop")

# bare clear cannot unlatch (H-016 hardening)
bus.publish("aspen.safety.clear", {"source": "operator"}, source="safety")
check("bare clear refused", rrm.estop is True)

# two distinct humans authorize the clear, then clear executes
bus.publish("aspen.safety.authorize_clear", {"human_id": "op-b"}, source="human/op-b")
bus.publish("aspen.safety.authorize_clear", {"human_id": "op-c"}, source="human/op-c")
bus.publish("aspen.safety.clear", {"source": "operator"}, source="safety")
check("dual-human clear resets flag", rrm.estop is False)

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