# Nightly latest

- Timestamp (UTC): 2026-11-28T09:01:59Z
- Git SHA: 103ca5b
- Verdict: PASS
- check-nightly: 160/160
- Deviations: None. The previously known C11 p50 benchmark deviation cleared this run (all 62 smoke tests passed, including check 53). Total check count grew from 159 to 160 — investigate whether a new check was added. Static inventory matched baseline on every row (8 systemd unit files in both `systemd/` and `dist/pkgroot/lib/systemd/system/`; `debian/DEBIAN/` 4 files with Version 2.2.0; `scripts/update.sh` present and executable; 6 Windows packaging artifacts; VERSION 2.2.0 == control 2.2.0; 45 shell scripts all pass `bash -n`; nats-server v2.14.5). Python suite passed with 500+ tests, 0 failures, same 4 optional-dependency skips. No baseline drift, no new deviations.
- Issue: ASP-990

Run from the ASP-990 execution worktree at `origin/master` (103ca5b). Toolchain: go1.26.0, cargo 1.93.1, gcc 15.2.0 + libseccomp, Python 3.14.4, pytest 9.1.1, nats-server v2.14.5. Per-suite: smoke 62 passed / 0 failed, 62 total (C11 p50 cleared this run). Lock was free before the run (no concurrent holder). ISO/deb image builds remain SKIP by design on this host (`ISO_BUILDER.md`, Option B); static checks only. Overwritten in place — do not add `docs/ops/nightly-results-*.md`.