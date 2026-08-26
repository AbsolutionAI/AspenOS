# ASP-352 — Remove stale `deploy/` systemd unit directory

## Spec

- **Problem:** `deploy/` held 5 stale "agnetic"-branded systemd units from an older layout, superseded by the canonical `systemd/` directory used by `scripts/install-daemon.sh`, `scripts/build-deb.sh`, `scripts/install-systemd.sh`, and `scripts/smoke-test.sh`. No build, packaging, or CI path referenced `deploy/`.
- **Success criteria:** `deploy/` no longer exists in the repo; no live references remain; canonical units remain solely under `systemd/`.
- **Plan doc:** this file.

## Resolution — dedupe with ASP-192

Scope is identical to [ASP-192](ASP-192-deploy-stale-units-cleanup.md), which landed first on branch `ox/packaging-hygiene` via commit `29ba44b` ("chore(deploy): remove stale incompatible systemd units"). That commit:

- Deleted all 5 files: `agnetic-agent-mesh.target`, `agnetic-agent@.service`, `agnetic-dashboard.target`, `agnetic-dashboard-web.service`, `agnetic-status-bridge.service`.
- Updated `docs/ARCHITECTURE_COMPLETE.md` (dropped §2.8 and the §7 `deploy/*` row).
- Recorded the canonical learning in `docs/solutions/asp-192-deploy-stale-units.md`.

No further code change was required for ASP-352; this ticket closes as satisfied by that work. A stray *empty* untracked `deploy/` directory (side effect of a concurrent packaging script run) was removed with `rmdir`.

## QA (verified 2026-08-22 on `ox/packaging-hygiene`)

- `test ! -e deploy` passes at HEAD (`c4325e9`).
- `git grep -n 'deploy/' -- ':!docs' ':!*.md'` → no matches across code, scripts, packaging, debian, iso, and CI.
- Remaining `docs/plans/*` / `docs/solutions/*` mentions are historical decision records (intentionally kept).
- Canonical units intact under `systemd/`; consumers (`install-daemon.sh`, `build-deb.sh`, `install-systemd.sh`, `smoke-test.sh`) unaffected.

## Disposition

**SUPERSEDED** (ASP-482 sweep — 2026-08-26) — Ticket closed as satisfied by ASP-192 work. `deploy/` directory removed. Zero code/script/packaging references to `deploy/` remain. Canonical learning: `docs/solutions/asp-192-deploy-stale-units.md`.
