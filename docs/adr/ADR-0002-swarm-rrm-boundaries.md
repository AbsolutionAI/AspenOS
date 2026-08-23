# ADR-0002: Swarm manager vs Edge RRM vs micro-agents

## Status
Accepted — 2026-08-06  
**Linear:** BEL-180 · Epic BEL-179

## Context
AspenOS must coordinate cobots/swarms and edge devices without collapsing C2, scheduling, and on-device supervision into one process. Physical safety and fiscal freeze require clear boundaries.

## Decision

### Layers
| Layer | Package / home | Responsibility |
|-------|----------------|----------------|
| C2 | Paperclip, Aspen dashboard, Hermes | Human tasks, spend, mission *authoring* |
| Swarm / Cobot Manager | `aspen-swarm-manager` | Mission DAG, membership, capability match, arm gates |
| Edge RRM | `aspen-edge-rrm` | On-device agent lifecycle, budgets, offline queue, heartbeat |
| Micro-agents | SDK under edge-rrm | sense → decide* → **propose_act** only |
| Drivers | plugins | MQTT / OPC-UA / ROS2 / vendor — last mile |

### Rules
1. **Micro-agents never write actuators directly.** Only `propose_act` → RRM → safety → driver.
2. **Swarm manager never streams setpoints.** It assigns missions and arm/hold/abort.
3. **C2 agents (Hermes robotics) talk to swarm API only**, not to device drivers.
4. **Human arm gate** required before mission state `running` when profile is production or any real hardware flag is set. Sim profile may auto-arm with `ASPEN_SIM=1`.
5. **E-stop** is a bus-wide subject consumed by every RRM; highest precedence.
6. **Offline edge:** RRM stores-and-forwards; drops non-critical; never assumes cloud LLM.

### Mission state machine
`planned → armed → running → held → done | failed`  
Abort from any non-terminal state → `failed` + safe defaults.

## Consequences
- New public packages: swarm-manager, edge-rrm
- Contracts subjects in ADR-0003 / aspen-contracts
- Physical cell (Phase D) blocked until sim E2E green

## Alternatives rejected
- Single monolith agent on the robot with full tool access  
- Paperclip issuing joint commands  
- On-device large LLM as default supervisor  
