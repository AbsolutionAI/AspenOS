# Nightly Check Results — 2026-09-01

**Verdict: PASS (1 known failure)**

| Metric | 08:32 UTC | 09:15 UTC (ASP-544) | 15:25 UTC (ASP-544 sweep) |
|--------|-----------|---------------------|--------------------------|
| Passed | 100 | 100 | 100 |
| Failed | 1 | 1 | 1 |
| Total  | 101 | 101 | 101 |
| Time   | 10,867ms | 12,655ms | 11,638ms |

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
| 13 | Python test suite | 4 | 0 |
| 14 | ISO build structure | 8 | 0 |
| 15 | Dashboard static assets | 8 | 0 |

## Workspace verification
- Git root: `/home/tech/projects/aspen-dev/repos/aspen-os` ✓
- Origin URL: `https://github.com/AbsolutionAI/AspenOS.git` ✓
- Branch: `master`
- Last commit: `8df715a` — `docs(sweep): ASP-544 daily sweep record — nightly v4 shipped` (HEAD, ASP-544 sweep)

## Static inventory
- systemd unit files: 9 in `systemd/`, 9 in `dist/pkgroot/lib/systemd/system/` (matches baseline)
- Debian metadata: control, postinst, postrm, prerm all present
- Version consistency: VERSION = 2.2.0 matches debian/DEBIAN/control
- `scripts/update.sh`: present and executable
- Windows packaging: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt (all 6 present)
- Gatekeeper module: `src/python/gatekeeper/minimal_shim.py` present with valid Python syntax
- Python tests: 152 passed, 3 skipped (optional deps: aiohttp, mcp.server), 0 failures
- ISO build structure: 3 autoinstall profiles (edge/server/ops YAMLs), chroot hook present, package lists present
- Dashboard static assets: 8 files present (style.css, ui.js, dashboard.js, agents.js, chat.js, panels.js, incidents.js, boot.js)

## Baseline deviations from ops doc
None. Baseline matches: 100 passed, 1 known failure (C11 p50).