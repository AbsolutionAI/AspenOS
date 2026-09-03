# ASP-549: Nightly Packaging & Deployment Check

## Problem

The nightly packaging & deployment check needs to run daily on the control plane host,
verifying builds, smoke tests, static inventory, and toolchain health. Results must be
recorded with a clear PASS/FAIL verdict and any baseline deviations.

## Solution

Rerun the existing 15-section check (`scripts/check-nightly.sh`), record results, and
update the baseline ops doc if any counts shifted.

## Key findings

- **Shell syntax count stabilized at 35:** The ASP-546 fix (including `packaging/*.sh`
  in the shell syntax loop) corrected the count from 34 to 35. Previously the baseline
  claimed 34 scripts (33 scripts/ + 1 packaging/), but the `scripts/` dir actually had
  34 scripts. Now the count is 35 (34 scripts/ + 1 packaging/). Updated baseline.
- **C11 p50 benchmark (~3.451ms):** Remains the single known hardware-dependent failure.
  Not actionable on this host.

## Procedure

1. Run `bash scripts/check-nightly.sh`
2. Record pass/fail per section
3. Compare against baseline doc; update baseline if counts changed
4. Write results doc and compound learning
5. Commit plan, results, and any baseline corrections

## Verdict

PASS (101 passed, 1 known failure) — all builds, tests, and static inventory checks pass.
The single failure is the C11 p50 benchmark, hardware-dependent and not actionable.

## Files

| File | Purpose |
|------|---------|
| `docs/plans/ASP-549.md` | Plan |
| `docs/nightly-check-results-2026-09-03.md` | Results |
| `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` | Runbook with updated shell syntax count |
| `docs/solutions/asp-549-nightly-check.md` | Compound learning (this file) |