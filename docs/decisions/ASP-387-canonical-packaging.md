# ASP-387 — Canonical packaging implementation

**Status:** Accepted  
**Date:** 2026-08-22  
**Decider:** aspen (Aspen Architect)  
**Branches:** `ox/packaging-hygiene` (canonical) vs `hermes/asp-36-abs-mirror-routing` (packaging duplicates dropped)

## Decision

**`ox/packaging-hygiene` is the single packaging SoR** for ASP-151, ASP-190, ASP-191/120, ASP-192/352, ASP-353.

Parallel packaging commits on `hermes/asp-36-abs-mirror-routing` are **not** merge candidates. That branch retains non-packaging work only (ASP-36 fleet/robotics subjects, ABS mirror routing docs, ASP-118 go toolchain on its base).

## Why ox wins as base

| Capability | ox/packaging-hygiene | hermes packaging tip |
|---|---|---|
| Health-checker lifecycle (deb + install-daemon + enable/start/status) | Full (ASP-190) | Partial (deb ship only, ASP-151) |
| Package layout asserts + smoke check | Yes | Partial |
| Stale `deploy/` unit removal + archive | Yes (ASP-192/352) | No (`deploy/` still present) |
| ISO `/opt/starship` roots | Yes | Yes (equivalent) |
| Ollama pin `OLLAMA_VERSION=0.31.2` | Yes (ASP-120) | No |
| CE plans + compound docs for packaging cluster | Yes | Partial / alternate plan IDs |
| ASP-36 fleet / ABS mirror | No (out of packaging scope) | Yes — keep on hermes branch |

## Per-file winners (material conflicts)

### 1. `debian/DEBIAN/postinst`

| Item | Winner | Rationale |
|---|---|---|
| Enable list includes `starship-fleet` + `starship-health-checker` | Both (identical) | Unit still ships; firstboot enables fleet |
| Upgrade **restart** list | **Hybrid → hermes intent** | ox dropped `starship-fleet` from restart only; that was **not** covered by ASP-352/192 (those archived legacy `deploy/*` units, not `systemd/starship-fleet.service`). Restart must match enable. Applied on canonical branch. |

### 2. `debian/DEBIAN/prerm` / uninstall

| Item | Winner | Rationale |
|---|---|---|
| Stop/disable `starship-fleet` + `starship-health-checker` on remove | **ox** | hermes prerm omitted them; leaves orphans |

### 3. `scripts/build-deb.sh`

| Item | Winner | Rationale |
|---|---|---|
| `PATH` prefix `/tmp/go/bin` | **ox** | Matches host CI / ASP-118 layout |
| Go preflight `command -v go` | **hermes → adopted** | Fail fast before partial assemble |
| `agent-health-checker.py` copy | **hermes hard-copy → adopted** | Soft `\|\| true` is inconsistent with layout assert that already requires the file |

### 4. `iso/config/hooks/0100-agnetic-install.chroot`

| Item | Winner | Rationale |
|---|---|---|
| `/opt/starship` roots + legacy symlinks | Both (equivalent) | ASP-191 / ASP-120 |
| `OLLAMA_VERSION=0.31.2` pin | **ox** | Reproducible ISO; hermes left floating install.sh |

### 5. Installer / smoke / archive

All **ox**: `install-daemon.sh` health-checker wire-up, `uninstall-daemon.sh` cleanup, smoke health-checker check, `archive/deploy-systemd-legacy/`.

## Consolidation actions

1. Land hybrid postinst + build-deb deltas on `ox/packaging-hygiene` (this change set).
2. Drop unpushed duplicate packaging commits on local `hermes/asp-36-abs-mirror-routing` (ASP-353/191/151 tips) so they cannot race ox to master. Keep ASP-36 / ABS mirror commits only.
3. Merge path to `master`: **only** `ox/packaging-hygiene` (after review). Rebase ASP-36 branch onto post-merge master later — do not merge hermes packaging into master.
4. Do not re-open ASP-151/190/191/192/352/353 as open implementation work; they close through the ox branch merge.

## Non-goals

- Not deciding ASP-36 fleet robotics content (stays on hermes ASP-36 branch).
- Not force-pushing remote history beyond dropping local-only unpushed packaging commits.
- Not declaring master green until ox PR is reviewed and merged.

## Verification (decision heartbeat)

- Tip comparison: `git log ox/packaging-hygiene..hermes/asp-36-abs-mirror-routing` packaging SHAs vs ox ASP-190 cluster.
- File diffs on postinst / build-deb / ISO hook as recorded above.
- `starship-fleet.service` still present under `systemd/` on **both** tips — confirms ASP-352 did not retire fleet.
