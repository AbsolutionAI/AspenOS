# ASP-543: Nightly Check Improvements — Iteration 6

## Summary

Sixth maintenance iteration of the nightly packaging & deployment check.
Added three new coverage sections: Python test suite (Section 13), ISO build
structure (Section 14), Dashboard static assets (Section 15).

## Changes

| Change | Files | Rationale |
|--------|-------|-----------|
| Python test suite (Section 13) | `scripts/check-nightly.sh` | Python test suite (152+ tests) was recorded manually in results doc; now automated with pass count floor (>=150) and failure detection |
| ISO build structure (Section 14) | `scripts/check-nightly.sh` | ISO build is SKIP in CI (needs root), but source tree was unchecked. Added static inventory: 3 autoinstall YAMLs, chroot hooks, package lists |
| Dashboard static assets (Section 15) | `scripts/check-nightly.sh` | C2 dashboard depends on 8 JS/CSS files; missing asset causes silent UI failure. Added presence check for all known files |
| Baseline doc refresh | `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` | Added sections 13/14/15 to all tables, updated check counts (81 → 101), noted ISO structure now statically checked |

## Result

After changes: **100 passed, 1 failed** (101 total checks).

Known failure: C11 p50 benchmark deviation — hardware-dependent, ~3.451ms vs 2ms threshold per ADR 0001. Not actionable on this control-plane host.

## What was learned

- The POSIX test (`-f`) for file presence requires exact paths. The ISO autoinstall
  profiles are flat files (`user-data.edge.yaml`), not per-profile subdirectories —
  the initial plan assumed subdirectory layout, corrected during implementation.
- `grep -q 'error'` in pytest output is too broad: test method names like
  `test_cli_errors_return_2` contain the substring "error" and trigger false
  positives. Use `grep -q 'FAILED'` instead for pytest failure detection.
- Python test suite runs 152+3 (3 skipped for optional deps: aiohttp, mcp.server).
  The pytest pass-count check (>=150) is confirmed stable.
- Dashboard static directory has exactly 8 files matching the mature C2 UI layout;
  no new files have been added.