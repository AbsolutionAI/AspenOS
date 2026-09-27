# Nightly latest

- Timestamp (UTC): 2026-09-27T08:05:02Z
- Git SHA: e3b1d598024b23abf58bf4ea9d03ddb10c44cdd9
- Verdict: PASS
- check-nightly: 149/150
- smoke: 61/62 (1 known failure: C11 p50 3.669 ms)
- iso-smoke: 32/32
- Python suite: 466 passed, 4 skipped, 0 failures
- Deviations:
  1. C11 p50 3.669 ms vs the ADR 0001 threshold of 2 ms — known hardware deviation, same single
     known failure as the prior consecutive nightlies, and inside the runbook's documented
     3.2–3.7 ms observed range.
  2. Baseline correction (docs, not a check failure): the `Python test suite` row said
     `470 passed, 4 skipped`. Both the system interpreter and the repo `.venv` report
     `466 passed, 4 skipped` (470 collected). The 2026-09-26 run (2e6819b) had recorded the
     collected total as the pass count. Row corrected to `466 passed, 4 skipped (470 collected)`.
- Issue: ASP-671

The next nightly overwrites this file in place. Do not add `docs/ops/nightly-results-*.md`.
