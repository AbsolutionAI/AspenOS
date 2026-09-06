# Nightly Check Results — 2026-09-06 20:40 UTC

**Verdict: PASS (101 ✅, 1 known failure)**

| Suite | Result |
|---|---|
| Go toolchain | PASS |
| Rust toolchain | PASS |
| C11 toolchain | PASS |
| Go build (starshipctl) | PASS |
| Rust build (staragent) | PASS |
| C11 components (sandbox_spike, policyexec, starshipd, heald) | PASS |
| Smoke tests (58/59) | 1 known failure (C11 p50 ~3.45ms, hardware-dependent) |
| `make smoke` | 58 passed, 1 failed (same known C11 p50 deviation) |
| `make iso-smoke` | 32 passed, 0 failed |
| Debian package | PASS (size > 1MB) |
| Systemd units (16) | PASS (8 in `systemd/`, 8 in `dist/pkgroot/`) |
| Shell syntax (35 scripts) | PASS |
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

## Toolchain notes

- go1.26.0 linux/amd64
- cargo 1.93.1 (built from source tarball)
- Python 3.14.4
- Kernel 7.0.0-31-generic
- starshipctl: Starship OS CLI v2.1.0 (VERSION=2.2.0)

## Baseline deviations

- **`check-nightly.sh` total:** 101 passed, 1 failed — matches baseline (C11 p50 known deviation).
- **Shell syntax coverage:** 35 scripts (34 in `scripts/`, 1 in `packaging/`) — matches updated baseline.
- **Workspace note:** working tree carried uncommitted ASP-538/539 dual-human-clear work (mods to `docs/SECURITY_THREAT_MODEL_v2.2.md`, `scripts/smoke-fleet-bus.py`) and untracked plan/solution docs. The fleet-bus smoke (which includes the modified script) passed, so it does not affect the verdict.
- No other deviations from the baseline doc.

## Static inventory

- debian/DEBIAN/: control, postinst, postrm, prerm — all present
- Version consistency: VERSION=2.2.0, debian/DEBIAN/control Version: 2.2.0 — match
- scripts/update.sh — present, executable
- packaging/windows/: install.bat, configure.bat, uninstall.bat, staragent.exe (13MB), staragent.yaml, README.txt — all present
- Python tests: 156 passed, 3 skipped (optional deps: aiohttp, mcp.server), 0 failures

## Build steps

- ISO/deb builds SKIP by design on this host (Option B, `ISO_BUILDER.md`); static checks only.