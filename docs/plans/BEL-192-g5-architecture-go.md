# BEL-192 G5 — Architecture go/no-go (Phase D first physical cell)

**Issue:** ASP-381 · Linear [BEL-192](https://linear.app/bellahtech/issue/BEL-192/d1-first-physical-cell-gate-range-plant-only)  
**Decision date:** 2026-08-24  
**Decider:** aspen (Aspen Architect)  
**Verdict:** **CONDITIONAL GO**

## Preconditions checked

| Precondition | Evidence | Result |
|--------------|----------|--------|
| G1 sim fleet residual | ASP-380 `done` | Pass |
| G3 dual-human sim | `python3 scripts/sim_dual_human_gate.py` → exit 0; refuse×4 + happy path | Pass (re-run this heartbeat) |
| G4 fiscal un-defer | Paperclip interaction `confirmation:b0a50021-…:g4-fiscal-undefer-v1` **accepted** by captain user `4O0IhoLMkiTSps3VsM8DXal0rjmNk5vc` at 2026-08-24T03:12:20Z | Pass (formal) |
| G4 spend detail | Explicit **scope + $ ceiling** comment on ASP-381 / BEL-192 | **Fail / open** — accept without dollar comment |

## Verdict rationale

Architecture for a **single plant-range cell** is coherent with Master Spec, ADR-0002 layering, and plant ACL (`plant-range` isolation; no schedule-out). Sim safety gates are green. Captain formally accepted G4 un-defer.

**Conditional** because:

1. No hard **$ ceiling** or BOM scope is on the record yet — PO path stays closed.
2. Live dual-human path (H-016 / ASP-364) is still **backlog**; first live `act` is forbidden until a usable dual-auth path exists on the cell path (sim proof is not enough for hardware).
3. G6 cell profile and G7 estop/audit are not yet proven on a named node.

This is **not** a no-go on architecture. It is a go to **prepare** the range cell (config, runbooks, sim drills, BOM shortlist) without motion or spend.

## Cell BOM constraints (architecture lock)

| Constraint | Rule |
|------------|------|
| Plant | **`plant-range` only** — never plant-alpha / plant-edge for D1 |
| Isolation | `isolation: true`; ACL allow-list **empty outbound** (`plant-range: []`) |
| Arms / motion | Hold-to-enable skill; human operator string **≠ `sim`**; no auto-arm in non-sim |
| Act path | `propose_act` only until **two distinct human principals** authorize; refuse self-approve / duplicate / expired |
| Runtime layers | Paperclip/Hermes = C2 only; swarm = mission DAG; edge-rrm = lifecycle/estop; **no** micro-agent actuator writes |
| Sim flag | Real cell: **`ASPEN_SIM` unset/0**; never run production drivers under `ASPEN_SIM=1` |
| Network | Prefer isolated lab VLAN / Tailscale ACL; no default route into alpha plant bus |
| Audit | JSONL + hash chain on cell node (`verify_audit()` must pass after estop drill) |
| Spend | No PO until captain posts **scope + hard $ ceiling**; stay under ceiling; single cell only |
| Deferred SKUs | No second arm, no conveyor, no production jig in D1 BOM without new G5 |

### Suggested D1 BOM classes (shortlist only — not a PO)

- One educational / collaborative arm **or** existing range fixture (captain chooses within ceiling)
- E-stop (hardware latch) + clearly labeled clear path
- Cell compute (existing edge node OK if isolated) running edge-rrm
- Network: isolated switch or VLAN; NATS credentials plant-range scoped
- Optional: cheap force/torque or joint-current monitoring if ceiling allows

## Test card (must pass before first free motion)

1. **Profile lock** — node advertises `plant=plant-range`, `isolation=true`; cross-plant mission to edge/alpha **refused**.
2. **Sim dry-run** — dual-human gate script still exit 0 on cell host tooling path.
3. **Arm gate** — mission arm with operator `sim` **fails** on physical profile; named human operator required.
4. **Estop** — press estop → latch; all propose_act held/refused; clear requires authorized procedure; audit chain verifies.
5. **Dual auth** — two distinct humans authorize a no-op or free-space slow move proposal; single principal **refused**; self-approve **refused**.
6. **Enable window** — expire window → act refused; new propose required.
7. **No setpoint stream** — swarm/Hermes cannot stream joints; only gated act path.
8. **Spend** — if hardware purchased, receipt ≤ ceiling and linked on BEL-192.

## Explicit non-goals (G5)

- Multi-cell fleet on physical hardware
- plant-alpha production cutover
- Unattended dark-factory shift
- Replacing Paperclip with LangGraph org control
- Closing H-016 as “done” without live wire proof

## Follow-on work

| ID | Work | Owner | Notes |
|----|------|-------|-------|
| G6 ASP-416 | Cell profile + hold-to-enable | robotics | Seeds: `config/cells/plant-range-d1.yaml`, runbook, `scripts/sim_plant_range_cell_profile.py` |
| G7 ASP-417 | Estop latch + audit verify | robotics + auditor | Seed: `docs/runbooks/plant-range-estop-audit-drill.md` — sim drill OK before live |
| ASP-364 | H-016 live dual-human wire | aspen / runtime | Prefer before first live act |
| Captain | Scope + $ ceiling comment | josiah | Unblocks PO only |

## Sign-off

**G5 CONDITIONAL GO** — architecture approved for plant-range D1 **preparation**.  
**Physical motion:** NO until G6+G7 green **and** dual-auth usable on path.  
**Spend:** NO until captain scope + $ ceiling on record.

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — G5 architecture conditional go approved. Architecture approved for plant-range D1 preparation. Gate dependencies (G6 ASP-416, G7 ASP-417, H-016 ASP-364) tracked separately. Physical motion and spend remain gated.
