# ADR-0004: Light core vs plugins (AspenOS)

## Status
Accepted — 2026-08-06  
**Linear:** BEL-183 · BEL-114 · Epic BEL-179

## Context
AspenOS must stay a small coherent kernel while adding fleet, swarm, edge, and plant drivers. Monolith growth blocks packaging and third-party review.

## Decision

### In kernel (always-on)
| Module | Role |
|--------|------|
| Agent loop / tool dispatch | Run one agent turn |
| Policy + governance gates | Allow/deny |
| Event envelope codec | aspen-contracts |
| Local config + secrets refs | Paths only |
| Health `/health` | Process liveness |
| NATS/MQTT client **interfaces** | Adapters injected |

### Plugins (loadable)
| Plugin class | Examples | Package |
|--------------|----------|---------|
| Fleet topology | ops-manager, plant ACL | swarm-manager, edge-rrm |
| Drivers | MQTT, OPC-UA, ROS2 | edge adapters |
| Swarm missions | mission DAG | aspen-swarm-manager |
| Memory / RAG | LanceDB, etc. | optional |
| Dashboard UI | C2 panels | aspen-dashboard |
| Process workers | Aider, A0 | aspen-process-workers |

### Rules
1. Kernel must not import vendor SDKs (Fanuc, ROS, etc.).
2. Plugins speak **only** bus contracts + kernel-facing APIs.
3. Physical act path: micro-agent → RRM plugin → driver plugin → hardware.
4. Extract path: grow `aspen-agent-runtime` from kernel slice; keep AspenOS as product umbrella.

### Acceptance
- New plant protocol = new plugin package, not kernel bump
- `aspen-edge-rrm` and `aspen-swarm-manager` remain installable without full AspenOS tree

## Consequences
- BEL-114 spike closed by this table
- Runtime extract work prioritizes kernel list above
- Driver work stays in edge packages

## Alternatives rejected
- Everything-in-AspenOS monorepo forever  
- Per-robot forks of the kernel  
