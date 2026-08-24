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
| [ADR-0001](./ADR-0001-aspen-grove-packaging.md) | Aspen Grove GitHub packaging | Accepted | Package mesh / licenses |
| [ADR-0002](./ADR-0002-swarm-rrm-boundaries.md) | Swarm manager vs Edge RRM vs micro-agents | Accepted | Fleet layering |
| [ADR-0003](./ADR-0003-fleet-edge-safety-contracts.md) | Fleet / edge safety contracts | Accepted | Bus + arm/e-stop + G8 authz |
| [ADR-0004](./ADR-0004-light-core-plugins.md) | Light core + plugins | Accepted | Optional deps |
| [ADR-0005](./ADR-0005-langgraph-execution-plugin.md) | LangGraph as execution plugin | Accepted | Paperclip remains org SoR |
| [ADR-0006](./ADR-0006-memory-store-tiering.md) | Tiered memory store (LanceDB vs PG+AGE) | **Accepted** | 2026-08-24 · ASP-428 / ASP-426 D1 · T1 default; T2 optional |
| [ADR-0010](./0001-c11-agent-runtime.md) | C11 agent runtime (legacy file `0001-…`) | Accepted | Logical **0010**; file keeps historic name |

### Open candidates (not yet filed)

| ID | Topic | Trigger |
|----|-------|---------|
| ADR-0007 | Sunset dual-publish (`starship.*`/`agnetic.*` → `aspen.*` only) | >50% consumers on `aspen.*` or first external plant pilot |
| ADR-0008 | Authenticated operator-of-record binding for DualHumanGate | Before any non-sim arm (G9+) |

## Related docs

- Product SoR: `docs/sor/MASTER_SPEC.md` (§3.1 Data & Memory)
- Act gate contract (H-016/G8): `docs/security/ACT_GATE_CONTRACT.md`
- Fleet subject inventory: `docs/ops/FLEET_SUBJECT_PUBLISHERS.md`
- Memory design: `docs/architecture/MEMORY_LAYER.md` (BEL-154)
- ABS path ownership: `docs/ops/ABS_MIRROR_ROUTING.md`
- Weekly reviews: `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_*.md`

## How to add an ADR

1. Copy the shape of `ADR-0006-memory-store-tiering.md` (Context → Decision → Consequences → Alternatives).
2. Use the next free `ADR-NNNN` number.
3. Add a row to this index in the same PR.
4. Link parent Paperclip / Linear IDs in the Status block.
5. Do not mark **Accepted** without architecture review (ASP Weekly Architecture Review or explicit human accept).
