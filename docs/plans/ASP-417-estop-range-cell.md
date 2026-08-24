# ASP-417 / G7 — Estop Latch + Audit Hash Chain on the Range Cell

Issue: ASP-417 · Parent: ASP-381 · Linear [BEL-192](https://linear.app/bellahtech/issue/BEL-192/d1-first-physical-cell-gate-range-plant-only) · Epic BEL-179

Builds on: ASP-384 (dual-human authorize gate, `docs/plans/BEL-192-phase-d-physical-cell-gate.md`)
and BEL-191 (`aspen-edge-rrm/aspen_edge/audit.py` hash-chained `AuditLog`).

## Status

**G7.** Estop **latch** + **audit hash chain** on the nominated plant-range-cell node.
Sim drill only — no physical motion, no production plant, no live act. Live wiring
remains gated on G6 profile lock + captain $ ceiling + dual-auth path (ASP-384), which
are tracked separately.

## Threat Model

An emergency-stop press must be **latched** and **tamper-evidently audited**. Failure
modes to exclude:

- **Auto-clear / soft reset** — the estop state reverts without an explicit authorized
  clearance. The whole point of a latch is that one button press or one cleared flag
  cannot silently re-enable actuation.
- **Single-principal clear** — any human (including the person who caused the stop) can
  unlatch, with no second-party accountability.
- **Audit forgery / reordering** — an attacker or careless operator edits or deletes audit
  lines; the verifier must detect insertion, deletion, reordering, or tampering.
- **Act while latched** — an `act`/`propose_act` slips through while the cell is latched.

## Latch Semantics (range cell)

State is one of `armed` (normal), `latched` (estop pressed, refuses everything), and
`clearing` (authorized clear initiated). Transitions:

1. **Press** — `estop_press` → `latched`. Latched refuses every `propose_act`/`act`
   with `refused: estop_latched`. The latch cannot be toggled off by a plain flag write;
   only the authorized-clear path below returns the cell to `armed`.
2. **Refuse** — while `latched`, any actuation attempt is refused and that refusal is
   itself audited (so attempts are also evidence).
3. **Authorized clear** — two distinct human principals, neither the operator-of-record
   for the incident line, each submit `authorize_clear(cell_id)`. Both authorizations must
   be present **before** the latch releases. A single principal or the stop-causer cannot
   clear.
4. **Arm** — after both authorizations are recorded, `clear(cell_id)` releases to `armed`.

Mirrors the ASP-384 gate: no single principal may enable actuation after a safety stop.

## Audit Hash Chain

Every lifecycle event is appended to the range cell audit JSONL as an `AuditLog` record
(hash chained). Path: `ASPEN_AUDIT_PATH` (override for tests/sim), default
`/tmp/aspen-audit-<node>.jsonl`. Records carry `ts`, `event`, `data`, `prev` (prior
record hash, `GENESIS` for the first), and `hash` = SHA-256 over the canonical body. The
chain makes any insertion, deletion, reordering, or content edit detectable by
`verify_audit()`.

Event set:

| event | data | meaning |
| --- | --- | --- |
| `estop_press` | `cell`, `actor` | estop physically pressed; cell latched |
| `propose_act_refused` | `cell`, `skill`, `args`, `agent` | actuation refused while latched |
| `authorize_clear` | `cell`, `human_id` | one clearance authorization recorded (1/2) |
| `clear` | `cell`, `authorizers`, `decision` | both authorizations present → armed |

## Deliverable Mapping

1. **Estop drill procedure** (press → latch → refuse act → authorized clear) → this doc §"Latch Semantics" + `scripts/sim_estop_range_cell.py` (scripted drill).
2. **Audit JSONL path + `verify_audit()` pass evidence** → `aspen_edge.audit.AuditLog.append()`/`verify()`; sim prints JSONL evidence on stdout and exits 0 only when `verify_audit()` passes a full latch→refuse→clear drill.
3. **Sim drill acceptable first; live only after G6 profile lock + captain $ ceiling + dual-auth path** → this run executes the sim only; live-wiring is a separate follow-up gated on ASP-384/G6.

## Scripted Proof

```
python3 scripts/sim_estop_range_cell.py
```

Exit 0 = the full drill (press → latch → refuse act → dual-authorized clear → armed) runs
and `verify_audit()` confirms the hash chain is intact. Output is JSONL audit evidence plus
one final proof line. Self-tests also prove the must-fail cases:

- act refused while latched (`estop_latched`),
- single-principal clear refused (`insufficient_principals`),
- duplicate-principal clear refused (`duplicate_principal`),
- tampered audit line detected by `verify_audit()`.

## Co-owners

- **robotics** — execution (this issue).
- **auditor** — verify chain / refuse-path review (independent sign-off tracked in ASP-417 comments or a follow-up review ticket).

## Forbidden

Free motion, production plant, skip dual-auth on live act. This issue performs sim-only work; nothing here touches live hardware or the production plant.