# BEL-192 G5 — Architecture go/no-go (Phase D first physical cell)

**Issue:** ASP-381 · Linear [BEL-192](https://linear.app/bellahtech/issue/BEL-192/d1-first-physical-cell-gate-range-plant-only)  
**Decision date:** 2026-08-24  
**Decider:** aspen (Aspen Architect)  
**Verdict:** **CONDITIONAL GO** (software prep complete; physical motion still NO)

## Preconditions checked

| Precondition | Evidence | Result |
|--------------|----------|--------|
| G1 sim fleet residual | ASP-380 `done` | Pass |
| G3 dual-human sim | `python3 scripts/sim_dual_human_gate.py` → exit 0; refuse×4 + happy path | Pass (re-run 2026-08-24 closeout) |
| G4 fiscal un-defer | Paperclip interaction `confirmation:b0a50021-…:g4-fiscal-undefer-v1` **accepted** by captain user `4O0IhoLMkiTSps3VsM8DXal0rjmNk5vc` at 2026-08-24T03:12:20Z | Pass (formal) |
| G4 spend detail | Interaction `ask:…:g4-spend-detail-v1` **answered** 2026-08-24T03:27:02Z — `hw_scope=compute_net_only`, `usd_ceiling=c0` (**$0 — no PO**) | Pass (locked) |
| G6 plant-range profile | ASP-416 `done` · `scripts/sim_plant_range_cell_profile.py` pass · robotics profile/runbook | Pass (software) |
| G7 estop + audit | ASP-417 `done` · `scripts/sim_estop_range_cell.py` pass · `verify_audit` green | Pass (software/sim) |

## Verdict rationale

Architecture for a **single plant-range cell** is coherent with Master Spec, ADR-0002 layering, and plant ACL (`plant-range` isolation; no schedule-out). Sim safety gates G1/G3/G6/G7 are green. Captain formally accepted G4 un-defer and locked spend.

**Conditional** because:

1. Spend lock is **$0 PO** + **compute/network only** — no arm purchase; no automated PO.
2. Live dual-human path (H-016 / ASP-364) is still **backlog**; first live `act` is forbidden until a usable dual-auth path exists on the cell path (sim proof is not enough for hardware).
3. No physical node has completed the live test card (estop hardware, RRM online, dual-auth on cell host).

This is **not** a no-go on architecture. Software residual for Phase D D1 **prep** is complete. Physical motion remains closed until a fresh captain motion-day authorization (and preferably ASP-364).

## Captain spend lock (G4 detail)

| Field | Value | Source |
|-------|-------|--------|
| Hardware scope | **Cell compute/network only** (no arm purchase this cycle) | `g4-spend-detail-v1` / `compute_net_only` |
| USD ceiling | **$0 — no PO** | `g4-spend-detail-v1` / `c0` |
| PO path | **CLOSED** | Ceiling $0 |
| Motion | **HARD NO** until motion-day gate + dual-auth usable | Master Spec |

To reopen PO or arm SKU: new captain interaction superseding this lock (new ceiling and scope). Do not treat formal G4 accept alone as spend authority beyond this table.

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
| Spend | Locked **$0 / compute_net_only** until captain supersedes |
| Deferred SKUs | No arm buy, no second arm, no conveyor, no production jig in D1 without new G5 + spend lock |

### In-scope under $0 lock

- Existing range fixture / existing compute only (no purchase)
- Software: cell profile, hold-to-enable, estop/audit sims, dual-auth live wire (ASP-364)
- Docs / runbooks / BOM shortlist (not a PO)

### Out of scope until spend lock raised

- Educational/collaborative arm purchase
- New estop hardware purchase if none on hand
- Any invoiceable cell BOM line

## Test card (must pass before first free motion)

1. **Profile lock** — node advertises `plant=plant-range`, `isolation=true`; cross-plant mission to edge/alpha **refused**.
2. **Sim dry-run** — dual-human gate script still exit 0 on cell host tooling path.
3. **Arm gate** — mission arm with operator `sim` **fails** on physical profile; named human operator required.
4. **Estop** — press estop → latch; all propose_act held/refused; clear requires authorized procedure; audit chain verifies.
5. **Dual auth** — two distinct humans authorize a no-op or free-space slow move proposal; single principal **refused**; self-approve **refused**.
6. **Enable window** — expire window → act refused; new propose required.
7. **No setpoint stream** — swarm/Hermes cannot stream joints; only gated act path.
8. **Spend** — if hardware purchased, receipt ≤ ceiling and linked on BEL-192 (currently ceiling **$0** ⇒ no purchase).

## Explicit non-goals (G5)

- Multi-cell fleet on physical hardware
- plant-alpha production cutover
- Unattended dark-factory shift
- Replacing Paperclip with LangGraph org control
- Closing H-016 as “done” without live wire proof
- Treating $0 compute_net_only lock as arm authorization

## Follow-on work

| ID | Work | Owner | Notes |
|----|------|-------|-------|
| ASP-416 | G6 cell profile + hold-to-enable | robotics | **done** (software) |
| ASP-417 | G7 estop latch + audit sim | robotics + auditor | **done** (software) |
| ASP-364 | H-016 live dual-human wire | aspen / runtime | Prefer before first live act |
| Physical D1 child | Bring-up under $0 / existing gear only | captain + robotics | New ticket; motion-day auth required |
| Captain | Supersede spend lock if PO/arm needed | josiah | New interaction |

## Sign-off

**G5 CONDITIONAL GO** — architecture approved; **software residual for Phase D D1 prep is complete**.  
**Physical motion:** NO until live test card + dual-auth usable on path + captain motion-day go.  
**Spend:** locked **$0 / compute_net_only** (interaction `g4-spend-detail-v1`).
