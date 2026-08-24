# Packaging hygiene: health-checker packaging, stale deploy/ archive, ISO root migration

**Tickets:** ASP-151, ASP-190, ASP-353 (A); ASP-352, ASP-152, ASP-192 (B); ASP-120, ASP-191 (C)

## Problem

Three packaging-hygiene gaps on `ox/packaging-hygiene`:

1. `systemd/starship-health-checker.service` was canonical but absent from the
   .deb copy list (`scripts/build-deb.sh`) and from the daemon installer
   (`scripts/install-daemon.sh`); a near-duplicate sat in `config/`.
2. `deploy/` held legacy systemd units referencing non-existent
   `nats.service`/`staragent.service`, `Type=forking`, and `User=tech`.
3. The ISO chroot hook provisioned under `/opt/agnetic` while every consumer
   expects `/opt/starship`.

## Changes (this change set, uncommitted)

| File | Change | Closes |
|---|---|---|
| `config/starship-health-checker.service` | Deleted — duplicate of `systemd/starship-health-checker.service` (canonical source kept single; richer Description merged into canonical). `config/cron.d/starship-health-checker` retained (distinct cron run mode, documented alternative). | ASP-353, ASP-151 |
| `scripts/build-deb.sh` | Added `starship-health-checker.service` to the systemd copy list; ships `scripts/agent-health-checker.py` to `opt/starship/lib/starship/scripts/` so the shipped unit has its backing script. | ASP-151, ASP-190, ASP-353 |
| `scripts/install-daemon.sh` | Installs `starship-health-checker.service` + `agent-health-checker.py`, and `systemctl enable starship-health-checker.service`. | ASP-151, ASP-190 |
| `scripts/smoke-test.sh` | New cheap check: `build-deb ships health-checker unit` (greps build-deb list + canonical file exists). | ASP-353 |
| `archive/deploy-systemd-legacy/` | 5 former `deploy/*.service`/`*.target` units moved here via git history preservation, plus README marking them historical/not used by the packager. Complements commit `29ba44b` (ASP-192 removal of `deploy/`). | ASP-352, ASP-152, ASP-192 |
| `docs/solutions/ox-packaging-hygiene.md` | This note. | all |

## Parallel work already committed on this branch

- `29ba44b` — chore(deploy): remove stale incompatible systemd units (ASP-192)
- `c4325e9` — fix(iso): migrate chroot hook to `/opt/starship` roots with
  legacy `/opt/*agnetic` compat symlinks (ASP-120 / ASP-191)

Both are consistent with this change set; no overlap conflicts.

## Verification

- `bash -n` clean on `scripts/build-deb.sh`, `scripts/install-daemon.sh`,
  `scripts/smoke-test.sh`.
- `bash scripts/smoke-test.sh`: 53 passed / 5 failed. New health-checker check
  PASSES. All 5 failures are pre-existing environment issues, untouched by
  this diff: `make build` needs Go at `/tmp/go/bin` (absent here) → breaks
  `starshipctl builds/version/tui`; `sandbox_run -- /bin/echo ok` times out in
  this container (seccomp/ns restriction) → breaks `C11 sandbox echo` and
  `C11 p50 under 2ms`.

## Patterns to reuse

1. **Canonical units live only in `systemd/`.** Packagers and installers must
   reference that directory; never re-copy unit content into `config/`.
2. **A shipped unit ships its ExecStart target.** Adding a unit to
   `build-deb.sh` implies shipping any script it executes.
3. **Legacy roots survive as symlinks only** (`/opt/agnetic → /opt/starship`
   et al.), mirroring `install-daemon.sh`'s transitional dual-root block.

## Remaining / out of scope

- `debian/DEBIAN/postinst` does not auto-enable `starship-health-checker`
  (brief scoped enablement to `install-daemon.sh`; raw enables there mirror
  existing postinst style).
- Ollama installer version-pinning in the ISO hook deliberately skipped
  (also deferred per `docs/plans/ASP-120-*`).
