# Nightly latest

- Timestamp (UTC): 2026-10-07T08:02:35Z
- Git SHA: 101a77815cd086496e4d528c0e9376fda811257c
- Verdict: PASS
- check-nightly: 149/150
- Deviations: C11 p50 3.653 ms (known hardware deviation; ADR 0001 threshold is 2 ms). Same single known failure as the recorded baseline — 150 checks across 22 sections, 149 pass / 1 known fail. Static inventory matched baseline on every row (16 systemd unit files, 8 cgroup drop-in dirs per tree, `debian/DEBIAN/` 4 files, `scripts/update.sh` executable, 6 Windows packaging artifacts, VERSION 2.2.0 == control 2.2.0, 44 shell scripts, nats-server v2.14.5). No baseline drift, no new deviations.
- Issue: ASP-749

Run from base `origin/master` (101a778, merge of the ASP-739 weekly architecture review). Toolchain: go1.26.0, cargo 1.93.1, gcc 15.2.0 + libseccomp, Python 3.14.4, pytest 9.1.1, nats-server v2.14.5. Per-suite: smoke 61 passed / 1 failed (C11 p50), 62 total; `make iso-smoke` 32 passed / 0 failed; python 466 passed, 4 skipped, 0 failures — the same four absent optional dependencies (`aiohttp`, `mcp.server`, `nats-py`, and the Hermes holographic plugin missing `ruamel`), so the ASP-706 skip-on-ImportError fix is holding. ISO/deb image builds remain SKIP by design on this host (`ISO_BUILDER.md`, Option B); static checks only. Overwritten in place — do not add `docs/ops/nightly-results-*.md`.
