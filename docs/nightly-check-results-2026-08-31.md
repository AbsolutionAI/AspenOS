# Nightly Check Results — 2026-08-31 15:30 UTC

**Verdict: PASS (1 known failure)**

| Metric | Value |
|--------|-------|
| Passed | 80 |
| Failed | 1 |
| Total  | 81 |
| Time   | 10,788ms |

**Known failure:** C11 p50 benchmark deviation — hardware-dependent, ~3.451ms vs 2ms threshold per ADR 0001. Not actionable on this control-plane host.

## Toolchain
- nats-server: v2.14.5 (on PATH at `$HOME/go/bin/nats-server`)
- Go: go1.26.0 linux/amd64
- Cargo/Rust: cargo 1.93.1
- gcc: (Ubuntu 15.2.0-16ubuntu1) 15.2.0
- libseccomp-dev: 2.6.0-2ubuntu5

## Section-by-section results
| Section | Name | Pass | Fail |
|---------|------|------|------|
| Pre-flight | Toolchain | 3 | 0 |
| 1 | Go build | 2 | 0 |
| 2 | Rust agent build | 1 | 0 |
| 3 | C11 components | 4 | 0 |
| 4 | Smoke tests | 58 | 1 (known C11 p50) |
| 5 | Debian package | 2 | 0 |
| 6 | Systemd units | 9 | 0 |
| 7 | Shell syntax | 34 | 0 |
| 8 | Key file presence | 10 | 0 |
| 9 | Debian metadata | 5 | 0 |
| 10 | Windows packaging | 6 | 0 |
| 11 | Update mechanism | 2 | 0 |
| 12 | Gatekeeper module | 2 | 0 |

## Workspace verification
- Git root: `/home/tech/aspen-dev/repos/aspen-os` ✓
- Origin URL: `https://github.com/AbsolutionAI/AspenOS.git` ✓
- Branch: `master`
- Last commit: `57cf10e` — `docs(compound): ASP-541 daily implementation sweep learning`

## Static inventory
- systemd unit files: 9 in `systemd/`, 9 in `dist/pkgroot/lib/systemd/system/` (matches baseline)
- Debian metadata: control, postinst, postrm, prerm all present
- Version consistency: VERSION = 2.2.0 matches debian/DEBIAN/control
- `scripts/update.sh`: present and executable
- Windows packaging: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt (all 6 present)
- Gatekeeper module: `src/python/gatekeeper/minimal_shim.py` present with valid Python syntax
- Python tests: 152 passed, 2 skipped (optional deps: aiohttp, mcp.server), 1 pre-existing collection-order failure (`test_holographic_ingest` in bulk)

## Baseline deviations from ops doc
None. Baseline matches: 80 passed, 1 known failure (C11 p50).