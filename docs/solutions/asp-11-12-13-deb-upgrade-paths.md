# Learning: Debian package upgrade safety + canonical install root (ASP-11/12/13)

**Date:** 2026-08-03
**Issues:** [ASP-11](/ASP/issues/ASP-11), [ASP-12](/ASP/issues/ASP-12), [ASP-13](/ASP/issues/ASP-13)
**Source:** ASP-10 nightly packaging & deployment audit

## Bug
`dpkg --install` upgrades torn down services/users/venv because the maintainer
scripts treated every invocation like a remove. Systemd units also referenced
`/opt/starship` while `install-daemon.sh` installed into `/opt/agnetic` as a
real dir with no alias — units broke on standalone installs.

## Pattern
- **dpkg maintainer-script args:** `prerm <action> [old-version]`,
  `postinst configure <old-version>`. Always `case "$1"` on `upgrade`,
  `failed-upgrade`, `remove`, `purge` — never run destructive logic
  unconditionally.
- **Upgrade flow:** `prerm upgrade` → leave services running; new files unpack;
  `postinst configure <old-version>` → detect `$2` non-empty = upgrade, back up
  user config, then `systemctl daemon-reload` + restart services.
- **Canonical root:** pick one real install root (`/opt/starship`) and express
  legacy names (`/opt/agnetic`) as symlinks created in *every* installer path
  (postinst, firstboot, standalone installer) — do not let symlink creation
  depend on a single optional step like firstboot.

## Files touched
- `debian/DEBIAN/prerm`, `debian/DEBIAN/postinst`, `debian/DEBIAN/postrm`
- `src/python/lib/scripts/install-daemon.sh`
- `scripts/update.sh` (new — file/URL .deb installer with config backup)

## Verification
- `bash -n` on all edited/new scripts
- `dpkg-deb --build` + `dpkg-deb -e` re-validation of packaged maintainer scripts
- `scripts/update.sh --help`, missing-arg, bad-file error paths
