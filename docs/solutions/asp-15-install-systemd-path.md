# Learning: Derive installer paths from script location, not $HOME (ASP-15)

**Date:** 2026-08-04
**Issues:** [ASP-15](/ASP/issues/ASP-15)
**Source:** ASP-10 nightly packaging & deployment audit finding #8 (HIGH, previously untracked)

## Bug
`scripts/install-systemd.sh` (and its `src/python/lib/scripts/` duplicate)
hardcoded `SERVICES_DIR="/home/tech/agnetic-os/systemd"` — a developer-machine
path that never existed in the current repo layout. It also iterated a phantom
service name `agnetic-agents`; no such unit exists (the real one is the
template `agnetic-agent@.service`). Running the documented
`sudo bash scripts/install-systemd.sh` silently skipped every unit.

## Pattern
- **Never hardcode `/home/<user>` paths in install scripts.** Resolve the repo
  root relative to the script itself (`SCRIPT_DIR="$(cd "$(dirname "$0")" &&
  pwd)"`; `REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"`) with a canonical
  fallback (`/opt/starship/systemd`) for the deployed layout.
- **Validate the service list against real unit files.** A unit named
  `agnetic-agents` does not exist; the mesh uses the `agnetic-agent@.service`
  template with instances `proxy`/`romi`/`ergo` plus `agnetic-nats`,
  `agnetic-staragent`, `agnetic-dashboard`, `agnetic-status-bridge`,
  `agnetic-message-history`, and `agnetic-mesh.target`.
- **Fix both copies.** This repo mirrors scripts under `scripts/` and
  `src/python/lib/scripts/`; identical stale bugs live in both.

## Files touched
- `scripts/install-systemd.sh`
- `src/python/lib/scripts/install-systemd.sh`
- `docs/plans/ASP-15-install-systemd-path-fix.md`

## Verification
- `bash -n` clean on both copies
- Dry-run path resolution: `SERVICES_DIR` resolves to repo `systemd/`; every
  referenced `.service`/`.target` file exists
- `grep '/home/tech/agnetic-os'` in both files returns nothing

## Still open (flagged, not tracked)
- `deploy/` stale developer units (ASP-10 finding #9) — needs Architect
  decision on deletion
- `scripts/backup-cron.sh` cron comment, `scripts/test-iso-auto.sh` embedded
  `/home/tech/agnetic-os` refs — stale dev-machine paths
- Health-checker `/opt/starship-os` path (ASP-10 finding #10)
