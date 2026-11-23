# Nightly latest

- Timestamp (UTC): 2026-11-23T19:46:04Z
- Git SHA: 17db1bc
- Verdict: PASS (1 known failure)
- check-nightly: 158/159
- Deviations: C11 p50 benchmark (known hardware-dependent deviation; ADR 0001 threshold is 2ms, measured ~3.2-3.7ms). Same single known failure as the recorded baseline — 159 checks across 23 sections, 158 pass / 1 known fail. No new deviations. Static inventory matched baseline on every row (16 systemd unit files, 8 cgroup drop-in dirs per tree, `debian/DEBIAN/` 4 files, `scripts/update.sh` executable, 6 Windows packaging artifacts, VERSION 2.2.0 == control 2.2.0, 45 shell scripts, nats-server v2.14.5). Python suite: 576 passed / 1 skipped (Hermes holographic plugin absent, same optional-dep pattern as the 4 known skips), 0 failures. Three test fixes applied for aiohttp 3.14.x API drift: `test_server.py` (dead route removed, health endpoint `ok`→`healthy`), `test_sentinel_consumer.py` (`._routes`→`.routes()`), `test_holographic_ingest.py` (skip on broken Hermes plugin).
- Issue: ASP-952

Run from the ASP-952 execution worktree at `origin/master` (17db1bc, docs(security): land H-024 IEC 62443-4-2 cell assessment with ADR-0012 update). Toolchain: go1.26.0, cargo 1.93.1, gcc 15.2.0 + libseccomp, Python 3.14.4, pytest 9.1.1, nats-server v2.14.5. Per-suite: smoke 61 passed / 1 failed (C11 p50), 62 total; python 576 passed, 1 skipped, 0 failures. Lock was free before the run. ISO/deb image builds remain SKIP by design on this host (`ISO_BUILDER.md`, Option B); static checks only. Overwritten in place — do not add `docs/ops/nightly-results-*.md`.