# Learning: New systemd units must be wired into every deployment path at once

**Ticket:** ASP-190

## Problem

`starship-health-checker.service` existed in `systemd/` but no deployment path shipped it:

- `scripts/build-deb.sh` omitted it from the systemd unit copy loop **and** never
  packaged its backing script (`scripts/agent-health-checker.py`).
- `debian/DEBIAN/postinst` enable/restart loops and `prerm` stop loop didn't list it.
- `scripts/install-daemon.sh` installed/enabled/started every other unit but skipped it.
- `scripts/uninstall-daemon.sh` only removed `agnetic-*` units, so even a manually
  deployed health-checker unit would leak across uninstall.

Result: after a clean `.deb` install or `install-daemon.sh`, the documented health
checker silently never existed (flagged by the nightly packaging check backlog).

## Fix

- `build-deb.sh`: added `starship-health-checker.service` to the unit loop, packaged
  `agent-health-checker.py` into `/opt/starship/lib/starship/scripts/`, and added both
  to the required-path layout validation so regressions fail the build.
- `postinst`: enabled it on install + restarts it on upgrade (unit self-orders via
  `After=/Wants=agnetic-nats.service`). `prerm`: stops/disables it on remove/purge.
- `install-daemon.sh`: installs script + unit, enables, starts, includes in verify loop.
- `uninstall-daemon.sh`: stop/disable + explicit `rm` of the unit (it isn't matched by
  the `agnetic-*` glob).

## Patterns to reuse

1. **A systemd unit has four deployment touchpoints: ship payload (build-deb),
   register (enable), lifecycle (start/restart/prerm), and cleanup (uninstall/postrm).**
   Adding a unit file to `systemd/` does nothing until all four are wired. Check them
   as a set whenever a unit is added or audited.
2. **Unit + backing script must ship together.** A packaged unit whose `ExecStart`
   script isn't packaged fails at first start (same failure class as ASP-16's path fix).
3. **Put critical payloads in `build-deb.sh`'s required-path validation list** — the
   validator turns silent omissions into hard build failures.
4. **Non-`agnetic-*` unit names need explicit removal lines** — globs like
   `rm -f /etc/systemd/system/agnetic-*` won't catch `starship-*`.
5. `dpkg-deb` on this host fails under Paperclip's `LD_LIBRARY_PATH` (embedded-postgres
   liblzma lacks `XZ_5.4`); run builds/inspections with `env -u LD_LIBRARY_PATH`.

## Verification

- `bash -n` clean on all five edited scripts
- `bash scripts/build-deb.sh` → "Layout validation OK" (with new required paths)
- `dpkg-deb -c dist/starship-os_2.2.0_amd64.deb | grep health-checker` → unit + script present
- Extracted unit byte-identical to `systemd/starship-health-checker.service`

## Related

- `docs/plans/ASP-190-health-checker-unit-deployment.md`
- `docs/solutions/asp-16-health-checker-path.md` (canonical ExecStart paths)
- `docs/solutions/asp-11-12-13-deb-upgrade-paths.md` (deb upgrade lifecycle)
- Open observations: pre-existing `control` missing `Description:` field (dpkg warning);
  stale `src/python/lib/scripts/{install-daemon,build-deb}.sh` duplicates still target
  the removed `installed/` layout — candidates for the stale-tree cleanup track.
