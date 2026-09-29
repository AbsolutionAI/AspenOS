# Nightly latest

- Timestamp (UTC): 2026-09-29T02:47:00Z
- Git SHA: e3b1d598024b23abf58bf4ea9d03ddb10c44cdd9
- Verdict: PASS
- check-nightly: 149/150
- Deviations: C11 p50 3.592 ms (known hardware deviation; ADR 0001 threshold is 2 ms). Same single known failure as the prior consecutive nightlies. `make smoke` 61/62, `make iso-smoke` 32/32, Python 470 passed / 4 skipped. All static inventory rows match the baseline table.
- Issue: ASP-675

Overwritten in place per `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` step 6. Do not add
`docs/ops/nightly-results-*.md`.
