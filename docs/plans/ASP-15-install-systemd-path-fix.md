# Plan: ASP-15 — Fix install-systemd.sh stale path (ASP-10 finding #8)

## Spec (required before code)
- **Problem:** `scripts/install-systemd.sh` (and its duplicate
  `src/python/lib/scripts/install-systemd.sh`) hardcodes
  `SERVICES_DIR="/home/tech/agnetic-os/systemd"`, which does not exist in the
  current repo layout (units live at `<repo>/systemd/`). It also iterates a
  service name `agnetic-agents` that has no matching unit (the real unit is the
  template `agnetic-agent@.service`). Running the documented
  `sudo bash scripts/install-systemd.sh` would silently skip every unit.
  Left untracked by the ASP-10 audit; identified as HIGH finding #8.
- **Success criteria:**
  1. `install-systemd.sh` resolves the units directory relative to its own
     location (`<repo>/systemd/`), with a runtime fallback to the canonical
     `/opt/starship/systemd` when run outside the repo.
  2. Service list matches real units: `agnetic-nats`, `agnetic-staragent`,
     `agnetic-agent@` template instances, `agnetic-dashboard`,
     `agnetic-status-bridge`, `agnetic-message-history`, `agnetic-mesh.target`.
  3. No `$HOME`-style or `/home/tech/...` hardcoded path remains.
  4. `bash -n` clean on both copies.
- **Plan doc:** docs/plans/ASP-15-install-systemd-path-fix.md (this file)
- **Out of scope:** `deploy/` stale developer units (ASP-10 finding #9 —
  architectural decision on whether to delete), `build-deb.sh`/`build-iso.sh`
  root-vs-src duplication, health-checker `/opt/starship-os` path (ASP-10
  finding #10). Flag these for the Architect if not already tracked.

## Approach
1. Write this plan first (CE gate).
2. In `scripts/install-systemd.sh` and `src/python/lib/scripts/install-systemd.sh`:
   - Replace hardcoded `SERVICES_DIR` with a script-relative resolution:
     `SERVICES_DIR="$(cd "$(dirname "$0")/../systemd" && pwd)"` guarded by a
     check, with `SERVICES_DIR="${SERVICES_DIR:-/opt/starship/systemd}"`
     fallback when the repo copy is absent.
   - Replace the `agnetic-agents` entry with the real units installed by
     `install-daemon.sh` (nats, staragent, agent@ instances, dashboard,
     status-bridge, message-history) and enable `agnetic-mesh.target`.
   - Install `agnetic-agent@.service` (template) alongside the instances.
3. Verify: `bash -n` on both files; `grep -rn '/home/tech/agnetic-os'` in the
   two files returns nothing.
4. Commit with Paperclip co-author. No push (GitHub auth follow-up still open
   per FOUNDATION).

## Files
- `docs/plans/ASP-15-install-systemd-path-fix.md` (this file)
- `scripts/install-systemd.sh`
- `src/python/lib/scripts/install-systemd.sh`

## Non-goals
- No changes to `install-daemon.sh` (already correct).
- No deletion of `deploy/` stale units (Architect decision).
- No doc edits in this pass beyond the plan.

## Acceptance
- [x] Plan written before code edits
- [x] Both `install-systemd.sh` copies resolve units from repo `systemd/` with `/opt/starship/systemd` fallback
- [x] Real unit names used; no `agnetic-agents` phantom service
- [x] `bash -n` clean
- [x] Working tree clean after commit; ASP-15 disposition recorded

## Disposition (ASP-480 sweep — 2026-08-25)

**Status: Completed.** All acceptance criteria met. Both `install-systemd.sh` copies resolve units from repo `systemd/` with `/opt/starship/systemd` fallback. Real unit names used; no `agnetic-agents` phantom service. `bash -n` clean. Implementation confirmed on current branch.
