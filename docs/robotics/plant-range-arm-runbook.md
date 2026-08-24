# Plant Range Arm Runbook

> BEL-192 / ASP-416 · G6 deliverable
> Plant: plant-range (Training Range, isolated)

## Status

**G6 — sim-only profile.** No live joints until G7 green (ASP-417 estop latch + audit
chain), dual-human authorize usable (H-016), and captain \$ ceiling approved.

## Scope

This runbook covers the cobot arm within plant-range only. plant-range is an
**isolated plant** (`isolation: true`) — all cross-plant ACLs deny outbound
traffic. The arm's hold-to-enable controller is the only actuation path.

---

## 1. Arm Operator Requirements

### Who can operate

- Any authenticated human with a plant-range role (`red-team`, `blue-team`, `ops`)
- Operator identity must be a stable human ID (not a session/device token)
- **The operator string MUST NOT be `"sim"`** — the cell profile enforces
  `allow_sim_operator: false`

### What "arm operator" means

The arm operator is the human who **holds the enable** during actuation. Holding
the enable is not an approval — it is a real-time physical or virtual presence
assertion that the operator is at the controls and can see the arm.

### Prohibited

- Operator string == `"sim"` (refused: `sim_operator_not_allowed`)
- Session-only identity (refused: `unauthenticated_operator`)
- Proposer's operator-of-record acting as arm operator (refused: `self_approval`;

  this is enforced at G8 dual-auth layer)

---

## 2. Hold-to-Enable Protocol

### Principle

The hold-to-enable (HTE) pattern requires the operator to continuously assert
"enable" to the arm controller. If the assertion stops (deadman switch), the
controller drops power to the arm joints within `max_interval_s`.

This is NOT an on/off switch — it is a real-time presence requirement.

### Protocol

```
┌──────────────┐     hold(open)     ┌──────────────┐
│  Enable      │ ──────────────────→│  Arm Ready   │   ← can execute planned motions
│  Button/DIN  │                    │  (armed)     │
│  Held        │ ←──────────────────│              │
│              │     release        │              │
│  Released    │ ──────────────────→│  Arm Halt    │   ← immediate decel, enable drops
└──────────────┘                    └──────────────┘
```

1. **Enable held** → arm controller enables joint power. Motions from the
   mission plan proceed.
2. **Enable released** → arm halts within `max_interval_s` (0.5 s). All actuator
   power drops.
3. **Re-enable** → operator must re-assert hold. New propose_act required if
   mission was in HELD state.

### Configuration

```yaml
# In cell profile (plant-range-cell-profile.yaml)
hold_to_enable:
  required: true
  max_interval_s: 0.5
  audit_event: "cell.hold_to_enable"
```

### Updates

- `aspen.edge.<node>.propose_act` events carry `enable_held: true|false`
- `aspen.fleet.mission.held` when enable drops mid-mission — reason=`enable_dropped`
- Every enable/release event is JSONL-audited at `audit/hold-to-enable.jsonl`

---

## 3. Forbidden Paths

The following operations are **refused** in plant-range at G6. They remain
forbidden until the named gate clears.

| Operation | Refuse Reason | Gate | Reference |
|---|---|---|---|
| Live joint motion | `no_hardware_until_g7` | G7 | ASP-417 |
| Cross-plant schedule | `cross_plant_denied` | isolation + ACL | fleet.yaml ACL |
| Hardware PO | `sim_only` | G9 captain ceiling | Procurement |
| ASPEN_SIM=0 driver start | `sim_only` | G7 | ASP-417 |
| arm_operator = "sim" | `sim_operator_not_allowed` | G6 | This runbook |
| Single-principal enable | `insufficient_principals` | G8 dual-auth | H-016 / G8 gate |

### Cross-plant refuse proof

The fleet ACL (`config/fleet.yaml`) and PlantACL (`aspen_swarm/plants.py`)
already enforce:

```python
# plant-range has isolation: True and may_schedule_into: {"plant-range"}
# → SwarmManager.submit(origin="plant-range", target="plant-alpha")
#   raises -> can_schedule("plant-range", "plant-alpha") == False
#   → mission FAILED with reason="acl_cross_plant"
```

See `scripts/sim-verify-cell-acl.py` (deliverable 3 of ASP-416).

---

## 4. Mission Lifecycle in Plant Range

```
planner/agent
    │
    ▼
propose_act (<enable_held: bool>)
    │
    ├── enable_held == False → REFUSED (hold_to_enable_not_engaged)
    │
    └── enable_held == True
            │
            ├── operator == "sim" → REFUSED (sim_operator_not_allowed)
            │
            └── operator != "sim"
                    │
                    ├── cross-plant target → REFUSED (acl_cross_plant)
                    │
                    └── same-plant
                            │
                            ├── live_joint_motion in action → REFUSED (no_hardware_until_g7)
                            │
                            └── sim motion only → ACCEPTED → mission planned
```

G7 adds estop latch enforcement. G8 adds dual-human authorize. G9 adds captain
ceiling checks.

---

## 5. Quick Reference

```bash
# Verify cell profile syntax
python3 -c "import yaml; yaml.safe_load(open('docs/robotics/plant-range-cell-profile.yaml'))"
echo "YAML valid"

# Run cross-plant ACL proof
python3 docs/robotics/sim-verify-cell-acl.py

# Run the full fleet bus smoke
ASPEN_SIM=1 python3 scripts/smoke-fleet-bus.py

# Run dual-human gate refuse proofs
python3 scripts/sim_dual_human_gate.py
```