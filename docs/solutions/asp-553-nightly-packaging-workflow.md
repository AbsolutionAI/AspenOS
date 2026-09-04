# ASP-553: Nightly Packaging & Deployment Check Workflow

## Problem

Nightly check scripts (`scripts/check-nightly.sh`) and runbook (`docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`) were complete but gated behind manual execution — no automated GitHub Actions schedule existed. Each run required human invocation, creating regression gaps for binary builds, debian packages, systemd units, shell scripts, Python tests, ISO structure, dashboard assets, and Windows packaging.

## Solution

Created `.github/workflows/nightly.yml` — a GitHub Actions workflow modeled on the `smoke` job in `ci.yml`:

- **Trigger:** `schedule` (cron `0 2 * * *`) + `workflow_dispatch` for manual runs
- **Toolchain:** Go 1.22, Python 3.12, Rust stable, libseccomp-dev, gcc, pkg-config
- **Pre-build:** Go CLI (`make build`) + all C11 components (sandbox_spike, policyexec, starshipd, heald) before checks so the smoke tests have binaries to test
- **Sibling repos:** Pinned clones of `aspen-edge-rrm` and `aspen-swarm-manager` from `third_party/pins.json` for fleet-bus smoke
- **NATS tooling:** nats-server v2.14.5 for accounts validation + nkeys/nk for NATS credential ops
- **Check runner:** `bash scripts/check-nightly.sh` with explicit PATH including starshipctl, Go bin, and cargo bin

## Key Design Decisions

1. **Pre-build before check** — The check script tests binary artifacts (smoke tests, version commands), so they must exist. The previous manual workflow assumed pre-built binaries.
2. **No Rust cache** — Unlike `ci.yml` which uses `actions/cache` for Rust, the nightly workflow omits it. The nightly runs once daily and the rust build is fast enough without cache overhead.
3. **Expanded pip deps** — `pytest pytest-asyncio aiohttp httpx mcp` added to support the section 13 Python test suite checks beyond what ci.yml smoke needs.
4. **Explicit PATH** — Added both `env:PATH` and inline `export PATH` to ensure all toolchains (Go, Rust, starshipctl) are discoverable. Missing PATH was a common CI failure mode.

## Out of Scope

- ISO/deb build from source in CI (Option B per `docs/ops/ISO_BUILDER.md`)
- Changes to `scripts/check-nightly.sh` content (already stable at ~101 checks)
- Docker image build or performance benchmarks
- Integration tests against a real NATS mesh

## Verification

- `python3 -c "import yaml; yaml.safe_load(...)"` confirms YAML validity
- `bash -n scripts/check-nightly.sh` confirms shell syntax
- Workflow live at `.github/workflows/nightly.yml` triggers daily at 02:00 UTC and on demand via GitHub UI