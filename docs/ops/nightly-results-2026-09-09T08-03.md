# Nightly Check Results — 2026-09-09 08:03 UTC

**Verdict: PASS (107 ✅, 1 known failure)**

| Suite | Result |
|---|---|
| Go toolchain | PASS |
| Rust toolchain | PASS |
| C11 toolchain | PASS |
| Go build (starshipctl) | PASS |
| Rust build (staragent) | PASS |
| C11 components (sandbox_spike, policyexec, starshipd, heald) | PASS |
| Smoke tests (60/61) | 1 known failure (C11 p50 ~hardware-dependent) |
| `make smoke` | 60 passed, 1 failed (same known C11 p50 deviation) |
| Debian package | PASS (6.7 MB, >1MB; `dist/starship-os_2.2.0_amd64.deb`) |
| Systemd units (9) | PASS (9 in `systemd/`, 9 in `dist/pkgroot/lib/systemd/system/`) |
| Shell syntax (36 scripts) | PASS |
| Key files (VERSION, Makefile, configs, NATS, pins) | PASS |
| Version consistency (VERSION == debian/DEBIAN/control) | PASS |
| Debian metadata | PASS |
| Windows packaging | PASS |
| Update mechanism (scripts/update.sh) | PASS |
| Gatekeeper module | PASS |
| Python test suite | 303 passed / 4 skipped / 0 failures |
| ISO structure (3 profiles, hooks, package lists) | PASS |
| Dashboard static assets (8 files) | PASS |
| Dev-only package isolation (H-019) | PASS |
| AppArmor profiles in deb (H-010) | PASS |

**nats-server:** v2.14.5

## Toolchain notes

- go1.26.0 linux/amd64
- cargo 1.93.1 linux/amd64 (built from source tarball)
- Python 3.14.4 (pytest 9.1.1 installed and functional on this host)
- starshipctl version: PASS (Starship OS CLI, VERSION=2.2.0)
- libseccomp-dev present (gcc + seccomp check PASS)

## Changes from previous check (ASP-576, 2026-09-08 08:06 UTC)

1. **No new failures this run.** All sections pass except the single known C11 p50 benchmark deviation (hardware-dependent).
2. **Smoke suite grew to 61 checks** (60 passed + C11 p50 known failure). New since ASP-576: the `fleet-bus H-007 dual-human clear gate` smoke check (ASP-573).
3. **Python suite grew to 303 passed / 4 skipped** (from 299 / 4 at ASP-576), consistent with the sentinel consumer tests and AppArmor verification work in the working tree.

## Static inventory

- debian/DEBIAN/: control (starship-os 2.2.0 amd64), postinst, postrm, prerm — all present
- VERSION: 2.2.0, debian/DEBIAN/control Version: 2.2.0 — match
- scripts/update.sh — present, executable
- packaging/windows/: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt — all present
- Python test suite: 303 passed / 4 skipped / 0 failures
- 3 autoinstall profiles: edge, server, ops — all present with hooks and package lists
- Systemd: 9 canonical units in `systemd/` and 9 installed copies in `dist/pkgroot/lib/systemd/system/` — match

## Build steps

- ISO/deb builds SKIP by design on this host (Option B, `ISO_BUILDER.md`); static checks only. The deb build is exercised by Section 5 and produced `dist/starship-os_2.2.0_amd64.deb`, 6.7 MB.

## Known deviations

### C11 sandbox p50 benchmark (`make smoke` check 53 of 61)

Same as baseline: ADR-0001 requires `c11_internal p50 < 2ms`. Measured above threshold on this control-plane host. Hardware-dependent; not actionable.

## Baseline table update

The baseline table in `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` was stale (last reflective of ASP-524-era counts). Updated to reflect the current suite:

- check-nightly.sh total: **107 passed, 1 known failure** (was 101)
- Smoke suite: **60 passed, 1 failed** (was 58/1)
- Python test suite: **303 passed, 4 skipped, 0 failures** (was 152+/3)
- Systemd unit files: **9 in `systemd/`, 9 in `dist/pkgroot/`** (was 8/8)
- Shell syntax coverage: **36 scripts** (35 in `scripts/`, 1 in `packaging/`) (was 35)