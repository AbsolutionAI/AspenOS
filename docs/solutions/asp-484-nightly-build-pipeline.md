# Nightly build pipeline — deb validation + smoke (ASP-484)

## Problem

The Starship OS repository had no automated nightly build pipeline. CI ran only on push/PR to master, meaning `.deb` packages and ISO images were not built and validated on a schedule. Packaging regressions in `build-deb.sh`, dependency resolution, or layout validation could go undetected until someone manually ran `make deb`.

## Solution

### Separate nightly workflow file

A new `.github/workflows/nightly.yml` was created alongside the existing `ci.yml`, following the same patterns but with a scheduled trigger:

- **Schedule:** `cron: '0 2 * * *'` (02:00 UTC daily)
- **Manual trigger:** `workflow_dispatch` with optional version label override
- **Concurrency scoping:** `${{ github.workflow }}-${{ github.ref }}` to avoid overlap with normal CI runs

### Two-job pipeline

1. **`build` job** — Builds all binaries (Go CLI, Rust agent, C11 sandbox), builds the `.deb` package, renames it with a nightly tag (`starship-os_<version>-nightly-<YYYYMMDD>-<sha>.deb`), runs validation, uploads as artifact (30-day retention), and generates a job summary with build metadata.

2. **`smoke` job** (needs build) — Downloads the artifact, installs dependencies, and runs the full `scripts/smoke-test.sh` suite. This ensures the nightly artifacts are actually functional.

### Post-build validation script

`scripts/nightly-check.sh` validates the `.deb` package independently of the build process:

- Verifies the `.deb` exists at the expected path
- Checks version consistency between `VERSION`, `debian/DEBIAN/control`, and the deb filename
- Extracts and validates 11 critical package paths (layout check)
- Validates deb metadata (Package, Version, Architecture fields)
- Reports structured pass/fail results suitable for GitHub Actions job summaries
- Exits non-zero on any failure, which fails the workflow

### Key design decisions

1. **Separate workflow file** — No changes to existing `ci.yml`. The nightly workflow is self-contained and can be disabled or modified independently.

2. **No ISO building in CI** — ISO requires root + live-build, not suitable for standard runners. Out of scope per plan.

3. **No GitHub Releases integration** — Artifacts are workflow-run-scoped with standard 30-day retention. Publishing to Releases is a separate capability.

4. **Makefile targets** — `make nightly` (build + validate) and `make nightly-clean` (clean + remove `.deb`s) were added for local testing of the pipeline.

## Usage

- **Automatic:** Runs daily at 02:00 UTC from the default branch.
- **Manual:** Navigate to Actions → "Starship OS Nightly Build" → "Run workflow" → optionally set a version label → "Run workflow".
- **Local:** `make nightly` from the repo root.

## Trade-offs

- **Build duplication:** The `build` job builds Go CLI and Rust agent explicitly, then `make deb` rebuilds them as prerequisites. This is acceptable for a nightly schedule where build time is less critical than correctness.
- **No cross-arch:** Only `amd64` for now. Arm64 and other architectures are out of scope.
- **No notifications:** Failure notifications use GitHub's default workflow failure email. No Slack/email integration yet.