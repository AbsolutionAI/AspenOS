# ASP-512: Automated Nightly Packaging & Deployment Check

## Problem
Aspen OS had no automated nightly check. Packaging drift, broken builds, stale units, and deployment path regressions were only caught ad-hoc via manual audits (ASP-10, ASP-187, ASP-477). The ops doc referenced by historical solutions (`NIGHTLY_PACKAGING_DEPLOY_CHECK.md`) was missing from disk entirely.

## Solution
Three files delivered:

1. **`scripts/check-nightly.sh`** — A self-contained bash script with 8 sections covering Go, Rust, C11 builds, the 83-check smoke suite, Debian packaging with layout + size validation, all 9 systemd units, shell syntax on every `.sh` script, and key file presence. Each check is independent (one failure does not stop the suite). Exit code = number of failures.

2. **`.github/workflows/nightly.yml`** — Scheduled CI workflow at `0 2 * * *` (02:00 UTC daily), also manually triggerable via `workflow_dispatch`. Matches the existing `ci.yml` toolchain setup (Go 1.22, Python 3.12, Rust, libseccomp-dev, NATS server for accounts validation). Includes Rust cache layer to speed up nightly agent rebuilds.

3. **`docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`** — Restored/recreated the missing ops reference doc with section overview, failure semantics, links to historical packaging solutions, and instructions for adding new checks.

## Key decisions
- ISO build excluded (requires root / nested virt for live-build, not feasible in CI)
- Independent checks (no `set -e` in overall workflow so a single failure surfaces all problems in one run)
- Rust cached in GH Actions (agent Cargo.toml + Cargo.lock as cache key)
- Used same NATS server version (v2.14.3) as existing CI to avoid version skew
- Matched tooling versions and install steps from `ci.yml` to keep infra consistent

## Future work
- Add Windows packaging check when a Windows CI runner is available
- Consider adding `schedule` to the existing `ci.yml` as well, or merging nightly checks into a separate file only (done here)