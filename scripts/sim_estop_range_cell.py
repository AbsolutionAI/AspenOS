#!/usr/bin/env python3
"""BEL-192 / ASP-417 G7: Estop latch + audit hash chain sim drill (range cell).

Implements the estop latch state machine specified in
docs/plans/ASP-417-estop-range-cell.md and self-tests every refuse path plus
the full drill: press -> latch -> refuse act -> dual-authorized clear -> armed.

Uses the hash-chained AuditLog from aspen_edge.audit for tamper-evident audit.
Exit 0 = all proofs pass + verify_audit() confirms the chain is intact.
"""

from __future__ import annotations
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Inline hash-chained audit log (mirrors aspen_edge.audit.AuditLog contract)
# so the sim is self-contained. Production EdgeRRM uses the same algorithm.
# ---------------------------------------------------------------------------

def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


class AuditLog:
    """Append-only hash-chained audit log. Every record carries a SHA-256
    hash of the previous record, forming a tamper-evident chain."""

    GENESIS = "GENESIS"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash: str = self.GENESIS
        if self.path.exists() and self.path.stat().st_size > 0:
            self._recover_last_hash()

    def _recover_last_hash(self) -> None:
        last = None
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last = json.loads(line)
        if last and "hash" in last:
            self._last_hash = last["hash"]

    def append(self, event: str, data: dict[str, Any] | None = None) -> dict:
        rec = {
            "ts": time.time(),
            "event": event,
            "data": data or {},
            "prev": self._last_hash,
        }
        body = _canon({k: rec[k] for k in ("ts", "event", "data", "prev")})
        rec["hash"] = hashlib.sha256(body.encode()).hexdigest()
        line = json.dumps(rec, sort_keys=True) + "\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        self._last_hash = rec["hash"]
        return rec

    def verify(self) -> tuple[bool, str]:
        prev = self.GENESIS
        if not self.path.exists():
            return True, "empty"
        with self.path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("prev") != prev:
                    return False, f"line {i} prev mismatch: expected {prev!r}, got {rec.get('prev')!r}"
                body = _canon({k: rec[k] for k in ("ts", "event", "data", "prev")})
                expected = hashlib.sha256(body.encode()).hexdigest()
                if rec.get("hash") != expected:
                    return False, f"line {i} hash mismatch"
                prev = rec["hash"]
        return True, "ok"

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Estop Latch — range cell state machine
# ---------------------------------------------------------------------------

class EstopLatchError(Exception):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


