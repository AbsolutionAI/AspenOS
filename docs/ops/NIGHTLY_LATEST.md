# Nightly latest

- Timestamp (UTC): 2026-11-26T09:03:38Z
- Git SHA: 103ca5b
- Verdict: PASS
- check-nightly: 160/160
- Deviations: check-nightly total is 160 instead of the documented 159 — the C11 p50 gate is now passing (was 1 known hardware deviation in baseline), and `scripts/c11-bench-modes.sh` was added (+1 shell script, total 46 vs baseline 45). Python suite measured 576 passed, 0 failures, 0 skipped, 2 deprecation warnings (vs. baseline 500 passed/4 skipped) — the net +76 comes from accumulated unit test additions and optional dependencies now being installed (`aiohttp`, `nats-py`, Hermes plugin present) so those tests run and pass instead of skipping. No baseline regressions, no new defects. Static inventory matched on every row: 8 systemd unit files (per tree), 8 cgroup drop-in dirs (per tree), `debian/DEBIAN/` 4 files, `scripts/update.sh` present and executable, 6 Windows packaging artifacts, VERSION 2.2.0 == control 2.2.0, 46 shell scripts, nats-server v2.14.5. Smoke suite: 62 passed / 0 failed.
- Issue: ASP-970