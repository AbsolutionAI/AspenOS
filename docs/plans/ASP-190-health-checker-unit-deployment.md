# Plan: ASP-190 — Deploy starship-health-checker.service in .deb package + install-daemon

## Spec (required before code)
- **Problem:** `starship-health-checker.service` exists in `systemd/` (and a near-duplicate
  in `config/`) but no deployment path ships or registers it:
  - `scripts/build-deb.sh` omits it from the systemd unit copy loop, and never packages
    `scripts/agent-health-checker.py`, so the .deb contains neither the unit nor its backing script.
  - `debian/DEBIAN/postinst` never enables `starship-health-checker`; `prerm` never stops/disables it.
  - `scripts/install-daemon.sh` copies every other unit to `/etc/systemd/system/`,
    enables and starts them, but skips health-checker entirely (script + unit + enable + start).
  - `scripts/uninstall-daemon.sh` only removes `agnetic-*` units, so a deployed
    health-checker unit would leak across uninstall.
  Net effect: after a clean .deb install or `install-daemon.sh` run, the health checker
  documented in README (`sudo bash scripts/install-health-checker.sh`) silently never exists.
  Flagged in the nightly packaging check (`docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`,
  backlog item "ASP-151 / ASP-190").
- **Success criteria:**
  1. A `.deb` built by `scripts/build-deb.sh` contains
     `./lib/systemd/system/starship-health-checker.service` and
     `./opt/starship/lib/starship/scripts/agent-health-checker.py`.
  2. `debian/DEBIAN/postinst` enables `starship-health-checker` (fresh install) and
     restarts it on upgrade; `prerm` stops/disables it on remove/purge.
  3. `scripts/install-daemon.sh` installs the script to
     `/opt/starship/lib/starship/scripts/`, installs the unit, enables + starts it,
     and reports it in the final status loop.
  4. `scripts/uninstall-daemon.sh` stops/disables/removes the unit.
  5. Layout validation in `build-deb.sh` guards both new paths against regression.
  6. `bash -n` clean on all edited shell scripts; built package passes `dpkg-deb -c` grep checks.
- **Plan doc:** docs/plans/ASP-190-health-checker-unit-deployment.md (this file)

## Approach
1. Write this plan first (CE gate).
2. `scripts/build-deb.sh`: add `starship-health-checker.service` to the systemd unit loop;
   add `agent-health-checker.py` to the `$PKG_ROOT/opt/starship/lib/starship/scripts/`
   copies (next to `message_history.py`); extend the required-path validation list with
   both new entries.
3. `debian/DEBIAN/postinst`: append `starship-health-checker` to the enable loop and to the
   upgrade-restart loop (unit already orders itself `After=/Wants=agnetic-nats.service`).
4. `debian/DEBIAN/prerm`: append `starship-health-checker` to the stop/disable loop.
5. `scripts/install-daemon.sh`: copy `scripts/agent-health-checker.py` to
   `/opt/starship/lib/starship/scripts/` (+ chmod, canonical root per ASP-16 learning),
   copy the unit to `/etc/systemd/system/`, enable it, start it after NATS-dependent
   services, include it in the verify loop.
6. `scripts/uninstall-daemon.sh`: add `starship-health-checker` to stop/disable loop and an
   explicit `rm -f /etc/systemd/system/starship-health-checker.service`.
7. Verify: `bash -n` all edited scripts; run `bash scripts/build-deb.sh` (builds missing
   binaries) then `dpkg-deb -c dist/*.deb | grep health-checker` proving both payloads ship;
   `dpkg-deb -f` control sanity.
8. Commit (Paperclip co-author trailer). No push unless asked.

## Files
- `docs/plans/ASP-190-health-checker-unit-deployment.md` (this file)
- `scripts/build-deb.sh`
- `debian/DEBIAN/postinst`
- `debian/DEBIAN/prerm`
- `scripts/install-daemon.sh`
- `scripts/uninstall-daemon.sh`
- `docs/solutions/asp-190-health-checker-unit-deployment.md` (compound learning)

## Non-goals
- `src/python/lib/scripts/install-daemon.sh` / `build-deb.sh` stale duplicates: they still
  target the removed `installed/` layout and a nonexistent `agneticctl/` binary path, i.e.
  they have diverged from canonical `scripts/` long ago. Mirroring changes there would
  perpetuate drift; flagged for the stale-tree cleanup track instead (cf. ASP-352 scope).
- `config/starship-health-checker.service` near-duplicate cleanup (tracked under ASP-353
  dedup work; canonical deployed unit remains `systemd/`).
- `deploy/` stale units (ASP-152/192/352) and ISO hook paths (ASP-120/191).
- Enabling the cron variant (`config/cron.d/`) from packaging — systemd unit supersedes it;
  cron stays opt-in via manual copy.

## Acceptance
- [ ] Plan written before code edits
- [ ] `dpkg-deb -c` shows unit + checker script in the built package
- [ ] postinst/prerm/install-daemon/uninstall-daemon lists updated consistently
- [ ] `bash -n` clean on all edited shell scripts
- [ ] Compound learning written
- [ ] Working tree committed (only ASP-190 files staged); disposition recorded
