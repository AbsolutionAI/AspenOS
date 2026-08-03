# Plan: ASP-13 — Implement update mechanism for aspen-os deb packages

## Spec (required before code)
- **Problem:** No APT repo, no OTA support, no version upgrade script. The deb
  maintainer scripts mishandle upgrades: `prerm` stops/disables services on any
  removal (including `upgrade`), `postrm`'s destructive cleanup is gated only on
  `remove|purge` (safe on upgrade), and `postinst` has no version comparison or
  config migration. Running `dpkg --install` to upgrade therefore tears down
  services, users, venv, and data.
- **Success criteria:**
  1. `prerm` handles `upgrade`/`failed-upgrade` without stopping/disabling services.
  2. `postrm` keeps the `upgrade`/`failed-upgrade` cases non-destructive (already present; verified).
  3. `postinst` compares old vs new version on upgrade and performs config migration + service restart.
  4. `scripts/update.sh` downloads/installs a newer `.deb`, backs up config, and verifies services.
- **Plan doc:** docs/plans/ASP-13-deb-update-mechanism.md (this file)
- **Out of scope:** APT repo hosting, GPG signing, OTA infrastructure, ISO.

## Approach
1. Write this plan first (CE gate — no code before plan).
2. Edit `debian/DEBIAN/prerm` — add `upgrade|failed-upgrade` case that skips
   stop/disable (new postinst restarts services after unpack).
3. Edit `debian/DEBIAN/postinst` — add `configure`-with-prev-version branch:
   - version compare (old != new) → backup `etc/starship` user config
   - `systemctl daemon-reload` + re-enable units (idempotent)
   - restart services when upgrading (not on fresh install)
4. Create `scripts/update.sh` — bash updater following existing script style:
   - detect installed version (`dpkg-query -W -f='${Version}' starship-os`)
   - accept `.deb` path/URL, back up `/etc/starship`, `dpkg -i`, verify `dpkg -s` and service status.
5. Verify: `bash -n` on edited scripts; `dpkg-deb --build` smoke if toolchain allows.
6. Commit with Paperclip co-author. No push (GitHub auth is an open follow-up).

## Files
- `docs/plans/ASP-13-deb-update-mechanism.md` (this file)
- `debian/DEBIAN/prerm`
- `debian/DEBIAN/postinst`
- `debian/DEBIAN/postrm` (verify only)
- `scripts/update.sh` (new)

## Non-goals
- No APT repo / GPG / OTA.
- No changes to ISO or runtime agent code.
- No push/PR (open `[ ] GitHub auth` follow-up owned by aspen).

## Acceptance
- [ ] Plan written before code edits
- [ ] `prerm` upgrade case skips stop/disable
- [ ] `postinst` version comparison + config backup + service restart on upgrade
- [ ] `scripts/update.sh` present and `bash -n` clean
- [ ] Working tree clean after commit; sweep issue updated
