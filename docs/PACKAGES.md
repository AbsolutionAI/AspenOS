# AspenGrove Packages — Classification & Ownership (v4.0)

**Status:** Authoritative (aligned with ADR-0008)  
**Owner:** aspen-dev  
**Cross-links:** ADR-0001 (Packaging), ADR-0004 (Light Core + Plugins), ADR-0008 (Core/Plugin/Dev-only), Master Spec v4.0 §2.3

## Classification Matrix

| Tier          | Definition                                                                 | Ownership          | License          | Examples                                      | Visibility / Install |
|---------------|----------------------------------------------------------------------------|--------------------|------------------|-----------------------------------------------|----------------------|
| **Core**     | Must ship with every AspenOS / Sentinel install. Minimal runtime surface. | aspen-dev (shared) | MIT (core)      | aspen-os-runtime, nats-client, event-envelope, safety-estop driver, aspen-nats | Always present in base images |
| **Plugin**   | Optional, loadable at runtime. Extend capability without forking core.   | aspen-dev + community | MIT or dual     | langgraph-execution (ADR-0005), pgvector-memory, ros2-bridge, opc-ua-adapter, memory-tiering, **aspen-gatekeeper** (ADR-0009 / ASP-628) | Paperclip catalog or `aspen package install` |
| **Dev-only** | Internal tooling, CI, packaging, test harnesses. Never in production images. | aspen-dev         | MIT + commercial| package-mesh scripts, compound-engineering tools, grok-build sandbox | aspen-dev only |

## Rules
1. **Core** packages live in `aspen-os/` and `aspen-sentinel/` top-level. Minimal dependencies only.
2. **Plugins** declare `aspen-plugin` metadata + capability manifest in `pyproject.toml` / equivalent. Installed via Paperclip catalog or CLI.
3. **Dev-only** confined to `aspen-dev/` repo and never referenced in production Dockerfiles, agent images, or runtime paths.
4. Every package **must** declare `classification` field (core / plugin / dev-only).
5. License matrix enforced at packaging time (aspen-package-mesh).

## Current Core Packages (examples)
- aspen-runtime
- aspen-nats (JetStream client + envelope)
- aspen-safety (estop, propose_act enforcement)
- aspen-event-envelope

## Recommended Plugin Structure
```
aspen-plugin-langgraph/
├── pyproject.toml          # classification = "plugin"
├── manifest.json           # capabilities, subjects, version
└── src/...
```

## Plugin: aspen-gatekeeper (ASP-628)

| Field | Value |
|-------|-------|
| **classification** | `plugin` |
| **Source (until extract)** | monorepo `src/python/gatekeeper/` (P1+P2 + ASP-607 rate limits) |
| **Production name** | `aspen-gatekeeper` |
| **Plant profile** | Default **ON** when plant has actuators; **OFF** only for observation-only / Light-read profiles |
| **Not** | Always-on core-edge second binary (ADR-0004 light core) |
| **Core residual** | `aspen-safety` keeps estop + propose_act **contracts**; G8 dual-human remains in `aspen-edge-rrm` |
| **Deferred** | Durable token backend (Redis/PG); package extract + image matrix (needs Captain for prod image expand) |
| **Extract status** | **Skeleton exists** (`plugins/aspen-gatekeeper/`, ASP-630) — thin re-export shell; **no image matrix** yet; SoR remains `src/python/gatekeeper/` until extract |
| **Plan** | `docs/plans/ASP-628-gatekeeper-packaging.md` · `docs/plans/ASP-630.md` |

## Dev-only Examples (internal only)
- aspen-package-mesh
- compound-engineering-gate-tools
- monorepo path `src/python/gatekeeper/` while still unextracted (source SoR; **not** a prod image path by itself)

## Acceptance
- PACKAGES.md is the single source of truth for classification.
- Agents and packaging tools can query this matrix without ambiguity.
- Updated whenever new packages are added or reclassified.

**Next:** Wire into aspen-package-mesh (BEL-164) and Paperclip catalog install hook. Extract `aspen-gatekeeper` from `plugins/aspen-gatekeeper/` (skeleton, ASP-630) into its own package when packaging sprint + Captain allow image matrix work.