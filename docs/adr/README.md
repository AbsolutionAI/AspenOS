# Architecture Decision Records

**Authority ladder:** `docs/sor/MASTER_SPEC.md` (v4.0) → ADRs in this directory → living maps (`FLEET.md`, `PACKAGE_MAP.md`, `MODEL_ROUTING.md`).

## Index (current)

| ID | File | Status | Topic |
|----|------|--------|-------|
| **ADR-0001** | [ADR-0001-aspen-grove-packaging.md](./ADR-0001-aspen-grove-packaging.md) | Accepted | Grove packaging layers, licenses, org split |
| **ADR-0002** | [ADR-0002-swarm-rrm-boundaries.md](./ADR-0002-swarm-rrm-boundaries.md) | Accepted | Swarm vs Edge RRM vs micro-agents |
| **ADR-0003** | [ADR-0003-fleet-edge-safety-contracts.md](./ADR-0003-fleet-edge-safety-contracts.md) | Accepted | `aspen.*` bus subjects + safety |
| **ADR-0004** | [ADR-0004-light-core-plugins.md](./ADR-0004-light-core-plugins.md) | Accepted | Kernel vs plugins |
| **ADR-0005** | [ADR-0005-langgraph-execution-plugin.md](./ADR-0005-langgraph-execution-plugin.md) | Accepted | LangGraph worker; Paperclip stays aspen-dev |
| **ADR-0010** (legacy “ADR 0001”) | [0001-c11-agent-runtime.md](./0001-c11-agent-runtime.md) | Accepted (spike) | C11 sandbox / policyexec path |

## Numbering note (resolved 2026-08-22 review)

Two historical “0001” labels existed:

1. **Starship C11 spike** — title “ADR 0001”, path `0001-c11-agent-runtime.md` (Jul 2026). Many code comments still say “ADR 0001”.
2. **AspenGrove packaging** — `ADR-0001-aspen-grove-packaging.md` (Aug 2026).

**Rule going forward:** new product/platform decisions use **`ADR-NNNN-kebab.md`** starting at **0006+**. The C11 document is **canonical ID ADR-0010**; keep the filename for git/history stability; do not open a second ADR-0001.

## Open / next ADRs (candidates)

| Candidate | Trigger | Owner |
|-----------|---------|-------|
| ADR-0006 Memory SoR (LanceDB vs PG+AGE+pgvector) | MEMORY_LAYER vs Master Spec §3.1 drift | aspen |
| ADR-0007 Subject dual-publish deprecation window | Code still on `starship.*`/`agnetic.*` | runtime + aspen |
| ADR-0008 Sentinel product boundary (dashboard split) | When Sentinel MVP starts (freeze-deferred) | aspen |
| ADR-0009 Soft-RT ↔ hard-RT bridge skeleton | Pre-Chaé / BEL physical cell | robotics |

## Writing an ADR

1. Copy structure from ADR-0002 (Context → Decision → Consequences → Alternatives rejected).
2. Link Linear `BEL-N` and Paperclip `ASP-N` when work is tracked.
3. Must not contradict Master Spec hard rules (`propose_act` only until dual human auth on safety-adjacent paths) without a Master Spec revision.