class EstopLatch:
    """Estop latch for a range cell.

    States:
        armed   — normal, actuation allowed
        latched — estop pressed, all actuation refused
        (authorized-clear path transitions back to armed)

    Audit events:
        estop_press               — press latches the cell
        propose_act_refused       — actuation refused while latched
        authorize_clear           — one human clears (1/2)
        clear                     — both principals present -> armed
    """

    def __init__(self, cell_id: str, audit: AuditLog) -> None:
        self.cell_id = cell_id
        self.audit = audit
        self.armed: bool = True
        self._clear_authorizations: dict[str, float] = {}  # human_id -> ts

    # -- Query helpers (no audit side effects) --

    def is_latched(self) -> bool:
        return not self.armed

    # -- Actions --

    def press(self, actor: str) -> dict:
        """Press the estop button. Latches the cell."""
        if not self.armed:
            # Already latched: pressing again is a no-op but still recorded
            rec = self.audit.append("estop_press", {"cell": self.cell_id, "actor": actor, "note": "already_latched"})
            return rec
        self.armed = False
        self._clear_authorizations.clear()
        rec = self.audit.append("estop_press", {"cell": self.cell_id, "actor": actor})
        return rec

    def propose_act(self, agent_id: str, skill: str, args: dict[str, Any]) -> dict:
        """Attempt an actuation. Refused while latched."""
        base = {"cell": self.cell_id, "skill": skill, "args": args, "agent": agent_id}
        if not self.armed:
            rec = self.audit.append("propose_act_refused", {**base, "reason": "estop_latched"})
            return rec
        rec = self.audit.append("propose_act", {**base, "result": "accepted"})
        return rec

    def authorize_clear(self, human_id: str) -> dict:
        """A human authorizes the clear. Requires two distinct humans."""
        if self.armed:
            raise EstopLatchError("not_latched", "cell is already armed")
        if human_id in self._clear_authorizations:
            rec = self.audit.append("authorize_clear_refused", {
                "cell": self.cell_id, "human_id": human_id, "reason": "duplicate_principal",
            })
            raise EstopLatchError("duplicate_principal", f"human {human_id} already authorized")
        self._clear_authorizations[human_id] = time.time()
        count = len(self._clear_authorizations)
        rec = self.audit.append("authorize_clear", {
            "cell": self.cell_id, "human_id": human_id, "count": f"{count}/2",
        })
        return rec

    def clear(self, executor: str = "gate") -> dict:
        """Execute the clear after dual authorization. Arms the cell."""
        if self.armed:
            raise EstopLatchError("not_latched", "cell is already armed")
        authorizers = sorted(self._clear_authorizations)
        if len(authorizers) < 2:
            rec = self.audit.append("clear_refused", {
                "cell": self.cell_id, "executor": executor,
                "authorizers": authorizers, "reason": "insufficient_principals",
            })
            raise EstopLatchError("insufficient_principals", f"got {len(authorizers)}/2 authorizations")
        # Check for duplicates (shouldn't happen due to authorize_clear guard, but belt-and-suspenders)
        if len(authorizers) != len(set(authorizers)):
            rec = self.audit.append("clear_refused", {
                "cell": self.cell_id, "executor": executor,
                "authorizers": authorizers, "reason": "duplicate_principal",
            })
            raise EstopLatchError("duplicate_principal", "duplicate principal in authorizations")
        self.armed = True
        authorizers = sorted(self._clear_authorizations)
        rec = self.audit.append("clear", {
            "cell": self.cell_id, "executor": executor,
            "authorizers": authorizers, "decision": "armed",
        })
        self._clear_authorizations.clear()
        return rec

    def verify_audit(self) -> tuple[bool, str]:
        """Verify the hash chain integrity of the audit log."""
        return self.audit.verify()


# ---------------------------------------------------------------------------
# Proofs
# ---------------------------------------------------------------------------

def _run_full_drill() -> None:
    """Press -> latch -> refuse act -> dual-authorized clear -> armed.
    This is the primary deliverable drill."""
    audit = AuditLog(tempfile.mktemp(suffix="-estop-drill.jsonl"))
    cell = EstopLatch("range-cell-1", audit)

    # 1. Press — latches the cell
    r1 = cell.press("op-alice")
    assert not cell.armed, "cell should be latched after press"
    assert r1["event"] == "estop_press"
    assert r1["data"]["actor"] == "op-alice"
    print(json.dumps(r1))

    # 2. Refuse — propose_act while latched is refused
    r2 = cell.propose_act("m1", "jog_arm", {"target": "home"})
    assert r2["event"] == "propose_act_refused"
    assert r2["data"]["reason"] == "estop_latched"
    print(json.dumps(r2))

    # 3. Authorize clear — two distinct humans
    r3a = cell.authorize_clear("bob")
    assert r3a["event"] == "authorize_clear"
    assert r3a["data"]["count"] == "1/2"
    print(json.dumps(r3a))

    r3b = cell.authorize_clear("carol")
    assert r3b["event"] == "authorize_clear"
    assert r3b["data"]["count"] == "2/2"
    print(json.dumps(r3b))

    # 4. Clear — arms the cell
    r4 = cell.clear("gate")
    assert r4["event"] == "clear"
    assert r4["data"]["decision"] == "armed"
    assert cell.armed, "cell should be armed after clear"
    print(json.dumps(r4))

    # 5. Verify chain integrity
    ok, msg = cell.verify_audit()
    assert ok, f"audit chain verification failed: {msg}"

    # 6. Post-clear actuation works
    r5 = cell.propose_act("m1", "jog_arm", {"target": "home"})
    assert r5["event"] == "propose_act"
    assert r5["data"]["result"] == "accepted"
    print(json.dumps(r5))

    print(json.dumps({"proof": "full_drill", "result": "pass", "events": len(audit.read_all())}))


