# Nightly Packaging & Deployment Check — 2026-09-15 08:16 UTC

**Run:** [ASP-602](/ASP/issues/ASP-602)
**Agent:** aspen (Opencode) — nightly routine
**Workspace:** `/home/tech/projects/aspen-dev/repos/aspen-os`
**Branch:** `master` (HEAD @ `9fb5386`)

## Verdict: PASS

| Suite | Passed | Failed | Known / notes |
|-------|--------|--------|---------------|
| `scripts/check-nightly.sh` | **107** | **1** | C11 p50 HW-dep only |
| Smoke (`make smoke` via nightly §4) | 60 | 1 | C11 p50 < 2ms (known HW-dependent) |
| Python suite (repo `.venv`) | PASS | 0 | ≥150 threshold, no failures |
| Shell syntax (`bash -n`) | 36 | 0 | — |

## Static Inventory

| Item | Status | Value |
|------|--------|-------|
| Systemd units | PASS | 9 sources (`systemd/`) + 9 staged (`dist/pkgroot/lib/systemd/system/`) = 18 |
| Debian metadata | PASS | control, postinst, postrm, prerm |
| `scripts/update.sh` | PASS | present, executable |
| Windows packaging | PASS | 6 artifacts (install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt) |
| Version consistency | PASS | VERSION=2.2.0, debian control=2.2.0 |
| AppArmor profiles | PASS | 3 profiles (agnetic-agent, nats, ollama) |
| Gatekeeper module | PASS | `src/python/gatekeeper/minimal_shim.py` present |
| ISO structure | PASS | edge/server/ops profiles + hooks, package lists non-empty |
| ISO/deb full rebuild | SKIP | Option B by design |

## Toolchain

| Tool | Version | Status |
|------|---------|--------|
| nats-server | v2.14.5 | PASS (baseline) |
| Go | 1.26.0 | PASS |
| Rust/Cargo | 1.93.1 | PASS |
| Python | 3.14.4 (+ repo `.venv`) | PASS |

## Deviations from Baseline

- **None.** Suite matches baseline: **107 pass / 1 known C11 fail**.
- **C11 p50:** known hardware-dependent benchmark — not actionable (ADR 0001 / runbook §Known deviations).
- **Paperclip API:** unreachable during this run (`connection refused` to `10.242.32.120:3100` and `127.0.0.1:3100`); results recorded via this doc + commit + push.

## Evidence

- Full check log: `/tmp/nightly-run-asp602-0216.log` — time 13.6s, exit 1 (= 1 failed check).
- Failure is only check 53 of 61 smoke tests: "C11 p50 under 2ms" — matches baseline.