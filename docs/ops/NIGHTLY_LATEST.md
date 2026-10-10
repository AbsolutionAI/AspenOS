# Nightly latest

- Timestamp (UTC): 2026-10-10T08:07:08Z
- Git SHA: f179faf0ff4ab259bce5e65e48c5e2bd55c5efa8
- Verdict: PASS
- check-nightly: 158/159
- Deviations: C11 p50 3.654 ms (known hardware deviation; ADR 0001 threshold is 2 ms). Same single known failure as the recorded baseline — 159 checks across 23 sections, 158 pass / 1 known fail. Static inventory matched baseline on every row (8 systemd unit files in `systemd/` + 8 in `dist/pkgroot/` = 16, 8 cgroup drop-in dirs per tree, `debian/DEBIAN/` 4 files, `scripts/update.sh` executable, 6 Windows packaging artifacts, VERSION 2.2.0 == control 2.2.0, 45 shell scripts passing `bash -n`, nats-server v2.14.5). Python suite 500 passed / 4 skipped / 0 failures (baseline row refreshed 495 → 500). No regressions.
- Issue: ASP-760

Run from base `origin/master` (f179faf, holographic read-back test fix, PR #57) — the worktree was clean at checkout and clean after the run, so the recorded SHA is the checked tree. Delta since the prior record (44eb3c8, ASP-728) is CI/nightly infra and test fixes: branch-protection deviation doc (ASP-732), the ASP-728 nightly record, a merge keeping both CI jobs, and two test fixes; no packaging surface moved. Toolchain: go1.26.0, cargo 1.93.1, gcc 15.2.0 + libseccomp, Python 3.14.4, pytest 9.1.1, nats-server v2.14.5. Per-suite: smoke 61 passed / 1 failed (C11 p50 3.654 ms), 62 total; python 500 passed, 4 skipped, 0 failures — the same four absent optional dependencies (`aiohttp`, `mcp.server`, `nats-py`, and the Hermes holographic plugin missing `ruamel`), so the ASP-706 skip-on-ImportError fix is still holding. Lock was free before the run, so exit code 1 (1 failure) is a real check count, not exit-75 contention. ISO/deb image builds remain SKIP by design on this host (`ISO_BUILDER.md`, Option B); static checks only. Overwritten in place — do not add `docs/ops/nightly-results-*.md`.
