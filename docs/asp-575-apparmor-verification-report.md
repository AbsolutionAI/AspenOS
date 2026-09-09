# AppArmor Profile Verification Report — ASP-575 (H-014)

**Date:** 2026-09-08
**Author:** Aspen Implementation Engineer (agent `8bcaadab`)
**Mode:** VERIFY-ONLY — no profile install, no `aa-enforce`, no CHG, no sudo.

## 1. Inventory: repo (source) vs host (loaded)

### 1.1 Profiles present in source

| Profile | File | Attachment path | Notes |
|---------|------|-----------------|-------|
| agnetic-agent | `security/apparmor/agnetic-agent` | `/opt/agnetic/bin/*` | Legacy 1.x path; resolves to `/opt/starship/bin/*` only via symlink `/opt/agnetic → /opt/starship` created by the installers |
| nats | `security/apparmor/nats` | `/usr/local/bin/nats-server` | Matches ISO hook install path (`nats-server-v*-linux-amd64` → `/usr/local/bin/`), but nats-server here lives at `~/.local/bin/nats-server` |
| ollama | `security/apparmor/ollama` | `/usr/bin/ollama` | **Mismatch**: ISO hook and this host install ollama at `/usr/local/bin/ollama`. Profile will NOT attach. |

Installer: `scripts/install-apparmor.sh` (copies → `/etc/apparmor.d/`, runs
`apparmor_parser -r`, then `aa-enforce`; requires root; standalone only).

### 1.2 Host state (this sandbox host, checked 2026-09-08)

| Check | Result |
|-------|--------|
| AppArmor kernel | **Enabled** (`/sys/module/apparmor/parameters/enabled` = `Y`) |
| `aa-status` / `apparmor_parser` | Present (`/usr/sbin/aa-status`, `/usr/sbin/apparmor_parser`) |
| AppArmor service | `active` |
| Loaded profiles total | 309 (Ubuntu default + GUI/app profiles) |
| `agnetic-agent` loaded? | **ABSENT** |
| `nats` / `nats-server` loaded? | **ABSENT** |
| `ollama` loaded? | **ABSENT** (no `usr.bin.ollama`, no custom profile) |
| Ollama process | **Running unconfined**: `/usr/local/bin/ollama serve` (pid 11167) |
| nats-server process | Not running |
| `/opt/agnetic` `/opt/starship` | **Absent** — host is a dev workstation, not a Starship deployment target |

**Loaded/enforce/complain breakdown for the three StarShip profiles on this
host:** all three are in the **absent** set (no profile file in
`/etc/apparmor.d/`, no entry in `/sys/kernel/security/apparmor/policy/profiles/`,
therefore neither enforce nor complain).

### 1.3 Deployment-target wiring (does anything install these profiles?)

| Target | Mechanism | AppArmor wiring |
|--------|-----------|-----------------|
| Manual install | `scripts/install-daemon.sh` | **None.** No reference to `install-apparmor.sh`, `apparmor`, `/etc/apparmor.d` anywhere in the file (341 lines). |
| Debian package | `scripts/build-deb.sh` + `debian/DEBIAN/postinst` | **None.** Profiles never staged into the `.deb` (`etc/apparmor.d/` not created/copied); `postinst` has no AppArmor step. |
| ISO (edge/server/ops) | `iso/config/hooks/0100-agnetic-install.chroot` | **None.** Hook installs Ollama + NATS, creates users/dirs/venv; no `apparmor` package, no profile copy, no parser run. |
| CI / nightly | `.github/workflows/ci.yml`, `nightly.yml`, `scripts/check-nightly.sh` | **None.** No AppArmor section in `check-nightly.sh`; no workflow references profiles. |

`scripts/install-apparmor.sh` appears twice in the tree
(`scripts/` and `src/python/lib/scripts/`) but **nothing invokes it**. Its only
documentation is a manual command: `SECURITY.md:45` and `docs/SECURITY.md:81`.

