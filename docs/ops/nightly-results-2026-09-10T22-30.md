# Nightly Packaging & Deployment Check — 2026-09-10 22:30 UTC

**Run:** [ASP-582](/ASP/issues/ASP-582) routine execution
**Agent:** Opencode (Aspen Implementation Engineer)
**Workspace:** `/home/tech/projects/aspen-dev/repos/aspen-os`
**Branch:** `master` @ `f5013d8`

## Verdict: PASS

| Suite | Passed | Failed | Known |
|-------|--------|--------|-------|
| `make smoke` | 60 | 1 | C11 p50 < 2ms (3.451ms HW-dependent, known deviation) |
| `make iso-smoke` | 32 | 0 | — |
| Python test suite | 303 | 0 | 4 skipped (optional deps) |
| Shell syntax (`bash -n`) | 36 | 0 | — |

## Static Inventory

| Item | Status | Value |
|------|--------|-------|
| Systemd units (`systemd/`) | PASS | 9 files (8 services + 1 target) |
| Systemd units (`dist/`) | PASS | 9 files (8 services + 1 target) |
| Debian metadata | PASS | control, postinst, postrm, prerm |
| `scripts/update.sh` | PASS | present, executable (5036 bytes) |
| Windows packaging | PASS | 6 artifacts (staragent.exe 13MB, install.bat, configure.bat, uninstall.bat, staragent.yaml, README.txt) |
| Version consistency | PASS | VERSION=2.2.0, debian control=2.2.0 |
| AppArmor profiles | PASS | 3 profiles: agnetic-agent, nats, ollama |

## Toolchain

| Tool | Version | Status |
|------|---------|--------|
| nats-server | v2.14.5 | PASS (matches baseline) |
| Go | 1.26.0 | PASS |
| Rust/Cargo | 1.93.1 | PASS |
| Python | 3.14.4 | PASS |

## Deviations from Baseline

- **Doc reference drift:** `docs/ops/ISO_BUILDER.md` (cited in the issue description for "Option B") no longer exists in the repo. The SKIP-by-design posture for ISO/deb builds is still documented in `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` ("What is NOT checked", Section 14). Recommend dropping or updating the stale reference.
- **Toolchain drift (informational):** host runs Go 1.26.0 / Python 3.14.4 vs the baseline doc's Go 1.22 / Python 3.12 (CI toolchain mirror). All suites still green; noted for accuracy only.
- **Counts:** smoke 60/1, iso-smoke 32/0, python 303 pass / 4 skip — all match the baseline table.

## Baseline Update

| Check | Baseline | Current | Delta |
|-------|----------|---------|-------|
| smoke test suite | 60/1 | 60/1 | — |
| iso-smoke suite | 32/0 | 32/0 | — |
| Python test suite | 303/4 skip | 303/4 skip | — |
| nats-server | v2.14.5 | v2.14.5 | — |
| systemd unit files | 18 | 18 | — |
| Shell syntax | 36 | 36 | — |

## Disposition

**PASS** — nightly packaging & deployment check complete. ISO/deb build steps skipped by design (Option B). Single smoke failure is the known hardware-dependent C11 p50 benchmark; all other suites and static inventory match baseline.