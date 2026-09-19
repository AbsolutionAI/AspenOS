# ASP-373: F-009 — Enforce mode 600 on NATS creds & secret paths in packaging

**Status:** READY_FOR_AIDER_QA
**Mode:** IMPLEMENTATION

## Summary

Postinst, firstboot, install, and packaging scripts previously wrote NATS
credentials (`nats-token`, `nats.env`, `staragent.yaml`) as mode 640/644 and
staged `server.conf` (which carries a static dev token) into the .deb payload
world-readable. This change enforces mode **600** on every NATS secret/config
path at every stage — generation, install/upgrade, and package build — with a
fixture test proving the resulting modes without a live install.

## Key insight: consumer ownership at mode 600

Mode 600 is owner-read-only, so the daemons that legitimately read the files
must own them:

- `/etc/starship/nats.env` → **agnetic:agnetic** (fleet/status/dashboard units run
  as `User=agnetic` and load it via `EnvironmentFile=-`)
- `/etc/starship/nats-token` → **root:root** (only firstboot reads it, as root)
- `fleet-accounts.conf` / `fleet-bus.active.conf` / `server.conf` → **nats:nats**
  (the NATS daemon reads the `active.conf` target)
- `creds/*`, `tls/*-key.pem`, `client.env` → **root:root**

This fixes a latent runtime bug too: `fleet-bus.active.conf` was previously
root:root 600 via `umask 077`, which the `nats` user could not read — NATS fell
back to no-auth. Now that file is 600 owned by `nats:nats` so the daemon reads
the token config it must enforce.

## Changes

### New: `scripts/fix-nats-secret-modes.sh`

Idempotent mode-600 enforcer, the single source of truth for the desired modes.
Takes an optional `ROOT` prefix so fixtures and the package staging root can be
locked with the same code (ownership fixes only apply when run as root on the
real system). Called from postinst, firstboot, and build-deb.

### `scripts/starship-firstboot.sh`

- `nats-token`: `chmod 640` → **600**, owner `root:root`.
- `nats.env` (fleet-bus, agent-bus, accounts-bus): `chmod 640/644` → **600**,
  owner `agnetic:agnetic` so agnetic units keep reading it.
- `fleet-bus.active.conf` / `fleet-accounts.conf`: **600**, owner `nats:nats`.
- Runs `fix-nats-secret-modes.sh` after bus selection (idempotent).

### `debian/DEBIAN/postinst`

New Section 4b: calls `fix-nats-secret-modes.sh` (inline fallback if absent) so
upgrades/repairs lock existing installs to 600.

### `scripts/build-deb.sh`

- Stages `fix-nats-secret-modes.sh` into `opt/starship/bin` and
  `opt/starship/lib/starship/scripts`.
- Locks the payload: runs the fixer against `$PKG_ROOT` (so `server.conf` ships
  600, not 644).
- Post-build `dpkg-deb -c` gate: **fails the build** if any NATS secret path in
  the payload is not mode 600 (`mode != 600`).

### `scripts/install-agent-linux.sh` / `scripts/deploy-agent.sh`

- `staragent.yaml` (contains the NATS token): `chmod 644` → **600**.

### `tests/test_nats_secret_modes.py`

Fixture test (no live install): builds a fake `/etc/starship` tree at 644/755,
runs the fixer against it, asserts 600/700. Also greps firstboot/postinst/
build-deb/install-agent to prove 640/644 no longer appear on the secret paths.

### `scripts/check-nightly.sh`

New **Section 18** gates (mirrors Section 17 pattern): firstboot uses 600 and
has no 640/644 on secret paths, postinst hardens, build-deb stages and verifies
600 payload, install-agent writes staragent.yaml 600, fixture tests pass.

## Files changed

| File | Change |
|------|--------|
| `scripts/fix-nats-secret-modes.sh` | New: idempotent 600/700 enforcer + ownership |
| `scripts/starship-firstboot.sh` | 640/644 → 600, owners corrected, fixer call |
| `debian/DEBIAN/postinst` | Section 4b: fixer (or fallback) on install/upgrade |
| `scripts/build-deb.sh` | Stage fixer, lock payload 600, `dpkg-deb -c` gate |
| `scripts/install-agent-linux.sh` | staragent.yaml 644 → 600 |
| `scripts/deploy-agent.sh` | staragent.yaml chmod 600 after write |
| `tests/test_nats_secret_modes.py` | New: fixture + static guard tests |
| `scripts/check-nightly.sh` | +Section 18 gates |
| `docs/plans/ASP-373.md` | Plan document |

## Verification

```bash
# fixture test (no live install needed)
python3 -m pytest tests/test_nats_secret_modes.py -v   # 3 passed

# syntax
bash -n scripts/fix-nats-secret-modes.sh \
       scripts/starship-firstboot.sh \
       scripts/build-deb.sh scripts/install-agent-linux.sh \
       scripts/deploy-agent.sh debian/DEBIAN/postinst
```