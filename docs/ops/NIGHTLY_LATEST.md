# Nightly latest

- Timestamp (UTC): 2026-10-04T08:02:40Z
- Git SHA: 44eb3c8c2d2129905be6ff812f53a5f6397572d6
- Verdict: PASS
- check-nightly: 149/150
- Deviations: C11 p50 3.683 ms (known hardware deviation; ADR 0001 threshold is 2 ms). Same single known failure as the recorded baseline — 150 checks across 22 sections, 149 pass / 1 known fail. Static inventory matched baseline on every row (16 systemd unit files, 8 cgroup drop-in dirs per tree, `debian/DEBIAN/` 4 files, `scripts/update.sh` executable, 6 Windows packaging artifacts, VERSION 2.2.0 == control 2.2.0, 44 shell scripts, nats-server v2.14.5). No baseline drift, no new deviations.
- Issue: ASP-728

Run from base `origin/master` (44eb3c8, merge of PR #56 / ASP-720 daily implementation sweep), which is also the recorded git SHA — the worktree was clean at checkout. Delta since the prior record (ad356a3, ASP-718) is docs-only: two plan docs and the ASP-718 nightly record, so no product-code surface moved under the checks. Toolchain: go1.26.0, cargo 1.93.1, gcc 15.2.0 + libseccomp, Python 3.14.4, pytest 9.1.1, nats-server v2.14.5. Per-suite: smoke 61 passed / 1 failed (C11 p50), 62 total; python 466 passed, 4 skipped, 0 failures — the same four absent optional dependencies (`aiohttp`, `mcp.server`, `nats-py`, and the Hermes holographic plugin missing `ruamel`), so the ASP-706 skip-on-ImportError fix is still holding. Lock was free before the run, so exit code 1 (1 failure) is a real check count, not exit-75 contention. ISO/deb image builds remain SKIP by design on this host (`ISO_BUILDER.md`, Option B); static checks only. Overwritten in place — do not add `docs/ops/nightly-results-*.md`.
