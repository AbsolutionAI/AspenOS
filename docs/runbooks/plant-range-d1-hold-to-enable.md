# Runbook — plant-range-d1 hold-to-enable (G6)

**Trackers:** ASP-416 · ASP-381 · BEL-192  
**Profile:** `config/cells/plant-range-d1.yaml`  
**Gate doc:** `docs/plans/BEL-192-g5-architecture-go.md` (test card §1–3, §5–7)

## Intent

Operate a **single isolated range cell** with skill-based hold-to-enable. No free motion until dual-human authorize clears a bounded enable window.

## Preconditions

- [ ] Profile file present and `cell.plant: plant-range`, `isolation: true`
- [ ] `config/fleet.yaml` ACL: `plant-range: []`
- [ ] Node override points at plant-range (not alpha/edge)
- [ ] `ASPEN_SIM` unset/0 on real cell; sim drills use explicit lab host only
- [ ] Dual-human sim proof green: `python3 scripts/sim_dual_human_gate.py`
- [ ] Captain scope + $ ceiling on record before any PO (not required for sim)

## Arm procedure (software)

1. Mission enters `planned`.
2. Operator string must be a **named human** (≠ `sim`, non-empty).
3. Hold-to-enable skill remains latched until dual auth (G3/H-016) enables act.
4. On physical profile: `auto_arm: false` — refuse any auto-arm path.

## Propose → act (safety-adjacent)

```
agent --propose_act--> HOLD
  human A authorize  --> 1/2
  human B authorize  --> enable window (default 600s)
  runtime verify 2 principals --> act OR refuse
```

Refuse matrix (must still fail):

| Case | Reason |
|------|--------|
| One approver | `insufficient_principals` |
| Same human twice | `duplicate_principal` |
| Approver == proposer operator | `self_approval` |
| Past enable/proposal expiry | `expired` |

## Forbidden paths (fail closed)

- Hermes/Paperclip issuing joint streams
- Micro-agent actuator writes
- Swarm streaming setpoints around the gate
- Scheduling missions from range → edge/alpha
- `ASPEN_SIM=1` with live drivers attached
- Arm with operator `sim` on physical profile

## Verification (sim-first)

```bash
# Profile + ACL contract (stdlib)
python3 scripts/sim_plant_range_cell_profile.py

# Dual-human refuse + happy path
python3 scripts/sim_dual_human_gate.py

# Fleet bus residual (optional, ASPEN_SIM=1 lab only)
ASPEN_SIM=1 python3 scripts/smoke-fleet-bus.py
```

Expect profile script exit 0 and dual-human JSON proof `result=pass`.

## Hand-off to G7

After G6 profile lock: run `docs/runbooks/plant-range-estop-audit-drill.md` (ASP-417).  
**No free motion** until G6+G7 green **and** dual-auth usable on path (ASP-364/H-016).
