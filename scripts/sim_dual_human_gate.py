#!/usr/bin/env python3
"""BEL-192 / H-016 G8: dual-human authorize gate proof harness.

Exercises the DualHumanGate library now living in the edge runtime
(aspen_edge.gate) and self-tests every refuse path plus the happy path.
Spec: docs/plans/ASP-364-dual-human-wire.md and
docs/plans/BEL-192-phase-d-physical-cell-gate.md.

Exit 0 = all refuse paths proven + happy path enables. Emits JSONL audit
events to stdout.
"""
import json
import sys
from pathlib import Path

# Shared library lives in the sibling aspen-edge-rrm checkout.
_REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (_REPO_ROOT.parent / "aspen-edge-rrm",):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from aspen_edge.gate import DualHumanGate, GateRefused, ENABLE_WINDOW_S
except ImportError as e:  # pragma: no cover
    print(
        f"error: cannot import aspen_edge.gate ({e}); "
        f"expected sibling checkout at {_p}",
        file=sys.stderr,
    )
    sys.exit(2)


def run_proofs():
    failures = []

    def make_gate(now):
        """Gate with JSONL stdout evidence; returns (gate, events)."""
        events = []

        def sink(event, data):
            rec = {"event": event, **data}
            events.append(rec)
            print(json.dumps(rec))

        return DualHumanGate(now=now, audit=sink), events

    def expect_refuse(name, fn, reason):
        g, _ = make_gate(lambda: 1000.0)
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

    # Case: unknown proposal refused and audited.
    expect_refuse(
        "unknown_proposal",
        lambda g: g.authorize("no-such-proposal", "bob"),
        "unknown_proposal",
    )

    # Case: enablement expires before execution.
    clock = {"t": 1000.0}
    g, _ = make_gate(lambda: clock["t"])
    pid = g.propose("cell-1", "jog_arm", "safety_adjacent", "op-alice")
    g.authorize(pid, "bob")
    g.authorize(pid, "carol")
    clock["t"] += ENABLE_WINDOW_S + 1
    expect_refuse("expired_enablement", lambda _: g.execute(pid, "runtime"), "expired")

    # Fail-safe: unknown/missing risk class must be treated safety_adjacent.
    g, _ = make_gate(lambda: 2000.0)
    pid = g.propose("cell-1", "jog_arm", None, "op-alice")
    if not g.held(pid):
        failures.append("failsafe_risk_class: missing risk_class did not hold")

    # Happy path: two distinct principals -> enabled -> executes.
    g, events = make_gate(lambda: 2000.0)
    pid = g.propose("cell-1", "jog_arm", "safety_adjacent", "op-alice")
    g.authorize(pid, "bob")
    g.authorize(pid, "carol")
    proof = g.execute(pid, "runtime")
    enables = [e for e in events if e["event"] == "enable_act"]
    execs = [e for e in events if e["event"] == "execute_act"]
    if len(enables) != 1 or sorted(enables[0]["principals_seen"]) != ["bob", "carol"]:
        failures.append("happy_path: enable record does not show exactly two distinct principals")
    if len(execs) != 1:
        failures.append("happy_path: act did not execute after dual authorization")
    if sorted(proof["principals_seen"]) != ["bob", "carol"]:
        failures.append("happy_path: execute proof lacks both principal ids")

    if failures:
        for f in failures:
            print(f"PROOF FAIL: {f}", file=sys.stderr)
        return False
    print(json.dumps({"proof": "dual_human_gate", "result": "pass",
                      "refuse_cases": 5, "happy_path": True,
                      "library": "aspen_edge.gate"}))
    return True


def _last(g):
    return list(g.proposals)[-1]


if __name__ == "__main__":
    sys.exit(0 if run_proofs() else 1)
