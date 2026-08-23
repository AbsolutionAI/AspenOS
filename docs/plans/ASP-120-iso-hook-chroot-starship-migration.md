# ASP-120 — Migrate ISO hook chroot from /opt/agnetic to /opt/starship

**Status:** implemented (branch `ox/packaging-hygiene`)
**Scope:** Fast Coder (small, low-risk path migration)

## Problem

`iso/config/hooks/0100-agnetic-install.chroot` still provisions the live/installed
system under legacy `/opt/agnetic`, `/etc/agnetic`, `/var/lib/agnetic`,
`/var/log/agnetic`. Everything downstream already expects starship roots:

- `scripts/build-iso.sh` stages `includes.chroot` under `/opt/starship` + `/etc/starship`
- systemd units ExecStart from `/opt/starship/venv/bin/python3` and
  `/opt/starship/lib/starship/...`
- autoinstall user-data profiles create starship dirs with legacy symlinks

## Change

Path-for-path migration inside the hook only (no filename rename; broader
agnetic→starship naming sweep is out of scope):

| Legacy | Canonical |
|---|---|
| `/opt/agnetic/{bin,lib/agnetic,venv}` | `/opt/starship/{bin,lib/starship,venv}` |
| `/etc/agnetic/nats` | `/etc/starship/nats` |
| `/var/lib/agnetic/{nats,message-history}` | `/var/lib/starship/{nats,message-history}` |
| `/var/log/agnetic` | `/var/log/starship` |

Keep: user/group names (`agnetic`, `nats`) — systemd units reference them;
Ollama/NATS install steps untouched.

Add legacy aliases mirroring `scripts/install-daemon.sh` §"Transitional Alpha
2.1 dual-root" (ASP-11/12/13 convention: symlinks in every installer path):
`/opt/agnetic → /opt/starship`, `/opt/starship/lib/agnetic →
/opt/starship/lib/starship`, plus `/etc`, `/var/lib`, `/var/log` equivalents.

Deferred (from issue description): version-pinning the Ollama installer —
switching from `curl … install.sh | sh` to a pinned release artifact changes
install semantics and cannot be verified without a full ISO build; tracked as a
follow-up consideration. nats-server is already pinned (`2.14.3`).

## Verification

- `sh -n` on the hook
- grep shows no real-dir creation under legacy paths; symlink lines only
- Cross-check vs systemd unit ExecStart/ReadWritePaths and autoinstall user-data

## Note

[ASP-191](/ASP/issues/ASP-191) is a duplicate of this issue; a parallel run
applied the equivalent change in the main checkout.
