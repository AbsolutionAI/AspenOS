# Nightly latest

- Timestamp (UTC): 2026-09-26T18:20:00Z
- Git SHA: 0ab00d9d574c7175cc26e5cb6374630a98448460
- Verdict: PASS
- check-nightly: 149/150
- Deviations: C11 p50 3.651 ms (known hardware deviation; ADR 0001 threshold is 2 ms). Same single known failure as the prior consecutive nightlies.
- Issue: ASP-656

Seeded by ASP-663 from `docs/ops/nightly-results-2026-09-26T12-20.md` (12:20 MDT). This wake did not re-run `scripts/check-nightly.sh`. The next nightly overwrites this file in place. Do not add `docs/ops/nightly-results-*.md`.
