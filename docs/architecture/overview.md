# Aspen OS / Starship monorepo — Architecture Overview

**Canonical product SoR:** [`docs/sor/MASTER_SPEC.md`](../sor/MASTER_SPEC.md) (AspenGrove v4.0 — Three Organs).  
**ADRs:** [`docs/adr/README.md`](../adr/README.md)  
**Last architecture review:** [`docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-08-22.md`](../ops/WEEKLY_ARCHITECTURE_REVIEW_2026-08-22.md)

This monorepo is the **AspenOS / Starship Alpha** implementation tree. Product boundaries:

| Organ | Role |
|-------|------|
| **AspenOS** | Agentic OS / plant & edge control plane |
| **Aspen Sentinel** | HITL C2 / audit / fleet awareness (dashboard evolution) |
| **aspen-dev** | Paperclip companies + Hermes personas + CE (not a plant scheduler) |

## High-level stack

```
Operator:     Aspen Sentinel / dashboard · starshipctl · OpenCode · Paperclip board
     │
Org mesh:     Paperclip + Hermes (aspen-dev) — issues, budgets, personas
     │
Runtime:      NATS/JetStream · agent daemons · skills · optional LangGraph worker
     │
Fleet:        swarm-manager · edge-rrm · micro-agents (propose_act only)
     │
Services:     policy · hooks · shield · memory · telemetry · healer · incidents
     │
Inference:    OpenRouter Flash (default volume) · Grok (architect) · Ollama offline-only
     │
OS:           Ubuntu 24.04 · systemd · AppArmor · cgroups · optional C11 sandbox
```

## Safety (non-negotiable)

- Safety-adjacent bus path: agents emit **`propose_act` only** until **dual human authorization**.
- E-stop: `aspen.safety.estop` highest precedence on every RRM.
- Sim default under fiscal freeze: `ASPEN_SIM=1`; no physical cell without gate.

## Runtime paths (target)

| Path | Purpose |
|------|---------|
| `/opt/starship` | Application install |
| `/etc/starship` | Config (policy, models, hooks) |
| `/var/lib/starship` | State (memory, accounts, healer) |
| `/var/log/starship` | Logs |

Legacy `/opt/agnetic` may still appear in Alpha installs — treat as migration debt.

## Bus subjects

| Family | Canonical (ADR-0003) | Legacy bridge |
|--------|----------------------|---------------|
| Fleet | `aspen.fleet.*` | `starship.fleet.*`, `agnetic.fleet.*` |
| Edge | `aspen.edge.<node>.*` | — |
| Safety | `aspen.safety.*` | — |
| Worker | `aspen.worker.langgraph.*` | — |
| Alpha agents | `starship.agent.*` | `agnetic.agent.*` |

## Source layout (this monorepo)

| Path | Content |
|------|---------|
| `src/python/services/`, `services/` | Service modules |
| `src/python/lib/`, `agents/` | Agent loop, tools, dashboard |
| `src/c/` | C11 sandbox / policyexec spikes (ADR-0010) |
| `agent/` | StarAgent Rust telemetry |
| `starshipctl/` | Go CLI |
| `docs/sor/`, `docs/adr/` | Product + decision SoR |
| `packaging/`, `debian/`, `iso/`, `systemd/` | Install & ISO |

## Ports (default)

| Service | Port |
|---------|------|
| NATS | 4222 |
| Ollama (optional local) | 11434 |
| Dashboard (C2) | 8788 |

## Related

- Fleet topology: `docs/FLEET.md`, `docs/MULTI_NODE.md`
- Model routing / freeze: `docs/MODEL_ROUTING.md`
- Memory layer: `docs/architecture/MEMORY_LAYER.md` (when present)
- Grove packages: `docs/PACKAGE_MAP.md` (when present)