## 2. Gap analysis vs threat model

### H-014 "Missing AppArmor profiles in deployment" (6.5, AV:L/AC:M)

**CONFIRMED GAP — exactly as suspected.** The threat model's hypothesis was
correct on every point:

- Profiles **exist** in `security/apparmor/` (3 files) ✓
- But **no deployment path installs them**: `install-daemon.sh` doesn't,
  `build-deb.sh`/`postinst` doesn't, the ISO chroot hook doesn't. The "install
  script" that threat model §8 P0#3 names (`install-daemon.sh`) indeed never
  copies or loads the profiles. ✗
- **No verification exists**: `check-nightly.sh` has no AppArmor section;
  CI has no fail-if-missing gate. The recommended "fail the build if profiles
  are present in source but absent from the installed target" is **not
  implemented**. ✗
- Residual on a real deployment today: every StarShip/Ollama/NATS process runs
  **unconfined**, so the H-HOST-01/02 controls (`ProtectSystem`,
  `ProtectHome`, path allowlists) rely solely on systemd + Python-level
  checks.

### H-010 "Stale capability tokens post-expiry" (closed, ASP-564 / ADR-0009)

AppArmor is the **host-layer control that makes H-010 meaningful**: gatekeeper
tokens and NATS credentials live in process memory/env. With agents unconfined,
a compromised agent can `ptrace`/read `/proc` peers and dump those credentials
before / despite token expiry. The shipped profiles explicitly `deny ptrace`,
`capability sys_ptrace`, `capability sys_admin`, `sys_module`, `sys_rawio`,
raw/packet sockets, and writes to `/home`, `/root`, `/etc`, `/var/lib` — the
exact primitives that would turn token theft into persistence/privilege
escalation. **Absence of these profiles widens the H-010 residual risk** (and
H-HOST-01/02/03) on all deployment targets.

### Secondary findings

1. **Path drift breaks `ollama` profile attachment.** Profile attaches
   `/usr/bin/ollama`; the ISO hook and this host install ollama to
   `/usr/local/bin/ollama` (official install script target). On a stock
   deployment the profile would never attach, silently.
2. **`agnetic-agent` profile uses legacy 1.x paths** (`/opt/agnetic`, `/etc/agnetic`).
   These resolve to `/opt/starship`/`/etc/starship` only via symlinks the
   installers create; `docs/SECURITY.md:89` already flags updating to 2.1 paths.
3. **nats profile path matches the ISO install** but not this host's
   `~/.local/bin/nats-server` (dev-only path, out of scope).
4. **No CI/nightly safety net** — a future profile edit that breaks parsing
   (`apparmor_parser -r` silent failure) or a removed profile would ship
   unnoticed. Ubuntu 26.04 host vs documented 24.04 target is noted; profiles
   use `#include <tunables/global>` and standard abstractions so should load on
   both, but this is unverified without loading (out of scope by mandate).

## 3. Non-change declaration

Per Captain 2026-09-08 mandate, no running security policy was altered: no
`aa-enforce`, no `apparmor_parser` load, no `cp` to `/etc/apparmor.d/`, no sudo
apply, no CHG. Verification was read-only (kernel sysfs + repo grep).

## 4. Files / evidence

- Combination of: repo `security/apparmor/*`, `scripts/install-apparmor.sh`,
  `scripts/install-daemon.sh`, `scripts/build-deb.sh`, `debian/DEBIAN/postinst`,
  `iso/config/hooks/0100-agnetic-install.chroot`, `.github/workflows/{ci,nightly}.yml`,
  `scripts/check-nightly.sh`, `docs/SECURITY.md`, `docs/SECURITY_THREAT_MODEL_v2.2.md`.
- Host: `/sys/module/apparmor/parameters/enabled`,
  `/sys/kernel/security/apparmor/policy/profiles/` (309 entries, none
  agnetic/nats/ollama), `aa-status`, `pgrep`.