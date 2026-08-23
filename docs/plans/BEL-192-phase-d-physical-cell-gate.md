# BEL-192 / ASP-381 — Phase D first physical cell gate

**Status:** BLOCKED (standing order)  
**Linear:** [BEL-192](https://linear.app/bellahtech/issue/BEL-192/d1-first-physical-cell-gate-range-plant-only) (Backlog)  
**Paperclip:** ASP-381 (child of ASP-50 / BEL-179)  
**Owner:** Captain (josiah) — cash/hardware un-defer · aspen — architecture go/no-go  
**Date:** 2026-08-23

## Intent

Single physical cell on **plant-range only**, with skill-based hold-to-enable and dual human authorization before any real motion. No production plant, no alpha, no unattended motion.

## Hard rules (Master Spec + ADR-0002)

- Agents emit **`propose_act` only** on safety-adjacent subjects until dual human auth clears **`act`**.
- Micro-agents never write actuators; swarm never streams setpoints; Hermes never issues joints.
- `ASPEN_SIM=1` is **forbidden** on real cells.
- Fiscal freeze: **no hardware spend** without captain un-defer.
- Do not assign physical motion work while any gate below is red.

## Gate checklist (all green required)

| # | Gate | Owner | Tracker | State (2026-08-23) |
|---|------|-------|---------|---------------------|
| G1 | Sim E2E residual: live NATS fleet bus + robotics agent contracts (sim) | robotics + aspen | ASP-380 · BEL-179 residual | **RED** — ASP-380 open (robotics) |
| G2 | Package smokes stay green (`aspen-swarm-manager`, `aspen-edge-rrm`, optional langgraph-worker) | robotics | package `make smoke` | Partial — in-process smoke previously green; live bus residual open |
| G3 | Dual-human `propose_act` → `act` path verified (sim or dry-run; Matrix `#aspen-authz` or equivalent two-person hold-to-enable) | aspen + captain | ASP-384 (child) · Matrix ops backlog | **RED** — room named; not wired/proven |
| G4 | Fiscal un-defer — explicit captain approval for cell hardware/spend | captain (josiah) | Human only (not agent-spendable) | **RED** — freeze active |
| G5 | Architecture go/no-go after G1–G3 | aspen | Comment on ASP-381 + BEL-192 | Not started |
| G6 | Cell profile: `plant-range` only, isolation true, human arm ≠ `sim`, hold-to-enable skill | robotics | Cell config + runbook | Not started |
| G7 | Estop latch + audit chain proven on the cell node | robotics + auditor | RRM audit JSONL verify | Not started |

## Allowed work while blocked

- Sim-only residual on **ASP-380** (NATS lab, contracts, Flash drips).
- Dual-auth **software** design/tests under **ASP-384** (no actuators, no purchase).
- Docs, ADRs, runbooks, plant ACL reviews.
- **Forbidden:** PO/hardware, joint motion, `ASPEN_SIM=0` on any node with drivers attached, assigning motion tickets under freeze.

## Unblock sequence

1. ASP-380 → `done` with live-bus evidence (sim).
2. ASP-384 → dual-auth path demo (two distinct humans or two distinct auth principals; reject single-actor self-approve).
3. Captain comment on BEL-192 / ASP-381: cash/hardware un-defer (quote scope + $ ceiling).
4. aspen architecture go: G1–G4 green → G5 comment with cell BOM constraints and test card.
5. Only then: range cell bring-up tickets (config, hold-to-enable, estop drill, first skill under hold).

## Exit criteria (Phase D D1)

- [ ] Range plant cell online under RRM with estop drill pass
- [ ] Mission arm requires human operator string ≠ `sim`
- [ ] Dual auth recorded before first `act` (audit hash chain verifies)
- [ ] No cross-plant schedule from range → edge/alpha
- [ ] BEL-192 + ASP-381 marked done with evidence links

## References

- Master Spec safety: `docs/sor/ASPENGROVE_MASTER_SPEC_v4.0.md`
- ADR-0002 / ADR-0003: swarm/RRM boundaries + subjects
- Matrix authz room: `docs/ops/MATRIX_TAILSCALE_HERMES_INSTALL.md` §9
- Skill: `aspen-fleet-edge`
