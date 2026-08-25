# ASP-192 — Remove stale `deploy/` systemd units

## Spec

- **Problem:** `deploy/` holds 5 systemd units from an older layout that conflict with the canonical `systemd/` directory. Installing both sets produces broken dependency chains and shadowed units.
  - `agnetic-agent-mesh.target` requires `nats.service` / `staragent.service` — names that do not exist (canonical: `agnetic-nats.service`, `agnetic-staragent.service`).
  - `agnetic-agent@.service` uses the old `Type=forking` + PIDFile pattern with `User=tech`; canonical unit is `Type=simple` as `User=agnetic`.
  - Duplicate targets (`agnetic-agent-mesh.target`, `agnetic-dashboard.target`) compete with `systemd/agnetic-mesh.target`.
  - Nothing in Makefile, scripts, packaging, debian, iso, or CI references `deploy/`.
- **Success criteria:** `deploy/` no longer exists in the repo; no build/packaging/docs path references it as a live artifact; canonical units remain solely under `systemd/`.
- **Plan doc:** this file.
- **Out of scope:** changes to `systemd/` units; ISO/deb packaging changes.

## Changes

1. Delete `deploy/` (5 files: `agnetic-agent-mesh.target`, `agnetic-agent@.service`, `agnetic-dashboard.target`, `agnetic-dashboard-web.service`, `agnetic-status-bridge.service`).
2. `docs/ARCHITECTURE_COMPLETE.md`: drop §2.8 (`deploy/`) and the `deploy/*` row in the configuration reference table (§7); renumber subsequent §2.x sections.
3. Compound learning in `docs/solutions/asp-192-deploy-stale-units.md`.

## QA

- `grep -r "deploy/"` over code/scripts/packaging paths returns no live references (docs/historical plan/solution notes excluded or updated).
- `git grep -l "agnetic-agent-mesh"` empty after change.
- No tests reference these files (verified pre-change).

## History

- Previously deferred by ASP-10 #9 / ASP-15 / ASP-16 / ASP-18 as "Architect decision"; ASP-187 nightly check flagged it again → cleanup now assigned here ([ASP-152](/ASP/issues/ASP-152), [ASP-352](/ASP/issues/ASP-352) track sibling packaging hygiene).
