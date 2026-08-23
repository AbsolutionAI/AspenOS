# Architecture Decision Records (ADRs)

Aspen OS / AspenGrove architecture decisions. Prefer short, statused markdown in this directory.

**Naming**

| Pattern | Use |
|---------|-----|
| `ADR-NNNN-kebab-title.md` | Canonical grove / product ADRs (preferred) |
| `NNNN-kebab-title.md` | Legacy Starship-era ADRs (retained) |

**Statuses:** Proposed · Accepted · Superseded · Deprecated

## Index

| ID | Title | Status | Notes |
|----|-------|--------|-------|
| [0001](./0001-c11-agent-runtime.md) | C11 agent runtime | Legacy | Starship / agnetic runtime note |
| [ADR-0001](./ADR-0001-aspen-grove-packaging.md) | Aspen Grove GitHub packaging | Accepted | Package mesh / licenses |
| [ADR-0002](./ADR-0002-swarm-rrm-boundaries.md) | Swarm manager vs Edge RRM vs micro-agents | Accepted | Fleet layering |
| [ADR-0003](./ADR-0003-fleet-edge-safety-contracts.md) | Fleet / edge safety contracts | Accepted | Bus + arm/e-stop |
| [ADR-0004](./ADR-0004-light-core-plugins.md) | Light core + plugins | Accepted | Optional deps |
| [ADR-0005](./ADR-0005-langgraph-execution-plugin.md) | LangGraph as execution plugin | Accepted | Paperclip remains org SoR |
| [ADR-0006](./ADR-0006-memory-store-tiering.md) | Tiered memory store (LanceDB vs PG+AGE) | **Proposed** | BEL-154 + Master Spec §3.1 |

## Related docs

- Product SoR: `docs/sor/MASTER_SPEC.md` (§3.1 Data & Memory)
- Memory design: `docs/architecture/MEMORY_LAYER.md` (BEL-154)
- ABS path ownership: `docs/ops/ABS_MIRROR_ROUTING.md`

## How to add an ADR

1. Copy the shape of `ADR-0006-memory-store-tiering.md` (Context → Decision → Consequences → Alternatives).
2. Use the next free `ADR-NNNN` number.
3. Add a row to this index in the same PR.
4. Link parent Paperclip / Linear IDs in the Status block.
5. Do not mark **Accepted** without architecture review (ASP Weekly Architecture Review or explicit human accept).
