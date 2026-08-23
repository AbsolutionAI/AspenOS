# ASP-356 Nightly Packaging & Deployment Check

- Host: BT-ASP-SRV
- Time: 2026-08-22T20:53:00-06:00 (MDT)
- Repo: `/home/tech/projects/aspen-dev/repos/aspen-os`
- Git: `f39f90d` branch=`master` (dirty tree present; latest commit 2026-08-08 ASP-118)
- Remote: `https://github.com/AbsolutionAI/AspenOS.git`
- Routine: Nightly Packaging & Deployment check (`0 22 * * *` UTC) → packndeploy
- Run context: recovery after `workspace_validation_failed` (packndeploy fallback agent-home cwd was empty/non-git)

## Verdict

**Packaging surface is present and coherent; host is not an ISO builder and `make smoke` is red (3 fails).**  
No packaging tree corruption. Autoinstall profiles, debian control, systemd unit set, update/install scripts, and Windows agent packaging are in place. Follow-ups filed for smoke + builder toolchain.

| Area | Status |
|------|--------|
| Project workspace git root | OK (`cwd` = repo git root) |
| Workspace `repoUrl` | Fixed this run → AspenOS.git (was stale starship-os.git) |
| ISO / autoinstall profiles | OK (edge, server, ops + README) |
| Debian package metadata | OK |
| Repo systemd / deploy units | OK (9 systemd + 5 deploy) |
| Update mechanism | OK (`scripts/update.sh`, install/deploy/deb/iso scripts) |
| `starshipctl` build | OK |
| `make smoke` | FAIL 54 pass / 3 fail |
| Host starship systemd install | Not installed (hermes-webui only) |
| ISO/DEB artifacts on disk | None (expected until builder run) |
| ISO builder tools | MISS live-build; qemu-system missing; nats-server missing |

## Findings

### Fixed this run

1. **Workspace validation root cause (prior failure):** Issue expected project workspace; packndeploy resolved to empty agent home  
   `/home/tech/.paperclip/instances/default/workspaces/ef88bbe1-5365-4c3b-b2e5-c2e4a54cf3a3` (no `.git`).  
   Primary project workspace `5749f1ce-…` already points at git root; **`repoUrl` aligned** to live origin AspenOS.git.
2. Nightly check executed with evidence in this document + Paperclip comments.

### WARN — action recommended

1. **`make smoke` 3 failures**
   - `FAIL gen accounts conf valid` — `nats-server: command not found` (accounts conf generation needs binary on PATH)
   - `FAIL C11 sandbox has seccomp`
   - `FAIL C11 p50 under 2ms` (likely host load / sandbox perf gate)
2. **ISO builder toolchain incomplete on BT-ASP-SRV**
   - Missing: `nats-server`, `live-build` (`lb`), `qemu-system-x86_64`
   - Present: go 1.26, rustc/cargo 1.93, docker 29.7, dpkg-buildpackage, python3, make
   - Decision needed: install builder deps here **or** designate a separate ISO builder host and keep this node control-plane only.

### INFO — expected / non-blocking on control plane

- No `starship`/`agnetic` systemd units installed or running (only `hermes-webui.service` enabled).
- No built `.iso` / `.deb` artifacts in tree.
- Paperclip + embedded Postgres running; staragent/nats-server processes not running as host daemons.

## Inventory (evidence)

### Toolchain

| Tool | Status |
|------|--------|
| go | OK 1.26.0 |
| rustc / cargo | OK 1.93.1 |
| python3 | OK 3.14.4 |
| make | OK 4.4.1 |
| dpkg-buildpackage | OK 1.23.7 |
| docker | OK 29.7.2 |
| ollama | OK 0.32.11 |
| curl / jq | OK |
| nats-server | MISS |
| live-build | MISS |
| qemu-system-x86_64 | MISS |
| podman | MISS (docker present) |

### Trees

- **iso/** autoinstall: `user-data.edge.yaml`, `user-data.server.yaml`, `user-data.ops.yaml`, README; live-build hooks + package-lists
- **packaging/**: `install-starship.sh`, `windows/*` (staragent.exe + install/uninstall), `iso` → `../iso`, `systemd` → `../systemd`
- **debian/DEBIAN/**: control, postinst, postrm, prerm
- **systemd/**: agnetic-agent@, dashboard, message-history, nats, staragent, status-bridge, starship-fleet, starship-health-checker, agnetic-mesh.target
- **deploy/**: dashboard target/web, agent@, status-bridge, agent-mesh target
- **scripts/** update path: `update.sh`, `install-daemon.sh`, `install-systemd.sh`, `build-deb.sh`, `build-iso.sh`, `deploy-agent.sh`, iso smoke scripts

### Makefile targets present

`build`, `build-agent`, `smoke`, `iso-smoke`, `iso-boot`, `iso`, `deb`, `install`, `cli`, c11 sandbox targets

### Update mechanism

- Primary: `scripts/update.sh`
- Related plan/solution docs: `docs/plans/ASP-13-deb-update-mechanism.md`, `docs/solutions/asp-11-12-13-deb-upgrade-paths.md`
- ISO testing: `docs/ISO_TESTING.md`

## Workspace / routine hygiene

| Item | Value |
|------|--------|
| Project | AspenOS `2f2b9b10-cfc4-423a-8d6f-ea8e54303b7f` |
| Workspace | `5749f1ce-ecf5-4156-bce9-687182cd11ef` aspen-os primary |
| cwd | `/home/tech/projects/aspen-dev/repos/aspen-os` (git root) |
| repoUrl | `https://github.com/AbsolutionAI/AspenOS.git` (corrected 2026-08-23) |
| Routine assignee | packndeploy `ef88bbe1-5365-4c3b-b2e5-c2e4a54cf3a3` |
| Schedule | `0 22 * * *` UTC |

**Guardrail:** hermes_local must not fall back to empty agent-home workspaces for project-linked routine issues. If validation fails again, re-check project primary cwd is a git root before retry storms.

## Follow-ups

1. Fix smoke reds: install/path `nats-server`; investigate C11 seccomp + p50 gate (packndeploy / runtime).
2. Decide ISO builder host; install live-build + qemu **or** document non-builder role for BT-ASP-SRV.
3. Optional later: install starship systemd units on lab edge nodes (not required on Paperclip control plane).

## Probe commands (re-run)

```bash
cd /home/tech/projects/aspen-dev/repos/aspen-os
git rev-parse --short HEAD && git remote get-url origin
make smoke
test -d .git && echo git_root_ok
ls iso/autoinstall systemd packaging/windows scripts/update.sh
```
