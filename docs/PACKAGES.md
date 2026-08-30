# AspenGrove Packages — Classification & Ownership (v4.0)

**Status:** Authoritative (aligned with ADR-0008)  
**Owner:** aspen-dev  
**Cross-links:** ADR-0001 (Packaging), ADR-0004 (Light Core + Plugins), ADR-0008 (Core/Plugin/Dev-only), Master Spec v4.0 §2.3

## Classification Matrix

| Tier          | Definition                                                                 | Ownership          | License          | Examples                                      | Visibility / Install |
|---------------|----------------------------------------------------------------------------|--------------------|------------------|-----------------------------------------------|----------------------|
| **Core**     | Must ship with every AspenOS / Sentinel install. Minimal runtime surface. | aspen-dev (shared) | MIT (core)      | aspen-os-runtime, nats-client, event-envelope, safety-estop driver, aspen-nats | Always present in base images |
| **Plugin**   | Optional, loadable at runtime. Extend capability without forking core.   | aspen-dev + community | MIT or dual     | langgraph-execution (ADR-0005), pgvector-memory, ros2-bridge, opc-ua-adapter, memory-tiering | Paperclip catalog or `aspen package install` |
| **Dev-only** | Internal tooling, CI, packaging, test harnesses. Never in production images. | aspen-dev         | MIT + commercial| package-mesh scripts, compound-engineering tools, grok-build sandbox, gatekeeper-shim (dev) | aspen-dev only |

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

## Dev-only Examples (internal only)
- aspen-package-mesh
- compound-engineering-gate-tools
- gatekeeper/minimal_shim.py (development prototype)

## Acceptance
- PACKAGES.md is the single source of truth for classification.
- Agents and packaging tools can query this matrix without ambiguity.
- Updated whenever new packages are added or reclassified.

**Next:** Wire into aspen-package-mesh (BEL-164) and Paperclip catalog install hook.