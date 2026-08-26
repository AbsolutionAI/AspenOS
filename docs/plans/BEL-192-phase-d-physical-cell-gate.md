# BEL-192 / ASP-381 — Phase D first physical cell gate

**Status:** G5 CONDITIONAL GO — architecture approved; physical motion still gated  
**Linear:** [BEL-192](https://linear.app/bellahtech/issue/BEL-192/d1-first-physical-cell-gate-range-plant-only)  
**Paperclip:** ASP-381 (child of ASP-50 / BEL-179)  
**Owner:** Captain (josiah) — spend scope/$ ceiling · aspen — architecture · robotics — G6/G7  
**Updated:** 2026-08-24 (G5 conditional go + G6/G7 prep seeds)

## Intent

Single physical cell on **plant-range only**, with skill-based hold-to-enable and dual human authorization before any real motion. No production plant, no alpha, no unattended motion.

## Hard rules (Master Spec + ADR-0002)

- Agents emit **`propose_act` only** on safety-adjacent subjects until dual human auth clears **`act`**.
- Micro-agents never write actuators; swarm never streams setpoints; Hermes never issues joints.
- `ASPEN_SIM=1` is **forbidden** on real cells.
- No hardware PO / cash outlay without captain **scope + $ ceiling** comment (see G4 note).
- Do not assign joint motion until G6–G7 green and dual-auth path available for the cell.

## Gate checklist (all green required for Phase D D1 exit)

| # | Gate | Owner | Tracker | State (2026-08-24) |
|---|------|-------|---------|---------------------|
| G1 | Sim E2E residual: live NATS fleet bus + robotics agent contracts (sim) | robotics + aspen | ASP-380 · BEL-179 residual | **GREEN** — ASP-380 `done` |
| G2 | Package smokes stay green (`aspen-swarm-manager`, `aspen-edge-rrm`, optional langgraph-worker) | robotics | package `make smoke` | **Partial/GREEN** — held under freeze unless regression reported |
| G3 | Dual-human `propose_act` → `act` path verified (sim/dry-run; refuse single-actor self-approve) | aspen | ASP-384 · detail `docs/plans/BEL-192-g3-dual-human-auth-gate.md` | **GREEN** — `scripts/sim_dual_human_gate.py` exit 0 (4 refuse + happy path) |
| G4 | Fiscal un-defer — explicit captain approval for cell hardware/spend | captain (josiah) | Human only | **GREEN (formal)** — Paperclip confirmation `confirmation:…:g4-fiscal-undefer-v1` **accepted** 2026-08-24 by captain user; **scope + $ ceiling still required in comment before PO** |
| G5 | Architecture go/no-go after G1–G4 | aspen | `docs/plans/BEL-192-g5-architecture-go.md` + ASP-381/BEL-192 | **CONDITIONAL GO** — see G5 record |
| G6 | Cell profile: `plant-range` only, isolation true, human arm ≠ `sim`, hold-to-enable skill | robotics | **ASP-416** · `config/cells/plant-range-d1.yaml` · `docs/runbooks/plant-range-d1-hold-to-enable.md` · `scripts/sim_plant_range_cell_profile.py` | **IN PROGRESS** — architecture seeds landed; robotics owns lock + sim verify |
| G7 | Estop latch + audit chain proven on the cell node | robotics + auditor | **ASP-417** · `docs/runbooks/plant-range-estop-audit-drill.md` | **OPEN** — drill runbook seeded; no live drivers until G6 profile locked |

## Agent-closeable vs human-only

| Class | Items | Status |
|-------|--------|--------|
| Agent-closeable sim gates | G1, G3 (+ G2 held) | **Closed** |
| Human formal un-defer | G4 confirmation accept | **Closed (accept)** |
| Human spend detail | G4 scope + $ ceiling comment | **Open — josiah before PO** |
| Architecture | G5 | **CONDITIONAL GO recorded** |
| Physical bring-up | G6–G7 + Phase D D1 exit | Open — no joints until both green + dual-auth usable |

## Allowed now (post G5 conditional go)

- Docs, cell profile YAML drafts, plant ACL reviews, BOM shortlist (no buy).
- G6/G7 software config + sim drills.
- Live Hermes dual-auth wiring (H-016 / ASP-364) — software only; **prefer before first real act**.
- Captain comment: hardware scope + hard $ ceiling (unblocks PO path only).

## Still forbidden

- Joint motion / `ASPEN_SIM=0` with live drivers attached.
- Hardware PO until captain scope + $ ceiling is on ASP-381 or BEL-192.
- Cross-plant schedule from range → edge/alpha.
- Auto-arm with operator string `sim` on the physical cell.

## Unblock sequence (remaining)

1. ~~ASP-380 → done.~~
2. ~~ASP-384 → dual-auth sim proof.~~
3. ~~Captain G4 confirmation accept.~~
4. ~~aspen G5 architecture conditional go (this revision).~~
5. **Captain:** post scope + $ ceiling (required before PO).
6. **robotics:** G6 lock via ASP-416 (profile sim proof exit 0) + G7 estop/audit drill ASP-417 (sim first; live only after ceiling + dual-auth path).
7. **aspen/runtime:** prefer ASP-364 (H-016) live dual-auth wire before first live act.
8. Phase D D1 exit criteria (below).

## Dual-human gate (G3) summary

Full flow, refuse matrix, audit schema: `docs/plans/BEL-192-g3-dual-human-auth-gate.md`.

```bash
python3 scripts/sim_dual_human_gate.py
# expect: {"proof":"dual_human_gate","result":"pass","refuse_cases":4,"happy_path":true} and exit 0
```

Refuse cases proven: `insufficient_principals`, `duplicate_principal`, `self_approval`, `expired`.

Live runtime wiring: H-016 / ASP-364 (backlog). **First physical `act` must not precede a usable dual-auth path** (sim proof alone is insufficient on live hardware).

## Exit criteria (Phase D D1)

- [ ] Range plant cell online under RRM with estop drill pass
- [ ] Mission arm requires human operator string ≠ `sim`
- [ ] Dual auth recorded before first `act` (audit hash chain verifies)
- [ ] No cross-plant schedule from range → edge/alpha
- [ ] Captain scope + $ ceiling recorded; any spend within ceiling
- [ ] BEL-192 + ASP-381 marked done with evidence links

## References

- G5 decision: `docs/plans/BEL-192-g5-architecture-go.md`
- G3 detail: `docs/plans/BEL-192-g3-dual-human-auth-gate.md`
- Master Spec safety / ADR layering: skill `aspen-fleet-edge`
- FLEET ACL: `docs/FLEET.md` (`plant-range: []`)
- Paperclip: ASP-381 · ASP-380 (done) · ASP-384 (done) · ASP-364 (H-016 open)

## Disposition

**IN PROGRESS** (ASP-482 sweep — 2026-08-26) — Phase D physical cell gate is a live tracking document, not a completed work item. G3 (spec+refuse proofs), G5 (architecture conditional go), G6 (cell profile), G7 (estop latch), G8 (dual-human wire) have landed. Remaining trackers: G9 captain scope/$ ceiling, physical motion gate, production plant (all intentionally unchecked). Left as-is.
