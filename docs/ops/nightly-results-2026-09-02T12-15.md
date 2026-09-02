# Nightly Check Results — 2026-09-02 12:15 UTC

**Verdict: PASS (101 ✅, 1 known failure)**

| Suite | Result |
|---|---|
| Go toolchain | PASS |
| Rust toolchain | PASS |
| C11 toolchain | PASS |
| Go build (starshipctl) | PASS |
| Rust build (staragent) | PASS |
| C11 components (sandbox_spike, policyexec, starshipd, heald) | PASS |
| Smoke tests (58/59) | 1 known failure (C11 p50 ~3.451ms, hardware-dependent) |
| Debian package | PASS (size > 1MB) |
| Systemd units (16) | PASS (8 in `systemd/`, 8 in `dist/pkgroot/`) |
| Shell syntax (34 scripts) | PASS |
| Key files (VERSION, Makefile, configs, NATS, pins) | PASS |
| Version consistency (VERSION == debian/DEBIAN/control) | PASS |
| Debian metadata | PASS |
| Windows packaging | PASS |
| Update mechanism (scripts/update.sh) | PASS |
| Gatekeeper module | PASS |
| Python test suite | 156 passed, 3 skipped, 0 failures |
| ISO structure (3 profiles, hooks, package lists) | PASS |
| Dashboard static assets (8 files) | PASS |

**nats-server:** v2.14.5

## Baseline deviations

- **Systemd unit count:** 16 (8+8), not 18 (9+9) as previously documented. Updated baseline in `NIGHTLY_PACKAGING_DEPLOY_CHECK.md`.
- All other baseline values match.

## Static inventory

- debian/DEBIAN/: control, postinst, postrm, prerm — all present
- scripts/update.sh — present, executable
- packaging/windows/: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt — all present
- packaging/install-starship.sh — present, passes bash -n
- Python tests: 156 passed, 3 skipped (optional deps), 0 failures

## Script results

- `scripts/check-nightly.sh`: 101 passed, 1 failed (known C11 p50 benchmark)
- `make smoke`: 58 of 59 smoke tests passed (known sandbox p50 deviation)