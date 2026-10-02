# Nightly latest

- Timestamp (UTC): 2026-10-02T08:02:20Z
- Git SHA: 0ce23a96c1d679910cfdeb2118dcaaca7b46a0e9
- Verdict: PASS
- check-nightly: 149/150
- Deviations: C11 p50 3.705 ms (known hardware deviation; ADR 0001 threshold is 2 ms). Same single known failure as the recorded baseline — 150 checks across 22 sections, 149 pass / 1 known fail. Static inventory matched baseline on every row (16 systemd unit files, 8 cgroup drop-in dirs per tree, `debian/DEBIAN/` 4 files, `scripts/update.sh` executable, 6 Windows packaging artifacts, VERSION 2.2.0 == control 2.2.0, 44 shell scripts, nats-server v2.14.5). No baseline drift, no new deviations.
- Issue: ASP-710

Run from base `origin/master` (0ce23a9), which already carries the ASP-706 skip-guard fix merged as 445f806 via PR #53. ISO/deb image builds remain SKIP by design on this host (`ISO_BUILDER.md`, Option B); static checks only. Overwritten in place — do not add `docs/ops/nightly-results-*.md`.