# ASP-364 / H-016 — Wire Dual-Human Authorize Gate for propose_act→act

Issue: ASP-364 · Parent: ASP-298 (Threat Model v2.2, F-017 CRITICAL) · G8 of BEL-192 Phase D

Builds on:

- ASP-384 / G3 — sim gate spec + refuse proofs (`docs/plans/BEL-192-phase-d-physical-cell-gate.md`, `scripts/sim_dual_human_gate.py`)
- ASP-416 / G6 — cell profile + hold-to-enable (`docs/robotics/plant-range-cell-profile.yaml`)
- ASP-417 / G7 — estop latch + audit hash chain (`scripts/sim_estop_range_cell.py`, `aspen_edge.audit.AuditLog`)

## Status

**G8 wire (sim/live-control-path only).** Promotes the DualHumanGate from a
script-only simulator into the importable edge runtime control path. Safety-adjacent
proposals hold at `propose_act` until two distinct human principals authorize; the
propose_act→act transition verifies the two-principal record immediately before act.
No physical motion, no `ASPEN_SIM=0` drivers, cell stays `status: sim_only`.

## Threat model (F-017)

A single principal — even a privileged one or the proposing agent's own operator —
must never be able to move hardware, spend cash, or mutate fleet state. Excluded
failure modes (must-fail cases):

| Case | Refuse reason |
| --- | --- |
| One approval only | `insufficient_principals` |
| Same human approves twice (any session/device) | `duplicate_principal` |
| Approver == proposer's operator-of-record | `self_approval` |
| Approval/enable outside window or expired proposal | `expired` |
| Act attempt while estop latched | `estop_latched` |
| Estop clear by fewer than two distinct humans | `insufficient_principals` |

## Design

### 1. Library extract (`aspen-edge-rrm/aspen_edge/gate.py`)

Move the dual-human state machine out of script-only so edge/runtime can import it:

- `GateRefused(reason)` exception; reasons are the stable contract strings above.
- `DualHumanGate(now=..., window_s=600, audit=None)`:
  - `propose(subject, action, risk_class, proposer_operator) -> proposal_id`
    - `risk_class ∈ {safe, safety_adjacent}`; unknown values are treated as
      `safety_adjacent` (fail-safe).
  - `authorize(proposal_id, human_id)` — enforces expiry, self-approval,
    duplicate-principal refuses; records principal + ts.
  - `execute(proposal_id, executor)` — verifies ≥2 distinct principals AND live
    enable window immediately before act; refuses otherwise.
  - Audit sink is injectable (defaults to JSONL stdout-style callback) so
    EdgeRRM can route events into the hash-chained `AuditLog`.
- `scripts/sim_dual_human_gate.py` remains the proof harness and imports the
  library (sibling-repo path auto-inserted); all four refuse proofs + happy path
  must stay green.

### 2. propose_act→act wiring (`aspen-edge-rrm/aspen_edge/rrm.py`)

- `ProposeAct` gains `risk_class` (default `"safety_adjacent"` — fail-safe).
- `EdgeRRM.handle_propose` order of checks (all audited):
  1. estop latched → `refused_estop` (existing, unchanged)
  2. bus down → `queued_offline` (existing, unchanged)
  3. `risk_class=safety_adjacent` → gate hold; record carries `proposal_id`,
     `result="held_dual_auth"`. Nothing executes.
  4. `risk_class=safe` → existing `accepted_sim` path.
- Human authorize channel: bus subject `aspen.edge.<node>.authorize` with payload
  `{proposal_id, human_id}` → `EdgeRRM.authorize(...)`. This is the local/NATS
  channel two humans drive in sim; the Matrix `#aspen-authz` room is a documented
  front-end onto the same payload schema (bridge not required for G8).
- Act transition: `EdgeRRM.request_act(proposal_id, executor)` calls
  `gate.execute(...)` immediately before any execution and emits audited
  `execute_act`; every refusal emits an audited refuse event. No silent auto-act.
- Enable window default 600s, overridable via `ASPEN_GATE_WINDOW_S` (tests/sim).

### 3. Estop clear stays human-only + authenticated

G7 sim already models dual-human clear; the live `EdgeRRM._on_clear` currently
trusts any `aspen.safety.clear` message. Harden without weakening:

- `_on_clear` no longer unlatches directly. New bus subject
  `aspen.safety.authorize_clear` carries `{human_id}`; two distinct principals
  arm the clear, then `aspen.safety.clear` executes it. Any single-principal
  clear attempt is refused and audited (`insufficient_principals`,
  `duplicate_principal`). Press/latch semantics unchanged.

### 4. Audit

Every propose/held/authorize/enable/refuse/execute/clear event goes through the
existing hash-chained `AuditLog` (`_record`), carrying principal ids and reasons.
`verify_audit()` must pass after the full drill.

### 5. Cell profile + docs (this repo)

- `docs/robotics/plant-range-cell-profile.yaml`: add `dual_auth` block under
  `safety` (required, principals=2 distinct humans, window_s=600, audit events),
  extend refuse reason list, mark lifecycle `g8: dual_auth_wired_sim` while
  keeping `status: sim_only` and isolation ACL untouched.
- Matrix `#aspen-authz` contract: document approve-payload schema and mapping to
  the bus authorize channel (`docs/robotics/plant-range-arm-runbook.md` §G8 +
  `docs/security/ACT_GATE_CONTRACT.md`). Bridge wiring stays nice-to-have.
- `docs/SECURITY.md` H-016 checklist entry updated when wired.
- `docs/robotics/README.md` gate table corrected to point G8 at ASP-364.

### 6. Sim isolation (AC)

All executable paths here run under `ASPEN_SIM` assumptions; nothing sets
`ASPEN_SIM=0`, no driver starts, no joint motion. Cell profile keeps
`status: sim_only` + empty `acl_outbound`. The gate library itself has no I/O.

## Acceptance criteria (restated)

- [x] `propose_act` cannot transition to `act` without two distinct human approvals — proven by refuse-case tests + sim drill.
- [x] Authz path records both approvals with audit trail (hash-chained JSONL; Matrix/local channel documented with payload schema).
- [x] Estop clear remains human-only and authenticated (dual distinct principals; single/duplicate refused + audited).
- [x] Documented sim path (`ASPEN_SIM`) stays isolated from production arm (no `ASPEN_SIM=0`, cell `status: sim_only`).

## QA plan

1. `python3 scripts/sim_dual_human_gate.py` (refuse suite + happy path, exit 0)
2. `python3 scripts/sim_estop_range_cell.py` (G7 regression, exit 0)
3. `python3 -m pytest ../aspen-edge-rrm/tests` (gate + rrm wiring incl. estop-clear hardening)
4. New end-to-end sim drill: propose → held → authorize A/B → request_act → executed, plus every refuse case, all under injected clock.

## Out of scope

- Live Matrix bridge deployment (contract documented only)
- Captain $ ceiling (G9), any physical motion, production plant
- Sentinel UI implementation (schema documented for it)
