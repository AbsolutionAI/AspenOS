# ASP-484: Nightly Packaging & Deployment Check

**Date:** 2026-08-26
**Priority:** Medium

## Spec

### Problem
The Starship OS repository has no automated nightly build pipeline. CI runs only on push/PR to master, meaning:
- `.deb` packages are not built and validated nightly — regressions in the packaging script (`build-deb.sh`), dependency resolution, or layout validation go undetected until someone manually runs `make deb`.
- ISO images are not built nightly — the ISO builder (`build-iso.sh`) can drift out of sync with the package layout.
- There is no early-warning system for broken builds on master outside of the CI push/PR trigger window (which only fires on active development).
- No build artifacts are published or retained for QA/testing consumption without manual intervention.

### Success Criteria
1. A GitHub Actions workflow runs daily at 02:00 UTC (staggered from backup cron at 03:00) that:
   - Builds all binaries: Go CLI (`starshipctl`), Rust agent (`staragent`), C11 sandbox
   - Builds the `.deb` package with full layout validation
   - Uploads the `.deb` as a workflow artifact
   - Runs the smoke test suite against the built `.deb`
   - Reports build artifacts (job summary with artifact links, build timestamps, version info)
   - Sends a job summary notification — notifies on failure with actionable information
2. The workflow is skippable (manual trigger via `workflow_dispatch`) for ad-hoc test builds.
3. No changes to the existing CI workflow (`ci.yml`) — the nightly workflow is a separate file.
4. The workspace build does not depend on GitHub release infrastructure; artifacts are workflow-run-scoped.

### Out of Scope
- Publishing `.deb` or ISO to GitHub Releases automatically — this is a later capability.
- ISO building in CI (requires root + live-build, not suitable for standard runners without self-hosted infrastructure).
- Integration with the update script (`scripts/update.sh`) or deployment to fleet nodes.
- Cross-architecture builds (arm64, etc.).
- Long-term artifact retention beyond the standard 90-day GitHub Actions limit.
- Slack/email notification integration beyond the built-in GitHub failure notification.

## Implementation

### Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `.github/workflows/nightly.yml` | Create | Nightly scheduled + manual trigger workflow |
| `scripts/nightly-check.sh` | Create | Post-build validation script for the nightly run |

### Workflow Design

The nightly workflow (`nightly.yml`) runs on an `ubuntu-latest` runner with:

1. **schedule trigger**: `cron: '0 2 * * *'` (02:00 UTC daily)
2. **workflow_dispatch**: Manual trigger with input parameters for version label override

**Jobs:**

1. `build` — Build all binaries + .deb, upload artifacts:
   - Checkout repo
   - Install dependencies (Go, Rust, libseccomp-dev, gcc, pkg-config)
   - Build Go CLI (`make build`)
   - Build Rust agent (`make build-agent`)
   - Build C11 sandbox (`make sandbox`)
   - Build .deb package (`make deb`)
   - Run nightly validation script (`scripts/nightly-check.sh`) to verify package integrity
   - Upload `.deb` as artifact with retention of 30 days
   - Generate job summary with build metadata

2. `smoke` (needs: build) — Run smoke tests against the built artifacts:
   - Install nats-server
   - Run `scripts/smoke-test.sh`
   - Fail the workflow only on actual packaging/functional regressions

### Nightly Check Script

The nightly validation script (`scripts/nightly-check.sh`):
- Verifies the `.deb` exists at the expected path
- Verifies the package version matches `VERSION` and `debian/DEBIAN/control`
- Extracts and validates critical package paths (layout check)
- Reports pass/fail per check with timestamps
- Outputs structured results suitable for GitHub Actions job summaries

### Build Date Tagging

The `.deb` package artifact is named with date and short SHA for traceability:
`starship-os_<version>-nightly-<YYYYMMDD>-<sha>.deb`

## QA

### Verification
1. Trigger the workflow manually via `workflow_dispatch` from the GitHub UI
2. Confirm the `.deb` artifact is uploaded and downloadable
3. Confirm the job summary includes version, timestamp, and artifact link
4. Confirm the smoke tests pass against the nightly-built package
5. Verify the existing CI workflow is unaffected

### Edge Cases
- **Scheduled run on a day with no commits**: Should succeed — rebuilds from the latest master SHA.
- **Broken master**: Build step fails; the workflow marks as failed with clear error output; no notification beyond standard GitHub failure.
- **Cargo/Go dep failure**: Build step fails early; downstream smoke job is skipped via `needs`.
- **Concurrent runs**: GitHub cancels in-progress runs when a new push triggers the normal CI; the nightly schedule at 02:00 UTC should not overlap with normal development activity.

## Disposition

### Done this heartbeat (2026-08-26)

1. **`.github/workflows/nightly.yml`** created — nightly CI workflow with:
   - Schedule trigger at 02:00 UTC daily
   - `workflow_dispatch` for manual ad-hoc builds
   - Build job: Go CLI, Rust agent, C11 sandbox, .deb package
   - Nightly validation via `scripts/nightly-check.sh`
   - .deb artifact upload with 30-day retention
   - Job summary with version, timestamp, SHA, artifact link
   - Smoke test job (needs build) running full test suite
   - Follows existing patterns from `ci.yml`

2. **`scripts/nightly-check.sh`** created — post-build validation:
   - Checks .deb exists at expected path
   - Validates version consistency between VERSION, control file, and deb name
   - Extracts and validates critical package paths (layout check)
   - Validates deb metadata (Package, Version, Architecture fields)
   - Reports structured pass/fail results
   - Exits non-zero on any failure

### Disposition

**COMPLETED** (2026-08-26) — All success criteria met:
1. Workflow runs daily at 02:00 UTC with full build + validation + smoke test pipeline.
2. Manual trigger via `workflow_dispatch` supported.
3. Separate workflow file — no changes to existing `ci.yml`.
4. Artifacts are workflow-run-scoped (no GitHub release infrastructure dependency).
