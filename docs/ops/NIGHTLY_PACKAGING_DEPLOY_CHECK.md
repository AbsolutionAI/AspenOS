# Nightly Packaging & Deployment Check

**Source:** `.github/workflows/nightly.yml`  
**Script:** `scripts/check-nightly.sh`  
**Schedule:** Daily at 02:00 UTC (`0 2 * * *`)  
**Manual trigger:** Yes, via `workflow_dispatch` in GitHub Actions

## What gets checked

The nightly check runs in 8 sections:

| Section | Checks |
|---------|--------|
| 1. Go build | `make build`, `starshipctl version` |
| 2. Rust build | `cargo build --release` for staragent |
| 3. C11 components | sandbox_spike, policyexec, starshipd, heald |
| 4. Smoke tests | Full 83-check suite via `scripts/smoke-test.sh` |
| 5. Debian package | `scripts/build-deb.sh`, package size > 1MB |
| 6. Systemd units | All 9 canonical units exist on disk |
| 7. Shell syntax | `bash -n` on every `scripts/*.sh` |
| 8. Key file presence | VERSION, Makefile, configs, NATS configs, pins.json |

## Failure handling

- Each check is independent: a single failure does not halt the suite
- The exit code equals the number of failed checks (0 = all passed)
- The full run log is visible in GitHub Actions under the nightly workflow

## What is NOT checked

- ISO build (requires root / nested virt, not feasible in CI)
- Windows packaging
- Performance benchmarks (use `make bench`)
- Integration tests against real NATS mesh

## Previous findings from manual audits

See `docs/solutions/` for historical packaging issues:
- `asp-11-12-13-deb-upgrade-paths.md` — Debian upgrade safety
- `asp-15-install-systemd-path.md` — Stale systemd path
- `asp-16-health-checker-path.md` — Health checker path fix
- `asp-18-canonical-repo-urls.md` — GitHub URL hygiene
- `asp-190-health-checker-unit-deployment.md` — Health checker unit packaging
- `asp-192-deploy-stale-units.md` — Stale units cleanup
- `asp-478-c11-kernel7-allowlist.md` — C11 seccomp allowlist drift

## Adding new checks

Edit `scripts/check-nightly.sh` and add a `check "description" command-to-run` line in the appropriate section, or create a new section.