# Nightly latest

- Timestamp (UTC): 2026-10-03T08:02:08Z
- Git SHA: ad356a3120f9a17899aa9ca8a95c9d655680dda8
- Verdict: PASS
- check-nightly: 149/150
- Deviations: C11 p50 3.641 ms (known hardware deviation; ADR 0001 threshold is 2 ms). Same single known failure as the recorded baseline — 150 checks across 22 sections, 149 pass / 1 known fail. Static inventory matched baseline on every row (16 systemd unit files, 8 cgroup drop-in dirs per tree, `debian/DEBIAN/` 4 files, `scripts/update.sh` executable, 6 Windows packaging artifacts, VERSION 2.2.0 == control 2.2.0, 44 shell scripts, nats-server v2.14.5). No baseline drift, no new deviations.
- Issue: ASP-718

Run from base `origin/master` (ad356a3), which carries the ASP-706 skip-guard fix (445f806 via PR #53) and the prior ASP-710 nightly record. Toolchain: go1.26.0, cargo 1.93.1, gcc + libseccomp, Python 3.14.4, pytest 9.1.1, nats-server v2.14.5. Per-suite: smoke 61 passed / 1 failed (C11 p50), 62 total; python 466 passed, 4 skipped, 0 failures — the same four absent optional dependencies (`aiohttp`, `mcp.server`, `nats-py`, and the Hermes holographic plugin missing `ruamel`), so the ASP-706 skip-on-ImportError fix is holding. ISO/deb image builds remain SKIP by design on this host (`ISO_BUILDER.md`, Option B); static checks only. Overwritten in place — do not add `docs/ops/nightly-results-*.md`.
