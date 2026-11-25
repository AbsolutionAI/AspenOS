# Nightly latest

- Timestamp (UTC): 2026-11-25T09:02:51Z
- Git SHA: 103ca5b
- Verdict: PASS
- check-nightly: 160/160
- Deviations: None. The C11 p50 known failure from pre-ASP-807 is retired — the retuned gate (overhead < 2ms, absolute ceiling < 5ms) passes on this host: overhead 0.489 ms (c11 p50=2.744, py_exec p50=2.255), absolute 2.744 ms. Zero known deviations.

Run from the ASP-967 execution worktree at `origin/master` (103ca5b, PR #100 / ASP-807 retune the C11 p50 smoke gate). Toolchain: go1.26.8, cargo 1.93.1, gcc 15.2.0 + libseccomp, Python 3.14.4, nats-server v2.14.5. Per-suite: smoke 62 passed / 0 failed; Python 576 passed / 0 failures; iso-firstboot-smoke 32 passed / 0 failed. Lock was free before the run (no concurrent holder), exit code 0. ISO/deb image builds remain SKIP by design on this host (`ISO_BUILDER.md`, Option B); static checks only. Overwritten in place — do not add `docs/ops/nightly-results-*.md`.