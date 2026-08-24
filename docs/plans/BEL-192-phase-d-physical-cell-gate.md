# BEL-192 / ASP-381 — Phase D first physical cell gate

**Status:** BLOCKED (standing order — sim gates green; cash/hardware red)  
**Linear:** [BEL-192](https://linear.app/bellahtech/issue/BEL-192/d1-first-physical-cell-gate-range-plant-only)  
**Paperclip:** ASP-381 (child of ASP-50 / BEL-179)  
**Owner:** Captain (josiah) — cash/hardware un-defer · aspen — architecture go/no-go after G4  
**Updated:** 2026-08-24

## Intent

Single physical cell on **plant-range only**, with skill-based hold-to-enable and dual human authorization before any real motion. No production plant, no alpha, no unattended motion.

## Hard rules (Master Spec + ADR-0002)

- Agents emit **`propose_act` only** on safety-adjacent subjects until dual human auth clears **`act`**.
- Micro-agents never write actuators; swarm never streams setpoints; Hermes never issues joints.
- `ASPEN_SIM=1` is **forbidden** on real cells.
- Fiscal freeze: **no hardware spend** without captain un-defer.
- Do not assign physical motion work while any gate below is red.

## Gate checklist (all green required)

| # | Gate | Owner | Tracker | State (2026-08-24) |
|---|------|-------|---------|---------------------|
| G1 | Sim E2E residual: live NATS fleet bus + robotics agent contracts (sim) | robotics + aspen | ASP-380 · BEL-179 residual | **GREEN** — ASP-380 `done` (fleet bus smoke + robotics contracts; ASPEN_SIM=1) |
| G2 | Package smokes stay green (`aspen-swarm-manager`, `aspen-edge-rrm`, optional langgraph-worker) | robotics | package `make smoke` | **Partial/GREEN** — prior in-process smokes green; treat as held green under freeze unless regression reported |
| G3 | Dual-human `propose_act` → `act` path verified (sim/dry-run; refuse single-actor self-approve) | aspen | ASP-384 · detail `docs/plans/BEL-192-g3-dual-human-auth-gate.md` | **GREEN** — ASP-384 `done`; `scripts/sim_dual_human_gate.py` exit 0 (4 refuse + happy path) |
| G4 | Fiscal un-defer — explicit captain approval for cell hardware/spend | captain (josiah) | Human only (not agent-spendable) | **RED** — freeze active |
| G5 | Architecture go/no-go after G1–G4 | aspen | Comment on ASP-381 + BEL-192 | **HOLD** — waiting G4 |
| G6 | Cell profile: `plant-range` only, isolation true, human arm ≠ `sim`, hold-to-enable skill | robotics | Cell config + runbook | Not started (blocked on G4–G5) |
| G7 | Estop latch + audit chain proven on the cell node | robotics + auditor | RRM audit JSONL verify | Not started (blocked on G4–G5) |

## Agent-closeable vs human-only

| Class | Items | Status |
|-------|--------|--------|
| Agent-closeable sim gates | G1, G3 (+ G2 held) | **Closed** |
| Human-only | G4 cash/hardware un-defer | **Open — unblock owner: josiah** |
| Post-cash architecture | G5 aspen go/no-go | Queued after G4 |
| Physical bring-up | G6–G7 + Phase D D1 exit | Forbidden until G5 go |

## Allowed work while blocked

- Docs, ADRs, runbooks, plant ACL reviews (no spend).
- Live Hermes dual-auth wiring tracked separately (H-016 / ASP-364) — software only.
- **Forbidden:** PO/hardware, joint motion, `ASPEN_SIM=0` on any node with drivers attached, assigning motion tickets under freeze.

## Unblock sequence (remaining)

1. ~~ASP-380 → done with live-bus evidence (sim).~~ **Done**
2. ~~ASP-384 → dual-auth path demo (two distinct principals; refuse self-approve).~~ **Done**
3. **Captain** comment on BEL-192 / ASP-381: cash/hardware un-defer (quote scope + $ ceiling).
4. **aspen** architecture go: G1–G4 green → G5 comment with cell BOM constraints and test card.
5. Only then: range cell bring-up tickets (config, hold-to-enable, estop drill, first skill under hold).

## Dual-human gate (G3) summary

Full flow, refuse matrix, audit schema: `docs/plans/BEL-192-g3-dual-human-auth-gate.md`.

Proof:

```bash
python3 scripts/sim_dual_human_gate.py
# expect: {"proof":"dual_human_gate","result":"pass","refuse_cases":4,"happy_path":true} and exit 0
```

Refuse cases proven: `insufficient_principals`, `duplicate_principal`, `self_approval`, `expired`.

Live runtime wiring into Hermes propose_act→act remains H-016 (ASP-364); Phase D D1 still requires G4–G7 before physical motion.

## Exit criteria (Phase D D1)

- [ ] Range plant cell online under RRM with estop drill pass
- [ ] Mission arm requires human operator string ≠ `sim`
- [ ] Dual auth recorded before first `act` (audit hash chain verifies)
- [ ] No cross-plant schedule from range → edge/alpha
- [ ] BEL-192 + ASP-381 marked done with evidence links

## References

- Master Spec safety: `docs/sor/MASTER_SPEC.md` (or ASPENGROVE v4.0 path if present)
- ADR-0002 / ADR-0003: swarm/RRM boundaries + subjects
- G3 detail: `docs/plans/BEL-192-g3-dual-human-auth-gate.md`
- Matrix authz room: `docs/ops/MATRIX_TAILSCALE_HERMES_INSTALL.md` §9 (if present)
- Skill: `aspen-fleet-edge`
- Paperclip: ASP-381 · ASP-380 (done) · ASP-384 (done)
