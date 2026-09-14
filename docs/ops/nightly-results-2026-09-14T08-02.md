# Nightly Packaging & Deployment Check — 2026-09-14 08:02 UTC

**Run:** [ASP-594](/ASP/issues/ASP-594) routine execution
**Agent:** Opencode (Aspen Implementation Engineer)
**Workspace:** `/home/tech/projects/aspen-dev/repos/aspen-os`
**Branch:** `master` (HEAD `4010c47`)

## Verdict: PASS

| Suite | Passed | Failed | Known |
|-------|--------|--------|-------|
| `make smoke` | 60 | 1 | C11 p50 < 2ms (3.423ms HW-dependent, known deviation) |
| `make iso-smoke` | 32 | 0 | — |
| Python test suite | 303 | 0 | 4 skipped (optional deps) |
| Shell syntax (`bash -n`) | 36 | 0 | — |

## Full Nightly Script

`bash scripts/check-nightly.sh`: **107 passed, 1 failed** across all 17 sections —
the single failure is the known hardware-dependent C11 p50 benchmark. Total runtime 13.6s (incremental build cache).

## Static Inventory

| Item | Status | Value |
|------|--------|-------|
| Systemd units (`systemd/`) | PASS | 9 files (8 services + 1 target) |
| Debian metadata | PASS | control, postinst, postrm, prerm |
| `scripts/update.sh` | PASS | present, executable (5036 bytes) |
| Windows packaging | PASS | 6 artifacts (staragent.exe 13MB, install.bat, configure.bat, uninstall.bat, staragent.yaml, README.txt) |
| Version consistency | PASS | VERSION=2.2.0, debian control=2.2.0 |
| AppArmor profiles | PASS | 3 profiles: agnetic-agent, nats, ollama |
| Gatekeeper module | PASS | minimal_shim.py present, syntax valid |
| Debian package | PASS | `dist/starship-os_2.2.0_amd64.deb`, 6.7MB |

## Toolchain

| Tool | Version | Status |
|------|---------|--------|
| nats-server | v2.14.5 | PASS (matches baseline) |
| Go | 1.26.0 | PASS |
| Rust/Cargo | 1.93.1 | PASS |
| Python | 3.14.4 | PASS |

## Deviations from Baseline

- **None.** All suites and static inventory match the documented baseline.
- **C11 p50:** measured 3.423ms (baseline doc references ~3.451ms). Slight
  run-to-run variance on the same host; remains the single known, non-actionable,
  hardware-dependent failure (ADR 0001 requires < 2ms).
- **Toolchain drift (informational):** host runs Go 1.26.0 / Python 3.14.4 vs the
  baseline doc's Go 1.22 / Python 3.12 CI toolchain mirror. All suites green.

## Baseline Update

| Check | Baseline | Current | Delta |
|-------|----------|---------|-------|
| smoke test suite | 60/1 | 60/1 | — |
| iso-smoke suite | 32/0 | 32/0 | — |
| Python test suite | 303/4 skip | 303/4 skip | — |
| nats-server | v2.14.5 | v2.14.5 | — |
| systemd unit files | 9 | 9 | — |
| Shell syntax | 36 | 36 | — |
| deb package | 6.7MB | 6.7MB | — |

## Disposition

**PASS** — nightly packaging & deployment check complete. ISO/deb build steps
skipped by design (Option B, `docs/ops/ISO_BUILDER.md`). Single smoke failure is
the known hardware-dependent C11 p50 benchmark; all other suites and static
inventory match baseline. No doc drift or stale references to fix this run.
