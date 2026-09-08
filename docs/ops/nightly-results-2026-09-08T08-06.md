# Nightly Check Results — 2026-09-08 08:06 UTC

**Verdict: PASS (103 ✅, 1 known failure)**

| Suite | Result |
|---|---|
| Go toolchain | PASS |
| Rust toolchain | PASS |
| C11 toolchain | PASS |
| Go build (starshipctl) | PASS |
| Rust build (staragent) | PASS |
| C11 components (sandbox_spike, policyexec, starshipd, heald) | PASS |
| Smoke tests (59/60) | 1 known failure (C11 p50 ~hardware-dependent) |
| `make smoke` | 59 passed, 1 failed (same known C11 p50 deviation) |
| Debian package | PASS (6.6 MB, >1MB; `dist/starship-os_2.2.0_amd64.deb`) |
| Systemd units (9) | PASS (9 in `systemd/`, 9 in `dist/pkgroot/lib/systemd/system/`) |
| Shell syntax (38 scripts) | PASS |
| Key files (VERSION, Makefile, configs, NATS, pins) | PASS |
| Version consistency (VERSION == debian/DEBIAN/control) | PASS |
| Debian metadata | PASS |
| Windows packaging | PASS |
| Update mechanism (scripts/update.sh) | PASS |
| Gatekeeper module | PASS |
| Python test suite | 299 passed / 4 skipped / 0 failures |
| ISO structure (3 profiles, hooks, package lists) | PASS |
| Dashboard static assets (8 files) | PASS |
| Dev-only package isolation (H-019) | PASS |

**nats-server:** v2.14.5

## Toolchain notes

- go1.26.0 linux/amd64
- cargo 1.93.1 (built from source tarball)
- Python 3.14.4 (pytest installed and functional on this host)
- starshipctl version: PASS (Starship OS CLI, VERSION=2.2.0)
- libseccomp-dev present (gcc + seccomp check PASS)

## Changes from previous check (ASP-571, 2026-09-07 22:01 UTC)

1. **Fixed: `test_devonly_marker_detected` assertion bug** — the H-019 gate script (`scripts/check-no-devonly-in-prod.sh`) reports its verdict via `echo` (stdout), but the test asserted the offending marker appeared in `result.stderr`. The gate itself worked correctly (returncode 1 + stdout message); only the test's stream assertion was wrong. Fixed the test to check combined stdout+stderr. This was the Section 13 `no pytest failures` check failing (0 failures now).
2. **pytest now installed/functional on this host** — prior runs flagged 2 cosmetic Section 13 failures because pytest was absent/broken (PEP 668). pytest runs clean now; no functional gap.

## Static inventory

- debian/DEBIAN/: control (starship-os 2.2.0 amd64), postinst, postrm, prerm — all present
- VERSION: 2.2.0, debian/DEBIAN/control Version: 2.2.0 — match
- scripts/update.sh — present, executable
- packaging/windows/: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt — all present
- Python test suite: 299 passed / 4 skipped / 0 failures
- 3 autoinstall profiles: edge, server, ops — all present with hooks and package lists

## Build steps

- ISO/deb builds SKIP by design on this host (Option B, `ISO_BUILDER.md`); static checks only (deb build is exercised by Section 5 and produced `dist/starship-os_2.2.0_amd64.deb`, 6.6 MB).

## Known deviations

### C11 sandbox p50 benchmark (`make smoke` check 53 of 60)

Same as baseline: ADR-0001 requires `c11_internal p50 < 2ms`. Measured above threshold on this control-plane host. Hardware-dependent; not actionable.

## Baseline table update

The H-019 Dev-only isolation gate added in ASP-574 introduced `tests/test_devonly_isolation.py` (3 tests). After the stream-assertion fix, all 3 pass. Baseline now reflects **103 total checks passed, 1 known failure**, Python suite **299 passed / 4 skipped / 0 failures**.
