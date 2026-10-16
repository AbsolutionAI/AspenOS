# Nightly latest

- Timestamp (UTC): 2026-10-16T08:15:49Z
- Git SHA: edbc440
- Verdict: PASS
- check-nightly: 158/159
- Deviations: C11 p50 3.565 ms on a follow-up `scripts/bench-sandbox.sh 100` after the suite failed the same predicate (known hardware deviation; ADR 0001 threshold is 2 ms). Same single known failure as the recorded baseline — 159 checks across 23 sections, 158 pass / 1 known fail. Static inventory matched baseline on every row (8 systemd unit files in `systemd/` plus 8 staged under `dist/pkgroot` = 16, 8 cgroup drop-in dirs, `debian/DEBIAN/` 4 files, `scripts/update.sh` executable, 6 Windows packaging artifacts, VERSION 2.2.0 == control 2.2.0, 45 shell scripts, nats-server v2.14.5). Python suite measured 516 passed / 4 skipped vs. 500 in the ASP-764 baseline — a benign +16 net from added unit tests, 0 failures, same 4 optional-dependency skips (`aiohttp`, `mcp.server`, `nats-py`, Hermes `ruamel`). No baseline drift, no new deviations.
- Issue: ASP-791

Run from the ASP-791 execution worktree at `origin/master` (edbc440, merge of PR #78 / ASP-773 weekly architecture review), which is also the recorded git SHA — the worktree was clean at checkout and the check did not dirty tracked files. Toolchain: go1.26.0, cargo 1.93.1, gcc 15.2.0 + libseccomp, Python 3.14.7, pytest 9.1.1, nats-server v2.14.5. Per-suite: smoke 61 passed / 1 failed (C11 p50), 62 total; python 516 passed, 4 skipped, 0 failures. Script exit 1 is that one known failure, not exit-75 lock contention (lock was free; elapsed 100194 ms). ISO/deb image builds remain SKIP by design on this host (`ISO_BUILDER.md`, Option B); static checks only. Overwritten in place — do not add `docs/ops/nightly-results-*.md`.
