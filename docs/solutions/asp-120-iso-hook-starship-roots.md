# Learning: ISO chroot hook must provision starship roots with legacy symlinks, pinned downloads

**Ticket:** ASP-120 (duplicate: ASP-191)

## Problem

`iso/config/hooks/0100-agnetic-install.chroot` still provisioned the live/installed
system under legacy roots (`/opt/agnetic`, `/etc/agnetic`, `/var/lib/agnetic`,
`/var/log/agnetic`) while everything downstream — `scripts/build-iso.sh`
staging, systemd unit ExecStart paths, autoinstall user-data — already expects
the canonical `/opt/starship` layout. ISO-installed systems ended up in
dual-directory state that the units could not run from.

## Fix

- Path-for-path migration inside the hook only: create real dirs under
  `/opt/starship/{bin,lib/starship,venv}`, `/etc/starship/nats`,
  `/var/lib/starship/{nats,message-history}`, `/var/log/starship`.
- Added the five legacy compat symlinks (`/opt/agnetic → /opt/starship`, plus
  `lib/agnetic`, `/etc`, `/var/lib`, `/var/log`), mirroring
  `scripts/install-daemon.sh` §"Transitional Alpha 2.1 dual-root" — the
  convention shared by every installer path (ASP-11/12/13, ASP-15).
- Kept user/group names (`agnetic`, `nats`) — systemd units reference them.
- Pinned downloads for reproducible ISO builds: nats-server `NATS_VERSION=2.14.3`
  (was already pinned) and Ollama via the installer's native
  `curl … | OLLAMA_VERSION="0.31.2" sh` env hook — same install.sh flow and
  semantics as before, just versioned.

## Patterns to reuse

1. **Any installer path (ISO hook, deb postinst, install-daemon.sh, autoinstall)
   must create real dirs under `/opt/starship` + friends and add the five
   legacy `agnetic` symlinks**, never write into legacy dirs directly.
2. **The env prefix must sit on the consumer side of a pipe**: correct form is
   `curl … install.sh | OLLAMA_VERSION=x.y.z sh`; putting it on `curl` sets the
   var only for curl, and the installer runs unpinned.
3. **Pin third-party downloads in image-building hooks** (`OLLAMA_VERSION`,
   `NATS_VERSION`) so ISO builds are reproducible; use upstream's own env hooks
   rather than switching to raw release-artifact downloads.

## Verification

- `sh -n iso/config/hooks/0100-agnetic-install.chroot` clean
- grep: no real-dir creation under legacy paths; symlink lines only
- Cross-checked against systemd unit ExecStart/ReadWritePaths and
  `scripts/build-iso.sh` includes.chroot staging

## Related

- `docs/plans/ASP-120-iso-hook-chroot-starship-migration.md`
- `docs/solutions/asp-15-install-systemd-path.md`,
  `docs/solutions/asp-11-12-13-deb-upgrade-paths.md`
