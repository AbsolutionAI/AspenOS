# BEL-192 Phase D Gate G3 — Dual-Human Authorization for propose_act→act

Issue: ASP-384 (done) · Parent: ASP-381 · Linear [BEL-192](https://linear.app/bellahtech/issue/BEL-192/d1-first-physical-cell-gate-range-plant-only) · Epic BEL-179

Parent checklist: `docs/plans/BEL-192-phase-d-physical-cell-gate.md`

## Status

**GREEN (sim/dry-run)** — specification + scripted refuse-path proof complete. No physical motion, no hardware spend. Wiring into the live Hermes propose_act→act path is tracked separately (H-016 / ASP-364).

## Threat Model

Safety-adjacent subjects (anything that can move hardware, spend cash, or mutate fleet state) must not be actable by a single principal, even a privileged one. Failure modes to exclude:

- **Self-approval**: the proposing agent's operator authorizes their own proposal.
- **Same-identity replay**: the same human approving twice under two sessions.
- **Rubber-stamp latency**: approval window too short for real review.

## Required Flow (two-principal hold-to-enable)

1. **Propose** — an agent emits a `propose_act` event carrying:
   - `subject` (target system/cell), `action`, `risk_class` (`safe | safety_adjacent`),
   - `proposer` identity, `proposal_id` (uuid), `expires_at`.
2. **Hold** — proposals with `risk_class=safety_adjacent` enter a hold state. Nothing executes.
3. **Dual authorize** — two *distinct* human principals must each submit `authorize(proposal_id)`:
   - Principal A ≠ Principal B (distinct stable human ids; device/session ids do not count).
   - Neither principal may be the proposer's operator-of-record.
   - Each authorization carries its own timestamp, reason string, and audit signature.
4. **Enable window** — once both approvals exist, `act` is enabled for a bounded window
   (default 10 minutes). A single new `propose_act` is required after expiry.
5. **Execute** — the runtime verifies the two-signature record immediately before `act`
   executes; verification failure aborts with a refusal event.

## Refuse Path (must-fail cases)

The gate MUST refuse single-principal enablement in all of these cases:

| Case | Result |
| --- | --- |
| One approval only | Refused: `insufficient_principals` |
| Same human approves twice (any session/device) | Refused: `duplicate_principal` |
| Approver == proposer's operator-of-record | Refused: `self_approval` |
| Either approval outside enable window / expired proposal | Refused: `expired` |

## Audit Evidence

Every `authorize`, refusal, enablement, and execution emits a JSONL audit event
(`audit/act-gate.jsonl`) containing: `ts`, `event`, `proposal_id`, `actor`,
`principals_seen`, `decision`, `reason`. A compliant enablement record shows exactly
two distinct principals; a refused record shows the refuse reason from the table above.

## Scripted Proof

`scripts/sim_dual_human_gate.py` implements this state machine in simulation and
self-tests every refuse case plus one happy path:

```
python3 scripts/sim_dual_human_gate.py
```

Exit 0 = all refuse paths proven + happy path enables. Output is JSONL evidence
suitable for linking on BEL-192 and the Phase D gate review.

## Exit Criteria Mapping

- Documented flow → this document.
- Automated/scripted refuse path for single auth → `scripts/sim_dual_human_gate.py` (refuse-case suite).
- Audit/event evidence two principals required → JSONL events emitted by the simulator; live-wiring evidence deferred to H-016.
