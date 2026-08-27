# Plan: ASP-11 — Fix systemd unit path mismatch (/opt/starship vs /opt/agnetic)

## Spec (required before code)
- **Problem:** systemd units in `systemd/` reference `/opt/starship/...` paths, but
  `src/python/lib/scripts/install-daemon.sh` creates real directories under
  `/opt/agnetic/` and never creates the `/opt/starship` symlink. The deb
  `postinst` and `starship-firstboot.sh` both create `/opt/agnetic ->
  /opt/starship` (legacy alias → canonical real root), so the deb path is
  consistent — but a standalone `install-daemon.sh` run leaves systemd units
  broken (missing `/opt/starship`).
- **Success criteria:**
  1. `install-daemon.sh` installs into the canonical `/opt/starship` root.
  2. `install-daemon.sh` creates the legacy `/opt/agnetic` (and `/etc`, `/var/lib`,
     `/var/log`) alias symlinks exactly like `postinst`/`firstboot`.
  3. systemd units keep referencing `/opt/starship` (already correct).
  4. `bash -n` clean; no firstboot dependency.
- **Plan doc:** docs/plans/ASP-11-systemd-path-alignment.md (this file)
- **Out of scope:** `deploy/` developer units (stale/competing — separate ASP-10
  finding), `/opt/starship-os` health-checker path (separate finding).

## Approach
1. Write this plan first (CE gate).
2. In `install-daemon.sh`:
   - Replace real-dir install targets `/opt/agnetic` → `/opt/starship`,
     `/etc/agnetic` → `/etc/starship`, `/var/lib/agnetic` → `/var/lib/starship`,
     `/var/log/agnetic` → `/var/log/starship` (canonical layout per postinst).
   - Add the legacy alias symlinks right after directory creation
     (`ln -sfn /opt/starship /opt/agnetic`, etc.) mirroring postinst.
3. Verify: `bash -n`; grep confirms no stray `/opt/agnetic` real-dir installs.
4. Commit with Paperclip co-author. No push (GitHub auth follow-up open).

## Files
- `docs/plans/ASP-11-systemd-path-alignment.md` (this file)
- `src/python/lib/scripts/install-daemon.sh`

## Non-goals
- No systemd unit edits (they already use the canonical `/opt/starship`).
- No changes to deb control/postinst/firstboot.
- No push/PR.

## Acceptance
- [x] Plan written before code edits
- [x] `install-daemon.sh` installs to `/opt/starship` with `/opt/agnetic` aliases
- [x] `bash -n` clean
- [x] Working tree clean after commit; ASP-11 disposition recorded

## Disposition (ASP-480 sweep — 2026-08-25)

**Status: Completed.** All acceptance criteria met via the packaging-hygiene forward-port initiative. `install-daemon.sh` installs to `/opt/starship` with `/opt/agnetic` legacy aliases. `bash -n` clean. Implementation confirmed on current branch (69 commits ahead of master).