def _run_refuse_proofs() -> list[str]:
    """Self-test each must-fail case."""
    failures: list[str] = []

    def expect_refuse(name: str, fn, expected_reason: str) -> None:
        try:
            fn()
            failures.append(f"{name}: expected EstopLatchError, got success")
        except EstopLatchError as e:
            if e.reason != expected_reason:
                failures.append(f"{name}: refused with {e.reason!r}, expected {expected_reason!r}")

    # Case 1: propose_act refused while latched
    def case_single_refuse():
        audit = AuditLog(tempfile.mktemp(suffix="-refuse1.jsonl"))
        c = EstopLatch("range-cell-1", audit)
        c.press("op-alice")
        rec = c.propose_act("m1", "move", {})
        # Should produce a refused event, not raise — but we verify the event
        assert rec["event"] == "propose_act_refused", f"expected refuse event, got {rec['event']}"
        assert rec["data"]["reason"] == "estop_latched", f"expected estop_latched reason, got {rec['data']['reason']}"
    case_single_refuse()

    # Case 2: single-principal clear refused
    expect_refuse(
        "single_principal_clear",
        lambda: (
            lambda a, c: (c.press("op-alice"), c.authorize_clear("bob"), c.clear("gate"))
        )(AuditLog(tempfile.mktemp(suffix="-refuse2.jsonl")), EstopLatch("range-cell-1", AuditLog(tempfile.mktemp(suffix="-refuse2b.jsonl")))),
        "insufficient_principals",
    )

    # Case 3: duplicate principal authorized clear
    def case_duplicate_authorize():
        audit = AuditLog(tempfile.mktemp(suffix="-refuse3.jsonl"))
        c = EstopLatch("range-cell-1", audit)
        c.press("op-alice")
        c.authorize_clear("bob")
        try:
            c.authorize_clear("bob")
            failures.append("duplicate_authorize: expected EstopLatchError, got success")
        except EstopLatchError as e:
            if e.reason != "duplicate_principal":
                failures.append(f"duplicate_authorize: refused with {e.reason!r}, expected 'duplicate_principal'")
    case_duplicate_authorize()

    # Case 4: tampered audit line detected by verify_audit()
    def case_tampered_audit():
        audit = AuditLog(tempfile.mktemp(suffix="-refuse4.jsonl"))
        c = EstopLatch("range-cell-1", audit)
        c.press("op-alice")
        c.propose_act("m1", "move", {})
        # Tamper: modify the second line's event
        lines = audit.path.read_text(encoding="utf-8").splitlines()
        modified = lines[1].replace('"propose_act_refused"', '"propose_act"')
        lines[1] = modified
        audit.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok, msg = audit.verify()
        if ok:
            failures.append("tampered_audit: verify() returned True despite tampered line")
        else:
            print(json.dumps({"proof": "tamper_detection", "result": "pass", "detail": msg}))
    case_tampered_audit()

    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("BEL-192 / ASP-417 G7: Estop Latch + Audit Hash Chain Drill")
    print("=" * 60)

    # Full drill
    print("\n--- Full drill: press -> latch -> refuse act -> authorized clear -> armed ---")
    _run_full_drill()
    print("  [PASS]")

    # Refuse proofs
    print("\n--- Refuse path proofs ---")
    refuse_failures = _run_refuse_proofs()
    if refuse_failures:
        for f in refuse_failures:
            print(f"  [FAIL] {f}", file=sys.stderr)
        print(json.dumps({"proof": "refuse_paths", "result": "fail", "failures": len(refuse_failures)}))
        return 1

    print("  [PASS] all refuse paths proven")

    # Summary
    print("\n" + "=" * 60)
    print(json.dumps({
        "proof": "estop_range_cell",
        "result": "pass",
        "drill": "press->latch->refuse->dual_clear->armed",
        "refuse_cases": 4,
        "audit_chain": "sha256_hash_chain",
        "verify_audit": "pass",
    }))
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())