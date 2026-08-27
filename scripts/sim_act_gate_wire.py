#!/usr/bin/env python3
"""BEL-192 / H-016 ASP-364 G8: end-to-end dual-human act-gate wire drill.

Drives the live EdgeRRM control path (aspen_edge.rrm) through:
  propose -> held_dual_auth -> authorize A/B -> request_act -> executed_sim,
plus every must-fail case (single principal, duplicate principal,
self-approval, estop-latched act, single-principal estop clear).

All events land in the hash-chained AuditLog; exit 0 requires
verify_audit() to pass after the full drill. Sim only: no physical motion,
no ASPEN_SIM=0 drivers.
"""

import json
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (_REPO_ROOT.parent / "aspen-edge-rrm",):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from aspen_edge import EdgeRRM, FleetBus, GateRefused, ProposeAct
except ImportError as e:  # pragma: no cover
    print(f"error: cannot import aspen_edge ({e}); expected sibling checkout at {_p}",
          file=sys.stderr)
    sys.exit(2)


def _emit(rec):
    print(json.dumps({k: rec[k] for k in rec if k != "hash"}, sort_keys=True,
                     default=str))


def main() -> int:
    audit_path = Path(tempfile.mktemp(suffix="-act-gate-wire.jsonl"))
    rrm = EdgeRRM("range-cell-sim-1", FleetBus(), plant="plant-range",
                  operator_of_record="op-alice", audit_path=str(audit_path))
    rrm.start()
    rrm.add_agent("agent-m1")
    failures = []

    def check(name, cond):
        if not cond:
            failures.append(name)

    # 1. propose -> held_dual_auth (safety_adjacent is the fail-safe default)
    rec = rrm.handle_propose(ProposeAct("jog_arm", {"target": "home"}, "agent-m1"))
    check("propose_held", rec["result"] == "held_dual_auth" and "proposal_id" in rec)
    pid = rec["proposal_id"]
    _emit(rec)

    # 2. act before authorizations refused
    rec = rrm.request_act(pid, "sim-runtime")
    check("refused_insufficient_principals",
          rec["result"] == "refused_insufficient_principals")
    _emit(rec)

    # 3. self-approval refused (approver == operator-of-record)
    try:
        rrm.authorize(pid, "op-alice")
        failures.append("self_approval_not_refused")
    except GateRefused as e:
        check("self_approval_reason", e.reason == "self_approval")

    # 4. duplicate principal refused (same human, second session)
    rrm.authorize(pid, "bob", note="matrix #aspen-authz session A")
    try:
        rrm.authorize(pid, "bob")
        failures.append("duplicate_principal_not_refused")
    except GateRefused as e:
        check("duplicate_principal_reason", e.reason == "duplicate_principal")
    rec = rrm.request_act(pid, "sim-runtime")
    check("still_refused_one_principal",
          rec["result"] == "refused_insufficient_principals")

    # 5. second distinct human -> enable window opens -> act executes
    rrm.authorize(pid, "carol", note="sentinel UI approval")
    rec = rrm.request_act(pid, "sim-runtime")
    check("executed_after_dual_auth", rec["result"] == "executed_sim"
          and sorted(rec["principals_seen"]) == ["bob", "carol"])
    _emit(rec)

    # 6. authorize channel reachable over the bus (human front-end contract)
    rec2 = rrm.handle_propose(ProposeAct("set_payload", {}, "agent-m1"))
    pid2 = rec2["proposal_id"]
    rrm.bus.publish(f"aspen.edge.{rrm.node_id}.authorize",
                    {"proposal_id": pid2, "human_id": "bob"}, source="human/bob")
    rrm.bus.publish(f"aspen.edge.{rrm.node_id}.authorize",
                    {"proposal_id": pid2, "human_id": "carol"}, source="human/carol")
    rec2 = rrm.request_act(pid2, "sim-runtime")
    check("bus_authorize_path", rec2["result"] == "executed_sim")

    # 7. estop latched refuses new proposals outright
    rrm.bus.publish("aspen.safety.estop", {"reason": "drill", "actor": "op-dave"},
                    source="operator/op-dave")
    rec3 = rrm.handle_propose(ProposeAct("jog_arm", {}, "agent-m1"))
    check("estop_blocks_proposal", rec3["result"] == "refused_estop")

    # 8. estop clear: bare clear + single authorization cannot unlatch;
    #    stop-causer cannot authorize; two distinct humans can.
    rrm.bus.publish("aspen.safety.clear", {}, source="gate")
    check("bare_clear_no_unlatch", rrm.estop)
    rrm.bus.publish("aspen.safety.authorize_clear", {"human_id": "bob"}, source="human/bob")
    rrm.bus.publish("aspen.safety.clear", {}, source="gate")
    check("single_clear_no_unlatch", rrm.estop)
    rrm.bus.publish("aspen.safety.authorize_clear", {"human_id": "op-dave"},
                    source="human/op-dave")
    rrm.bus.publish("aspen.safety.clear", {}, source="gate")
    check("stop_causer_cannot_clear", rrm.estop)
    rrm.bus.publish("aspen.safety.authorize_clear", {"human_id": "carol"},
                    source="human/carol")
    rrm.bus.publish("aspen.safety.clear", {}, source="gate")
    check("dual_clear_arms", not rrm.estop)

    ok, msg = rrm.verify_audit()
    check("audit_chain_intact", ok)
    if not ok:
        print(f"audit verify failed: {msg}", file=sys.stderr)

    if failures:
        for f in failures:
            print(f"DRILL FAIL: {f}", file=sys.stderr)
        print(json.dumps({"proof": "act_gate_wire", "result": "fail",
                          "failures": failures}), file=sys.stderr)
        return 1

    print(json.dumps({"proof": "act_gate_wire", "result": "pass",
                      "events": len(rrm.audit),
                      "audit_events": len(audit_path.read_text().splitlines()),
                      "verify_audit": msg,
                      "refuse_cases": ["insufficient_principals", "duplicate_principal",
                                       "self_approval", "estop_latched",
                                       "estop_single_clear"],
                      "happy_path": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
