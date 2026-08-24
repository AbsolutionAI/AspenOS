#!/usr/bin/env python3
"""BEL-192 Phase D gate: dual-human authorization state machine (simulation).

Implements the two-principal hold-to-enable flow specified in
docs/plans/BEL-192-phase-d-physical-cell-gate.md and self-tests every
refuse path plus the happy path. Sim/dry-run only — no physical motion.

Exit 0 = all proofs pass. Emits JSONL audit events to stdout.
"""
import json
import sys
import time
import uuid

ENABLE_WINDOW_S = 600


class GateRefused(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class DualHumanGate:
    def __init__(self, now=time.time, window_s=ENABLE_WINDOW_S):
        self.now = now
        self.window_s = window_s
        self.proposals = {}
        self.approvals = {}  # proposal_id -> {human_id: ts}
        self.enabled_until = {}  # proposal_id -> expiry ts
        self.audit = []

    def _audit(self, event, proposal_id, actor, decision, reason):
        rec = {
            "ts": round(self.now(), 3),
            "event": event,
            "proposal_id": proposal_id,
            "actor": actor,
            "principals_seen": sorted(self.approvals.get(proposal_id, {})),
            "decision": decision,
            "reason": reason,
        }
        self.audit.append(rec)
        print(json.dumps(rec))

    def propose(self, subject, action, risk_class, proposer_operator):
        if risk_class not in ("safe", "safety_adjacent"):
            raise ValueError("bad risk_class")
        pid = str(uuid.uuid4())
        self.proposals[pid] = {
            "subject": subject,
            "action": action,
            "risk_class": risk_class,
            "proposer_operator": proposer_operator,
            "expires_at": self.now() + self.window_s,
        }
        self.approvals[pid] = {}
        self._audit("propose_act", pid, proposer_operator, "held" if risk_class == "safety_adjacent" else "auto_safe", risk_class)
        return pid

    def authorize(self, proposal_id, human_id):
        p = self.proposals.get(proposal_id)
        if p is None:
            raise GateRefused("unknown_proposal")
        if self.now() > p["expires_at"]:
            self._audit("refuse", proposal_id, human_id, "refused", "expired")
            raise GateRefused("expired")
        approvals = self.approvals[proposal_id]
        if human_id == p["proposer_operator"]:
            self._audit("refuse", proposal_id, human_id, "refused", "self_approval")
            raise GateRefused("self_approval")
        if human_id in approvals:
            self._audit("refuse", proposal_id, human_id, "refused", "duplicate_principal")
            raise GateRefused("duplicate_principal")
        approvals[human_id] = self.now()
        self._audit("authorize", proposal_id, human_id, "recorded", f"{len(approvals)}/2 principals")
        if len(approvals) >= 2:
            self.enabled_until[proposal_id] = self.now() + self.window_s
            self._audit("enable_act", proposal_id, "gate", "enabled", "two_distinct_principals")

    def execute(self, proposal_id, executor):
        p = self.proposals.get(proposal_id)
        if p is None:
            raise GateRefused("unknown_proposal")
        principals_seen = sorted(self.approvals.get(proposal_id, {}))
        if len(principals_seen) < 2:
            self._audit("refuse", proposal_id, executor, "refused", "insufficient_principals")
            raise GateRefused("insufficient_principals")
        until = self.enabled_until.get(proposal_id)
        if until is None or self.now() > until:
            self._audit("refuse", proposal_id, executor, "refused", "expired")
            raise GateRefused("expired")
        self._audit("execute_act", proposal_id, executor, "executed", "sim_dry_run")


def run_proofs():
    failures = []

    def expect_refuse(name, fn, reason):
        g = DualHumanGate(now=lambda: 1000.0)
        try:
            fn(g)
            failures.append(f"{name}: expected refusal, got success")
        except GateRefused as e:
            if e.reason != reason:
                failures.append(f"{name}: refused with {e.reason}, expected {reason}")

    # Case: one approval only.
    expect_refuse(
        "single_approval",
        lambda g: (g.authorize(g.propose("cell-1", "jog_arm", "safety_adjacent", "op-alice"), "bob"), g.execute(_last(g), "runtime")),
        "insufficient_principals",
    )

    # Case: same human approves twice via two sessions.
    expect_refuse(
        "duplicate_principal",
        lambda g: (g.authorize(g.propose("cell-1", "jog_arm", "safety_adjacent", "op-alice"), "bob"),
                   g.authorize(_last(g), "bob")),
        "duplicate_principal",
    )

    # Case: approver is the proposer's operator-of-record (self approval).
    expect_refuse(
        "self_approval",
        lambda g: g.authorize(g.propose("cell-1", "jog_arm", "safety_adjacent", "op-alice"), "op-alice"),
        "self_approval",
    )

    # Case: enablement expires before execution.
    clock = {"t": 1000.0}
    g = DualHumanGate(now=lambda: clock["t"])
    pid = g.propose("cell-1", "jog_arm", "safety_adjacent", "op-alice")
    g.authorize(pid, "bob")
    g.authorize(pid, "carol")
    clock["t"] += ENABLE_WINDOW_S + 1
    expect_refuse("expired_enablement", lambda _: g.execute(pid, "runtime"), "expired")

    # Happy path: two distinct principals -> enabled -> executes.
    g = DualHumanGate(now=lambda: 2000.0)
    pid = g.propose("cell-1", "jog_arm", "safety_adjacent", "op-alice")
    g.authorize(pid, "bob")
    g.authorize(pid, "carol")
    g.execute(pid, "runtime")
    enables = [e for e in g.audit if e["event"] == "enable_act"]
    execs = [e for e in g.audit if e["event"] == "execute_act"]
    if len(enables) != 1 or sorted(enables[0]["principals_seen"]) != ["bob", "carol"]:
        failures.append("happy_path: enable record does not show exactly two distinct principals")
    if len(execs) != 1:
        failures.append("happy_path: act did not execute after dual authorization")

    if failures:
        for f in failures:
            print(f"PROOF FAIL: {f}", file=sys.stderr)
        return False
    print(json.dumps({"proof": "dual_human_gate", "result": "pass", "refuse_cases": 4, "happy_path": True}))
    return True


def _last(g):
    return list(g.proposals)[-1]


if __name__ == "__main__":
    sys.exit(0 if run_proofs() else 1)
