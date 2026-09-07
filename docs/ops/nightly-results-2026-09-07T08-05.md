# Nightly Check Results — 2026-09-07 08:05 UTC

**Verdict: PASS (101 ✅, 1 known failure)**

| Suite | Result |
|---|---|
| Go toolchain | PASS |
| Rust toolchain | PASS |
| C11 toolchain | PASS |
| Go build (starshipctl) | PASS |
| Rust build (staragent) | PASS |
| C11 components (sandbox_spike, policyexec, starshipd, heald) | PASS |
| Smoke tests (59/60) | 1 known failure (C11 p50 ~3.45ms, hardware-dependent) |
| `make smoke` | 59 passed, 1 failed (same known C11 p50 deviation) |
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
| Python test suite | 200 passed, 3 skipped, 0 failures |
| ISO structure (3 profiles, hooks, package lists) | PASS |
| Dashboard static assets (8 files) | PASS |

**nats-server:** v2.14.5

## Toolchain notes

- go1.26.0 linux/amd64
- cargo 1.93.1 (built from source tarball)
- Python 3.14.4
- starshipctl version: PASS (Starship OS CLI, VERSION=2.2.0)
- libseccomp-dev present (gcc + seccomp check PASS)

## Baseline deviations

- **`check-nightly.sh` total:** 101 passed, 1 failed — matches baseline (C11 p50 known deviation).
- **Smoke suite total:** now 59 passed, 1 failed (60 checks vs baseline 59). The +1 is the `authorize_clear` dual-human gate check in `scripts/smoke-fleet-bus.py` (ADR-0009 work carried uncommitted in the workspace tree). Fleet-bus smoke passes, so it does not alter the verdict.
- **Python test suite:** 200 passed (baseline 156/152) — suite has grown; 3 skipped (optional deps: aiohttp, mcp.server), 0 failures.
- **Shell syntax coverage:** 35 scripts (34 in `scripts/`, 1 in `packaging/`) — matches baseline.
- No other deviations from the baseline doc.

## Static inventory

- debian/DEBIAN/: control, postinst, postrm, prerm — all present
- Version consistency: VERSION=2.2.0, debian/DEBIAN/control Version: 2.2.0 — match
- scripts/update.sh — present, executable
- packaging/windows/: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt — all present
- Python tests: 200 passed, 3 skipped (optional deps: aiohttp, mcp.server), 0 failures

## Build steps

- ISO/deb builds SKIP by design on this host (Option B, `ISO_BUILDER.md`); static checks only.