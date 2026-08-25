# Learning: Plant-range D1 cell profile seeds — BEL-192 Phase D physical cell prep

**Tickets:** ASP-381, ASP-416, BEL-192 (Phase D)
**Date:** 2026-08-25
**Status:** Draft — D1 cell is sim/runbook only; no live drivers, no PO ceiling.

## Problem

BEL-192 Phase D requires a physical production cell (plant-range D1) with
safety-isolated robotics. Before any motion or hardware integration, the cell
needs a declarative profile describing its isolation, arm gate, act path,
safety/estop contract, and ACL boundaries — plus runbooks and sim proofs that
verify the contract before live wiring.

## What was done

Seeded the D1 cell artifact stack in one commit (`75417c9`):

1. **Cell profile YAML** (`config/cells/plant-range-d1.yaml`) — Declares
   `isolation: true`, `motion_allowed: false`, dual-human required act path,
   hold-to-enable arm gate, hash-chained estop audit, cross-plant ACL
   (`refuse_schedule_to: [plant-alpha, plant-edge]`), and explicit non-goals
   (`forbidden:` list). Status field: `aspen_sim: false` (stays false in
   production).

2. **Hold-to-enable runbook** (`docs/runbooks/plant-range-d1-hold-to-enable.md`)
   — Step-by-step operator procedure for the simulated hold-to-enable skill
   (`agents/skills/hold-to-enable/SKILL.md`). Covers arm gate check, enable
   window, dual-human authorization, estop drill, and controlled motion.

3. **Estop/audit drill runbook** (`docs/runbooks/plant-range-estop-audit-drill.md`)
   — Scripted drill: press estop, verify latch/refuse, verify dual-human clear
   (both acceptance and single-principal refusal), verify audit chain integrity.

4. **Sim profile contract script** (`scripts/sim_plant_range_cell_profile.py`)
   — Self-contained simulator that exercises the full cell lifecycle: arm gate,
   propose_act→hold→authorize→act, estop→latch→refuse, dual-human clear,
   audit verify. Exit 0 means the contract is sound.

5. **Fleet ACL integration** (`config/fleet.yaml`) — Cross-plant ACL entries for
   `plant-range` cell: outbound allow is empty, schedule-to refuses alpha/edge.

6. **Plant-range robotics role** (`agents/robotics.yaml`) — Robotics agent
   definition with role-scoped NATS subjects, policy allowlist, and hold-to-enable
   skill mount.

## Patterns to reuse

1. **Declarative cell profile before hardware.** The YAML profile acts as a
   single source of truth for safety isolation, act restrictions, and ACL
   boundaries. Every subsequent tool/drill/script reads from the profile's
   semantics; the profile is versioned and gated.

2. **Sim proof before live wiring.** The sim script
   (`sim_plant_range_cell_profile.py`) proves the full lifecycle before any
   physical motion. The `aspen_sim: false` flag in the profile ensures no
   production runner ever runs with sim semantics.

3. **Forbidden list as contract.** Listing explicit non-goals in the profile
   (`forbidden:`) makes architectural boundaries discoverable and reviewable,
   rather than implicit in assumptions.

4. **Cross-plant ACL at two layers.** The cell YAML declares `refuse_schedule_to`
   expectations, and `config/fleet.yaml` materializes them at the fleet bus
   level. Duelling these creates a validation cross-check.

## Verification

```
python3 scripts/sim_plant_range_cell_profile.py
```

Exit 0 = full profile lifecycle passes + audit chain verifies.

## Remaining

- Live wiring after captain scope + $ ceiling (PO decision)
- G6 profile lock deploy
- Physical estop circuit wiring matches runbook
