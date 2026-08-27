# Learning: Deduplicate systemd unit files across config/ and systemd/

**Ticket:** ASP-353

## Problem

`starship-health-checker.service` existed as two near-identical copies:

- `systemd/starship-health-checker.service` — canonical, installed by `scripts/install-health-checker.sh`
- `config/starship-health-checker.service` — unreferenced copy, only deltas being a longer Description and a `# Security hardening` comment

Two copies drift independently. The ASP-16 path fix had to patch both files because neither was authoritative. The `config/` copy had no installer or packaging references, so only the `systemd/` version actually ran on deployed systems.

## Fix

- Merged the richer Description from `config/` into `systemd/starship-health-checker.service`
- Deleted `config/starship-health-checker.service`
- Verified with `grep` and `find` that only one unit file exists and no runtime references point at the deleted copy

## Patterns to reuse

1. **One canonical source per systemd unit.** If a unit has copies in `config/`, `systemd/`, or `deploy/`, pick one home directory (`systemd/`) and delete the rest. Copy-on-write drift is inevitable.
2. **Every unit must be wired to an installer.** An orphan unit in `config/` with no reference from `build-deb.sh`, `install-daemon.sh`, or `install-health-checker.sh` is dead code. Apply the four-touchpoint rule from ASP-190 (ship, register, lifecycle, cleanup).
3. **When patching a unit, check for duplicates first.** The ASP-16 ExecStart fix had to patch two files. A `find . -name "*.service"` before editing would have caught the copy.

## Verification

- `find . -name "starship-health-checker.service" -not -path "./.git/*"` → exactly one result (`systemd/starship-health-checker.service`)
- `rg "config/starship-health-checker" --no-filename` → no runtime references (historical plan/solution docs keep mentions as decision records)
- Canonical unit in `systemd/` has the merged Description

## Related

- `docs/plans/ASP-353-dedupe-health-checker-service.md`
- `docs/solutions/asp-190-health-checker-unit-deployment.md` (four-touchpoint rule)
- `docs/solutions/asp-16-health-checker-path.md` (the drift that triggered this dedup)
- `docs/solutions/asp-192-deploy-stale-units.md` (parallel cleanup of stale `deploy/` units — same class of problem)
