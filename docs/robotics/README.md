# Plant Range Robotics Docs

> BEL-192 / ASP-416 G6 · Phase D: first physical cell gate

This directory contains the **plant-range cell profile** deliverables for the
training range (isolated plant). These documents define what is possible at G6
(sim-only), what is forbidden, and what gates must clear for G7/G8/G9.

## Deliverables

| File | Purpose |
|---|---|
| `plant-range-cell-profile.yaml` | Machine-readable cell profile (YAML) |
| `plant-range-arm-runbook.md` | Operator runbook: arm control, hold-to-enable, forbidden paths |
| `sim-verify-cell-acl.py` | In-process simulation that proves ACL and cell profile constraints |

## Quick Start

```bash
# Verify cell profile syntax
python3 -c "import yaml; yaml.safe_load(open('docs/robotics/plant-range-cell-profile.yaml')); print('YAML valid')"

# Run cell ACL proof
cd /home/tech/aspen-dev/repos/aspen-os
PYTHONPATH=agents:../aspen-swarm-manager:../aspen-edge-rrm \
  ASPEN_SIM=1 python3 docs/robotics/sim-verify-cell-acl.py

# Run dual-human gate refuse proofs (BEL-192 Phase D gate)
python3 scripts/sim_dual_human_gate.py

# Run end-to-end act-gate wire drill (G8 / H-016, ASP-364)
python3 scripts/sim_act_gate_wire.py

# Run full fleet bus smoke
python3 scripts/smoke-fleet-bus.py
```

## Verification Checklist

- [ ] All 14 ACL/constraint tests pass (sim-verify-cell-acl.py exit 0)
- [ ] Cross-plant schedule from plant-range refused
- [ ] Same-plant schedule accepted
- [ ] fleet_policy.py denies cross-plant from isolated range
- [ ] Hold-to-enable skill wired in `agents/robotics.yaml`
- [ ] Robotics role added to plant-range in `config/fleet.yaml`

## Gate Dependencies

| Gate | Issue | What it enables |
|---|---|---|
| G6 (this) | ASP-416 | Cell profile, hold-to-enable skill, sim-only ACL proof |
| G7 | ASP-417 | Estop latch + audit chain on range cell |
| G8 | H-016 (ASP-364) | Dual-human authorize usable |
| G9 | _(future)_ | Captain \$ ceiling approved |