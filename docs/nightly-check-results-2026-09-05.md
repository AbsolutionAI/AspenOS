# Nightly Check Results — 2026-09-05

**Verdict: PASS (1 known failure)** — after fixing a time-bomb pytest failure introduced overnight.

| Metric | Value |
|--------|-------|
| Passed | 101 |
| Failed | 1 (known C11 p50, hardware-dependent) |
| Total | 102 |
| Time | ~10.4s |

## New finding + fix this run

The first run reported **2 failures**: the known C11 p50 benchmark **and** a new
Section 13 failure — 4 tests in `tests/test_memory_promote.py` began failing.

**Root cause:** time-bomb test fixtures. The tests hardcoded
`timestamp="2026-08-06T00:00:00Z"`, and today (2026-09-05) that date fell exactly
outside `memory_promote`'s 30-day recency window (`_is_recent` → `score *= 0.6`).
Decisions scored 0.95 → 0.57, cross-referenced facts 0.85 → 0.51 (below the 0.7
threshold), and `promote()` began returning `None`.

**Fix:** `tests/test_memory_promote.py` now computes "recent" timestamps relative to
`datetime.now(timezone.utc) - 1d` via a `recent_ts()` helper, so fixtures always
stay inside the recency window. `test_old_entries_decay` intentionally keeps
`2025-01-01` to exercise the decay path. No product code changed — the scoring
logic behavior is per BEL-154 design.

After the fix: `pytest` → **156 passed, 3 skipped (aiohttp / mcp.server), 0 failures**;
full nightly → **101 passed, 1 known failure**.

## Toolchain
- nats-server: v2.14.5 (`$HOME/.local/bin/nats-server`)
- Go: go1.26.0 linux/amd64
- Cargo/Rust: cargo 1.93.1
- gcc: (Ubuntu 15.2.0-16ubuntu1) 15.2.0

## Section-by-section results
| Section | Name | Pass | Fail |
|---------|------|------|------|
| Pre-flight | Toolchain | 3 | 0 |
| 1 | Go build | 2 | 0 |
| 2 | Rust agent build | 1 | 0 |
| 3 | C11 components | 4 | 0 |
| 4 | Smoke tests | 58 | 1 (known C11 p50) |
| 5 | Debian package | 2 | 0 |
| 6 | Systemd units | 9 | 0 |
| 7 | Shell syntax | 35 | 0 |
| 8 | Key file presence | 10 | 0 |
| 9 | Debian metadata | 5 | 0 |
| 10 | Windows packaging | 6 | 0 |
| 11 | Update mechanism | 2 | 0 |
| 12 | Gatekeeper module | 2 | 0 |
| 13 | Python test suite | 4 | 0 |
| 14 | ISO build structure | 8 | 0 |
| 15 | Dashboard static assets | 8 | 0 |

## Baseline deviations from ops doc
- **None** relative to the post-fix baseline: 101 passed, 1 known failure (C11 p50).
- The transient +1 failure observed mid-run was the memory-promote time-bomb,
  resolved in this run (recorded as a learning, see
  `docs/solutions/asp-556-memory-promote-time-bomb.md`).

## Head of tree
- Branch: `master`
- Head: `db3648f` — `docs(compound): ASP-553 nightly packaging workflow learning`
- Version: 2.2.0