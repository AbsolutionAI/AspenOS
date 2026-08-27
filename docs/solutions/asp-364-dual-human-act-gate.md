# ASP-364 — Wiring a dual-human authorize gate without breaking the fleet

**Issue:** [ASP-364](/ASP/issues/ASP-364) (H-016, F-017 CRITICAL) · **Gate:** BEL-192 G8 · **Date:** 2026-08-24

## Problem

Master Spec hard rule: safety-adjacent subjects may only publish
`propose_act` until two distinct human principals authorize. The gate existed
only as a self-contained sim (`scripts/sim_dual_human_gate.py`, ASP-384); the
live edge control path (`aspen_edge.rrm.EdgeRRM.handle_propose`) accepted any
proposal not blocked by estop, and `_on_clear` unlatched on any bare
`aspen.safety.clear` bus message.

## What was done

- Extracted the state machine into `aspen_edge.gate.DualHumanGate`
  (sibling repo `aspen-edge-rrm`) with an injectable clock/window and an
  injectable audit sink; the aspen-os sim script became a proof harness that
  imports it.
- `EdgeRRM` now holds safety_adjacent proposals (`held_dual_auth`,
  carrying a `proposal_id`) and exposes `request_act()`, which re-verifies
  the two-principal record plus enable window immediately before act.
  Human approvals arrive on `aspen.edge.<node>.authorize`.
- Estop clear hardened: two distinct humans via `aspen.safety.authorize_clear`
  before `clear` can unlatch; the stop-causer is refused (`self_approval`);
  a bare clear message can never unlatch.
- All gate events flow through the existing hash-chained `AuditLog`.

## Learnings

1. **Fail-safe defaults beat validation.** `ProposeAct.risk_class` defaults to
   `safety_adjacent`; unknown/missing classes normalize to safety_adjacent
   (`DualHumanGate.normalize_risk`). Existing callers got stricter, never
   looser — this is why the change could land without touching every call site.
2. **Extract before wiring.** Promoting the sim class into an importable
   library first meant the RRM wiring, the pytest suite, and the aspen-os
   proof harness all exercise one implementation instead of three copies.
3. **Namespaced audit events keep layers separable.** Gate emits `gate.*`
   records; RRM emits API-level `propose_act` / `act` records. The held
   proposal is visible at both layers without double-counting either.
4. **Behavior changes surface in smoke scripts.** G7-era smoke checks
   (`accepted_sim` after every tick, bare-clear unlatch) encoded the old,
   unsafe semantics. Updating them to assert hold/refuse/dual-clear turned the
   fleet smoke into a regression suite for the gate.
5. **Identity source is the open architectural question.** `operator_of_record`
   is currently set by the node constructor; production must bind it from an
   authenticated identity source (Matrix id / Sentinel session). Flagged to
   Aspen Architect; contract documented in
   [`docs/security/ACT_GATE_CONTRACT.md`](../security/ACT_GATE_CONTRACT.md).

## Verification

- `python3 scripts/sim_dual_human_gate.py` → exit 0 (5 refuse cases + happy path)
- `python3 scripts/sim_act_gate_wire.py` → exit 0, verify_audit ok (31 chained events)
- `pytest tests/` in aspen-edge-rrm → 17 passed
- `scripts/smoke-fleet-bus.py` → 23 PASS / 0 FAIL under new semantics
- G7 regression (`sim_estop_range_cell.py`) still green; cell profile stays
  `status: sim_only`, isolation ACL untouched.

## Refs

- Plan: [`docs/plans/ASP-364-dual-human-wire.md`](../plans/ASP-364-dual-human-wire.md)
- Contract: [`docs/security/ACT_GATE_CONTRACT.md`](../security/ACT_GATE_CONTRACT.md)
- Branches: `hermes/asp-364-dual-human-wire` in aspen-os and aspen-edge-rrm
