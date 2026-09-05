# ASP-556: Memory-promote recency time-bomb in nightly check

## Problem

On the 2026-09-05 nightly check run, Section 13 ("no pytest failures") suddenly
broke: 4 tests in `tests/test_memory_promote.py` failed despite no product code
change. The previous run (2026-09-03) had passed the suite cleanly.

## Root cause

`tests/test_memory_promote.py` hardcoded `timestamp="2026-08-06T00:00:00Z"` in its
scoring fixtures. `scripts/memory_promote.py` applies a 30-day recency window
(`_RECENT_WINDOW_DAYS = 30`): any candidate older than 30 days gets
`score *= 0.6`. The fixture date sat *just inside* the window on 09-03, then the
calendar rolled past 30 days overnight, flipping `_is_recent()` from True to False:

| Test | Before (09-03) | After (09-05) |
|------|-----------------|---------------|
| `test_decision_scores_high` | 0.95 | 0.57 (= 0.95 × 0.6) |
| `test_cross_referenced_above_threshold` | 0.85 | 0.51 (< 0.7 threshold) |
| `test_promote_returns_memory_id` | id | `None` (0.57 < 0.7) |
| `test_dry_run_reports_and_promotes_high_confidence` | pass | facts.jsonl never written |

No product regression — the scoring behavior (recency decay) is intentional per
the BEL-154 design. The tests were simply not time-proof.

## Fix

`tests/test_memory_promote.py` now builds "recent" timestamps relative to now:

```python
def recent_ts() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
```

- All scoring/promotion fixtures use `recent_ts()` (1 day in the past, always
  inside the 30-day window).
- `test_old_entries_decay` deliberately keeps `2025-01-01` so it keeps exercising
  the decay path — that one is supposed to be old.
- The ingest fixture's daily filename reuses `recent_ts()[:10]` so the E2E test's
  ingest reads match the promotion timestamps.

## Verification

- `python3 -m pytest tests/test_memory_promote.py -q` → 12 passed
- `python3 -m pytest tests/ -q` → 156 passed, 3 skipped (aiohttp, mcp.server), 0 failures
- `bash scripts/check-nightly.sh` → back to baseline: 101 passed, 1 known failure (C11 p50)

## What was learned

1. **Hardcoded dates in scoring/recency tests are an active time-bomb.** Any test
   that asserts a confidence/score must reference the module's recency window
   relative to "now", or it will flip ~30 days after the fixture date and surface
   as a confusing phantom regression in CI.
2. **Diagnosis shortcut:** when a scoring test fails with a value exactly tied to
   `0.6 ×` a nice number (e.g. 0.57 = 0.95×0.6), suspect the recency/decay path
   rather than the scoring logic itself. Recency scales multiplicatively, so the
   culprit is never a change to the base score — it's the window boundary.
3. **`_is_recent()` (and `_now()`) are injectable seams.** A cleaner long-term fix
   is monkeypatching `memory_promote._now` in test fixtures; the `recent_ts()`
   helper is the lighter-weight approach and keeps fixtures readable.

## Files

| File | Change |
|------|--------|
| `tests/test_memory_promote.py` | Time-relative recency timestamps |
| `docs/nightly-check-results-2026-09-05.md` | Results record |
| `docs/solutions/asp-556-memory-promote-time-bomb.md` | This learning |
| `docs/plans/ASP-556.md` | Plan |