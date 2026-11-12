# ASP-796: D1 plant-range cell, sim_only software path

**Parent:** ASP-418 (Phase D D1 physical bring-up). It stays **parked/blocked**.
**Decision:** owner chose "Software sim_only ticket only" on 2026-09-26 (recorded on
ASP-650, closed 2026-10-17 under CHG-0037).
**Linear:** BEL-192 (D1 first physical cell gate) remains the umbrella. This plan
covers only the software slice.

## Hard constraints

- SIM ONLY. No physical cell and no OT action of any kind.
- No joints or motion, no MOTION_DAY, no `ASPEN_SIM=0`, no hardware I/O (estop GPIO,
  USB-serial, CAN, fieldbus).
- No plant or OT network changes. ASP-435 stays a parked human gate.
- No purchase orders. BT-ASP-SRV is not a plant cell.

## Slice 1 (this PR)

| Deliverable | Notes |
|---|---|
| `config/cells/plant-range-d1.sim.yaml` | Forward-port of the ASP-416/ASP-381 draft (PR #29 `config/cells/plant-range-d1.yaml`) with `sim_only: true`, `aspen_sim: true`, `motion_allowed: false`, no install path, no hardware blocks, `result_on_approve: executed_sim`. Node roles reduced to `[ops]`, because master's `plant-range.roles_allowed` has no `robotics`/`plant-controller` role (those land with the robotics agent in PR #29). |
| `tests/test_plant_range_d1_sim_profile.py` | 10 hermetic tests. They pin the sim-only invariants, reject hardware/install keys, check the arm/act gates and forbidden list, check the ACL against `config/fleet.yaml`, and prove that `fleet_policy.check_cross_plant` refuses range → alpha/edge and inbound to the isolated range. |
| This plan | — |

The profile is **not** shipped by `build-deb.sh` or `install-daemon.sh`, which copy only
`fleet.yaml`, `profiles.yaml`, `models-digests.yaml` and `policy.default.json`.

## Later slices (software only, each its own PR)

1. **Sim proofs from PR #29**: re-cut `scripts/sim_plant_range_cell_profile.py` and
   `scripts/sim_estop_range_cell.py` against the sim profile. Replace the raw-string
   checks with YAML parsing, and remove `/home/tech` paths (ASP-733).
2. **Dual-human act path in sim**: extend `scripts/smoke-fleet-bus.py` with the H-016
   `held_dual_auth` → two distinct humans → `executed_sim` assertion (the piece of
   PR #36 not yet on master), driven by this profile's `act.refuse` list.
3. **Hold-to-enable skill in sim**: port `agents/skills/hold-to-enable/SKILL.md` from
   PR #29 with the operator gate exercised by the sim only.
4. **Robotics role (optional)**: if the owner wants it, add `robotics` to
   `plant-range.roles_allowed` in a separate reviewed fleet-policy PR. It's a policy
   change, so it doesn't belong in a sim slice.

## Out of scope (needs the owner, stays parked)

- ASP-418 physical bring-up, naming a real cell host, any hardware PO.
- ASP-435 live OT/cell network segmentation.
- Any `motion_allowed: true` or physical profile install.

## Verification

```
python -m pytest tests/test_plant_range_d1_sim_profile.py -q
python -m pytest tests/test_fleet_policy.py -q
```
