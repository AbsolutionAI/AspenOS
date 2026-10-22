# Nightly latest

- Timestamp (UTC): 2026-10-22T08:03:24Z
- Git SHA: edbc440
- Verdict: PASS
- check-nightly: 158/159
- Deviations: C11 p50 ~3.2-3.7ms (known hardware deviation; ADR 0001 threshold is <2ms). Same single known failure as the recorded baseline — 159 checks across 23 sections, 158 pass / 1 known fail. Static inventory matched baseline on every row (8 systemd unit files, 8 cgroup drop-in dirs per tree, `debian/DEBIAN/` 4 files, `scripts/update.sh` executable, 6 Windows packaging artifacts, VERSION 2.2.0 == control 2.2.0, 45 shell scripts, nats-server v2.14.5). No baseline drift, no new deviations.
- Issue: ASP-813

Run from `origin/master` (edbc440, merge of PR #78 / ASP-773 weekly architecture review). Toolchain: go1.26.0, cargo 1.93.1, gcc 15.2.0 + libseccomp, Python 3.14.4, pytest 9.1.1, nats-server v2.14.5. Per-suite: smoke 61 passed / 1 failed (C11 p50), 62 total; python 516 passed, 4 skipped, 0 failures — the same four absent optional dependencies (`aiohttp`, `mcp.server`, `nats-py`, and the Hermes holographic plugin missing `ruamel`), so the ASP-706 skip-on-ImportError fix is still holding. Lock was free before the run, so exit code 1 (1 failure) is a real check count, not exit-75 contention. ISO/deb image builds remain SKIP by design on this host (`ISO_BUILDER.md`, Option B); static checks only. Overwritten in place — do not add `docs/ops/nightly-results-*.md`.