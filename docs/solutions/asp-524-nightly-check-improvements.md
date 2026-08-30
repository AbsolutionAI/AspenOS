# ASP-524: Nightly Check Improvements

## Summary

Third maintenance iteration of the nightly packaging & deployment check. The
check was running clean (78/79, known C11 deviation) but had version drift and
coverage gaps.

## Changes

| Change | Files | Rationale |
|--------|-------|-----------|
| nats-server v2.14.3 → v2.14.5 | `.github/workflows/nightly.yml`, `.github/workflows/ci.yml` | Baseline doc and local host already at v2.14.5; CI runners should match |
| Gatekeeper Section 12 | `scripts/check-nightly.sh` | New `src/python/gatekeeper/minimal_shim.py` was unchecked; added file presence + syntax validation |
| Baseline doc refresh | `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` | Merged iso-smoke row into smoke-test row (not a separate make target), added gatekeeper row, updated total to 80+1 |

## Result

After changes: **80 passed, 1 failed** (C11 p50 benchmark — hardware-dependent,
not actionable). Baseline updated to match.

## What was learned

- The `scripts/smoke-test.sh` suite now includes iso-firstboot-smoke checks
  inline. The ops doc's separate `make iso-smoke` row was stale.
- New source modules (e.g., `src/python/gatekeeper/`) should be added to the
  nightly check when introduced, not as an afterthought.
- Workflow NATS versions should be kept in sync with the baseline doc to avoid
  silent drift between CI runners and the reference environment.