# ADR-0008: AspenGrove Package Classification (Core / Plugin / Dev-only)

**Status:** Proposed — 2026-08-29  
**Linear:** BEL-195 (A2) · Parent BEL-193 (AspenGrove Three-Product Epic)  
**Related:** ADR-0001 (Aspen Grove GitHub Packaging), ADR-0004 (Light Core + Plugins), Master Spec v4.0 §2.3 (Packaging), PACKAGES.md

## Context
aspen-dev owns the packaging and evolution of AspenOS / Aspen Sentinel. Ambiguity in package ownership leads to agent extraction errors, license conflicts, and unclear boundaries between what ships with the OS vs what is optional vs what is internal tooling.

## Decision
Formalize a three-tier classification locked into ADRs and PACKAGES.md.

### Classification Matrix

| Tier          | Definition                                                                 | Ownership          | License          | Examples                                      | Agent Visibility |
|---------------|----------------------------------------------------------------------------|--------------------|------------------|-----------------------------------------------|------------------|
| **Core**     | Must ship with every AspenOS / Sentinel install. Minimal runtime surface. | aspen-dev (shared) | MIT (core)      | aspen-os-runtime, nats-client, event-envelope, safety-estop driver | Always present |
| **Plugin**   | Optional, loadable at runtime. Extend capability without forking core.   | aspen-dev + community | MIT or dual     | langgraph-execution (ADR-0005), pgvector-memory, ros2-bridge, opc-ua-adapter | Install via catalog |
| **Dev-only** | Internal tooling, CI, packaging, test harnesses. Never in production images. | aspen-dev         | MIT + commercial| package-mesh scripts, compound-engineering tools, grok-build sandbox | aspen-dev only |

### Rules
1. **Core** packages live in `aspen-os/` and `aspen-sentinel/` top-level. Minimal dependencies.
2. **Plugins** declare `aspen-plugin` metadata + capability manifest. Installed via Paperclip catalog or `aspen package install`.
3. **Dev-only** confined to `aspen-dev/` repo and never referenced in production Dockerfiles or agent images.
4. All packages must declare `classification` in `pyproject.toml` / `Cargo.toml` / `package.json`.
5. License matrix: Core = MIT; Plugins may add commercial rider; Dev-only = internal.

### Updated PACKAGES.md Structure (excerpt)
```markdown
## AspenGrove Packages v4.0

### Core (ship with every install)
- aspen-runtime
- aspen-nats
- aspen-safety

### Plugins (optional)
- aspen-langgraph
- aspen-memory-pgvector

### Dev-only (aspen-dev internal)
- aspen-package-mesh
- compound-engineering-gate-tools
```

## Consequences
- **Positive**: Agents can safely discover and install only appropriate packages; clear governance for aspen-dev ownership; supports Light Core vs Full Plant profiles.
- **Risks**: Over-classification of useful plugins as Dev-only (mitigate via review in ADR process).
- **Migration**: Existing packages audited and re-tagged in one pass (tracked in BEL-195).

## Acceptance Criteria
- ADR merged into docs/adr/
- PACKAGES.md reflects Core / Plugin / Dev-only split with examples
- Cross-links added to AspenOS README and Master Spec
- No ambiguity for future agents extracting packages from the grove

**Next**: Update aspen-contracts schema if needed; implement package catalog install hook in Paperclip.