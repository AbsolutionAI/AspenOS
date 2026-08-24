# BEL-192 / ASP-381 — Phase D first physical cell gate

**Status:** Software residual **CLOSED** — G1/G3/G4/G5/G6/G7 green (sim/docs); physical D1 exit still open  
**Linear:** [BEL-192](https://linear.app/bellahtech/issue/BEL-192/d1-first-physical-cell-gate-range-plant-only)  
**Paperclip:** ASP-381 (child of ASP-50 / BEL-179)  
**Owner:** Captain (josiah) — motion-day / spend supersede · aspen — architecture · robotics — live bring-up  
**Updated:** 2026-08-24 (children completed closeout — G6/G7 done + G4 spend lock)

## Intent

Single physical cell on **plant-range only**, with skill-based hold-to-enable and dual human authorization before any real motion. No production plant, no alpha, no unattended motion.

## Hard rules (Master Spec + ADR-0002)

- Agents emit **`propose_act` only** on safety-adjacent subjects until dual human auth clears **`act`**.
- Micro-agents never write actuators; swarm never streams setpoints; Hermes never issues joints.
- `ASPEN_SIM=1` is **forbidden** on real cells.
- Spend locked **$0 / compute_net_only** until captain supersedes (see G4 detail).
- Do not assign joint motion until live dual-auth usable + captain motion-day authorization.

## Gate checklist

| # | Gate | Owner | Tracker | State (2026-08-24 closeout) |
|---|------|-------|---------|------------------------------|
| G1 | Sim E2E residual: live NATS fleet bus + robotics agent contracts (sim) | robotics + aspen | ASP-380 | **GREEN** — `done` |
| G2 | Package smokes stay green | robotics | package `make smoke` | **Partial/GREEN** — freeze hold unless regression |
| G3 | Dual-human `propose_act` → `act` (sim/dry-run) | aspen | ASP-384 · `scripts/sim_dual_human_gate.py` | **GREEN** — exit 0 (4 refuse + happy) |
| G4 | Fiscal un-defer + spend detail | captain (josiah) | interactions `g4-fiscal-undefer-v1` + `g4-spend-detail-v1` | **GREEN (locked)** — formal accept + **scope=`compute_net_only` · ceiling=`$0`** |
| G5 | Architecture go/no-go | aspen | `docs/plans/BEL-192-g5-architecture-go.md` | **CONDITIONAL GO** — prep complete |
| G6 | Cell profile: plant-range, isolation, hold-to-enable | robotics | ASP-416 · `config/cells/plant-range-d1.yaml` · `scripts/sim_plant_range_cell_profile.py` | **GREEN** — ASP-416 `done` |
| G7 | Estop latch + audit chain (sim) | robotics + auditor | ASP-417 · `scripts/sim_estop_range_cell.py` | **GREEN** — ASP-417 `done` |

## Agent-closeable vs human-only

| Class | Items | Status |
|-------|--------|--------|
| Agent-closeable sim gates | G1, G3, G6, G7 (+ G2 held) | **Closed** |
| Human formal un-defer | G4 confirmation accept | **Closed** |
| Human spend detail | G4 scope + $ ceiling | **Closed — $0 / compute_net_only** |
| Architecture | G5 | **CONDITIONAL GO recorded** |
| Physical bring-up / D1 exit | Live test card + motion-day | **Open — new child; not agent-auto** |

## Proofs (re-run this closeout)

```bash
python3 scripts/sim_dual_human_gate.py
# {"proof":"dual_human_gate","result":"pass","refuse_cases":4,"happy_path":true}

python3 scripts/sim_plant_range_cell_profile.py
# {"proof":"plant_range_cell_profile","result":"pass",...}

python3 scripts/sim_estop_range_cell.py
# {"proof":"estop_range_cell","result":"pass",...,"verify_audit":"pass"}
```

## Allowed now

- Docs, cell profile YAML, plant ACL reviews, BOM shortlist (no buy).
- Live Hermes dual-auth wiring (H-016 / ASP-364) — software only.
- Inventory existing compute/network on range under $0 lock (no PO).
- Captain motion-day authorization when ready for first live test card (still no arm PO under current lock).

## Still forbidden

- Joint motion / `ASPEN_SIM=0` with live drivers attached without motion-day go + dual-auth.
- Hardware PO (ceiling **$0**).
- Arm purchase / conveyor / production jig without new G5 + spend supersede.
- Cross-plant schedule from range → edge/alpha.
- Auto-arm with operator string `sim` on the physical cell.

## Unblock sequence (physical D1 only)

1. ~~Software gates G1/G3/G6/G7.~~
2. ~~Captain G4 accept + spend lock.~~
3. ~~aspen G5 conditional go.~~
4. **aspen/runtime:** prefer ASP-364 (H-016) live dual-auth wire before first live act.
5. **Captain:** motion-day go (or supersede spend if arm/PO needed).
6. **robotics:** live test card on named plant-range node (profile, estop hardware, dual-auth, enable window).
7. Phase D D1 exit criteria (below).

## Dual-human gate (G3) summary

Full flow: `docs/plans/BEL-192-g3-dual-human-auth-gate.md`.  
Live runtime wiring: H-016 / ASP-364 (backlog). **First physical `act` must not precede a usable dual-auth path.**

## Exit criteria (Phase D D1 physical)

- [ ] Range plant cell online under RRM with **live** estop drill pass
- [ ] Mission arm requires human operator string ≠ `sim`
- [ ] Dual auth recorded before first `act` (audit hash chain verifies) — **live path**
- [ ] No cross-plant schedule from range → edge/alpha
- [x] Captain scope + $ ceiling recorded (`compute_net_only` / `$0`)
- [ ] BEL-192 physical exit marked done with evidence links

Software residual (ASP-381 prep scope) may close with G1–G7 green + G5 record; physical exit tracks a follow-up issue.

## References

- G5 decision: `docs/plans/BEL-192-g5-architecture-go.md`
- G3 detail: `docs/plans/BEL-192-g3-dual-human-auth-gate.md`
- G7: `docs/plans/ASP-417-estop-range-cell.md`
- Cell profile: `config/cells/plant-range-d1.yaml` · `docs/robotics/plant-range-cell-profile.yaml`
- Runbooks: `docs/runbooks/plant-range-d1-hold-to-enable.md` · `docs/runbooks/plant-range-estop-audit-drill.md`
- Master Spec safety / ADR layering: skill `aspen-fleet-edge`
- FLEET ACL: `docs/FLEET.md` (`plant-range: []`)
- Paperclip: ASP-381 · ASP-380/384/416/417 (done) · ASP-364 (H-016 open)
