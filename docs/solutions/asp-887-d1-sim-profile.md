# D1 plant-range cell sim-only profile (landed via ASP-887)

## What

Forward-ported the plant-range D1 profile (originally drafted in ASP-416/ASP-381,
PR #29) as a simulation-only profile. The physical D1 bring-up (ASP-418) stays
parked.

## Files

- `config/cells/plant-range-d1.sim.yaml` — SIM ONLY profile with hard constraints
  (no hardware I/O, no motion, no install path, no OT network changes).
- `tests/test_plant_range_d1_sim_profile.py` — 10 hermetic tests pinned to the
  sim-only invariants.
- `docs/plans/ASP-796-d1-sim-only.md` — Plan from the original issue.

## Key decisions

| Decision | Rationale |
|----------|-----------|
| `sim_only: true` + `aspen_sim: true` | Never installed on a physical cell. |
| `motion_allowed: false` | No joints, setpoints, MOTION_DAY or actuator writes. |
| `result_on_approve: executed_sim` | Sim path only; never "executed" (live). |
| Node roles `[ops]` only | Master's `plant-range.roles_allowed` has no robotics/plant-controller role yet. |

## Verification

```
python3 -m pytest tests/test_plant_range_d1_sim_profile.py -q  # 10 passed
python3 -m pytest tests/ --ignore=tests/test_memory_mcp.py -q   # 526 passed
```

## What this unblocks

1. Sim proofs from PR #29: re-cut `scripts/sim_plant_range_cell_profile.py`
   and `scripts/sim_estop_range_cell.py` against this profile.
2. Dual-human act path in sim: extend `scripts/smoke-fleet-bus.py` with
   H-016 `held_dual_auth` assertions driven by this profile's `act.refuse` list.
3. Hold-to-enable skill in sim: port `agents/skills/hold-to-enable/SKILL.md`
   with operator gate exercised in sim only.