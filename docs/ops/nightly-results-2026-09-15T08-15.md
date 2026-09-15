# Nightly Packaging & Deployment Check — 2026-09-15 08:15 UTC

**Run:** [ASP-602](/ASP/issues/ASP-602)
**Agent:** aspen (Opencode) — nightly routine
**Workspace:** `/home/tech/projects/aspen-dev/repos/aspen-os`
**Branch:** `master` (HEAD @ `4668bdf`)

## Verdict: PASS

| Suite | Passed | Failed | Known / notes |
|-------|--------|--------|---------------|
| `scripts/check-nightly.sh` | **107** | **1** | C11 p50 HW-dep only |
| Smoke (`make smoke` via nightly §4) | 60 | 1 | C11 p50 < 2ms (known HW-dependent) |
| Python via repo `.venv` | 303 | 0 | 4 skipped (optional deps) |
| Shell syntax (`bash -n`) | 36 | 0 | — |

## Static Inventory

| Item | Status | Value |
|------|--------|-------|
| Systemd units (`systemd/`) | PASS | 9 files (9 sources + 9 staged in pkgroot = 18) |
| Debian metadata | PASS | control, postinst, postrm, prerm |
| `scripts/update.sh` | PASS | present, executable |
| Windows packaging | PASS | 6 artifacts |
| Version consistency | PASS | VERSION=2.2.0, debian control=2.2.0 |
| AppArmor profiles | PASS | 3 profiles (agnetic-agent, nats, ollama); staged + postinst `apparmor_parser` (no `aa-enforce`) |
| Gatekeeper module | PASS | shim present, syntax valid |
| Debian package | PASS | `dist/starship-os_2.2.0_amd64.deb` ~6.4MB |
| H-019 dev-only isolation | PASS | Section 16 |
| H-010 AppArmor in deb | PASS | Section 17 |
| ISO structure | PASS | edge/server/ops profiles + hooks |
| ISO/deb full rebuild | SKIP | Option B |

## Toolchain

| Tool | Version | Status |
|------|---------|--------|
| nats-server | v2.14.5 | PASS |
| Go | 1.26.0 | PASS |
| Rust/Cargo | 1.93.1 | PASS |
| Python | 3.14.4 (+ repo `.venv`) | PASS |

## Deviations from Baseline

- **None.** Suite matches baseline: **107 pass / 1 known C11 fail**.
- **C11 p50:** known hardware-dependent benchmark — not actionable (ADR 0001 / runbook).
- **Paperclip API:** unreachable during this run (`connection refused` to `10.242.32.120:3100`); results recorded via this doc + commit.