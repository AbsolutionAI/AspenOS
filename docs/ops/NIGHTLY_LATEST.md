# Nightly latest

- Timestamp (UTC): 2026-10-09T08:09:00Z
- Git SHA: f179faf0ff4ab259bce5e65e48c5e2bd55c5efa8
- Verdict: PASS
- check-nightly: 158/159
- Deviations: C11 p50 3.635 ms (known hardware deviation; ADR 0001 threshold is 2 ms). Same single known failure as the recorded baseline — 159 checks across 23 sections, 158 pass / 1 known fail. Static inventory matched baseline on every row (16 systemd unit files, 8 cgroup drop-in dirs per tree, `debian/DEBIAN/` 4 files, `scripts/update.sh` executable, 6 Windows packaging artifacts, VERSION 2.2.0 == control 2.2.0, 45 shell scripts, nats-server v2.14.5). No baseline drift, no new deviations.
- Issue: ASP-756

Run from base `origin/master` (f179faf, ASP-753 daily implementation sweep merge plus the holographic read-back test fix), which is also the recorded git SHA — the worktree was clean at checkout and after the run. The previous merged live record (2b1175f, ASP-728) was at 44eb3c8; the delta since then covers the ASP-730 CI full-suite gate, the ASP-684 NATS TLS-by-default gate, the ASP-753 sweep, and f179faf, so the CI/packaging surface moved under the checks and every step stayed green on the new baseline. Toolchain: go1.26.0, cargo 1.93.1, gcc 15.2.0 + libseccomp, Python 3.14.4, pytest 9.1.1, nats-server v2.14.5. Per-suite: check-nightly 158 pass / 1 fail of 159 in 49.3 s; smoke suite 61 passed / 1 failed (C11 p50) of 62; python 500 passed, 4 skipped, 0 failures — the same four absent optional dependencies (`aiohttp`, `mcp.server`, `nats-py`, and the Hermes holographic plugin missing `ruamel`), so the ASP-706 skip-on-ImportError fix is still holding. Lock was free before the run, so exit code 1 (1 failure) is a real check count, not exit-75 contention. ISO/deb image builds remain SKIP by design on this host (`ISO_BUILDER.md`, Option B); static checks only. Overwritten in place — do not add `docs/ops/nightly-results-*.md`.
