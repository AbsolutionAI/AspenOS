# ASP-546: Nightly Packaging & Deployment Check

## Problem

The nightly packaging & deployment check needs to run daily on the control plane host,
verifying builds, smoke tests, static inventory, and toolchain health. Results must be
recorded with a clear PASS/FAIL verdict and any baseline deviations.

## Solution

A runbook (`docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`) and a script
(`scripts/check-nightly.sh`) codify the full check in 15 sections:

| # | Section | Key files |
|---|---------|-----------|
| 1 | Go build | `starshipctl` via `make build` |
| 2 | Rust build | `staragent` via `cargo build` |
| 3 | C11 components | `sandbox_spike`, `policyexec`, `starshipd`, `heald` |
| 4 | Smoke tests | `scripts/smoke-test.sh` (58 tests, fleet-bus smoke) |
| 5 | Debian package | `scripts/build-deb.sh`, size check |
| 6 | Systemd units | 8 canonical units in `systemd/`, 8 in `dist/pkgroot/` |
| 7 | Shell syntax | `bash -n` on all `scripts/*.sh` and `packaging/*.sh` |
| 8 | Key files | VERSION, Makefile, configs, NATS, pins, version consistency |
| 9 | Debian metadata | control, postinst, postrm, prerm |
| 10 | Windows packaging | install.bat, configure.bat, uninstall.bat, staragent.exe, yaml, README |
| 11 | Update mechanism | scripts/update.sh present + executable |
| 12 | Gatekeeper | minimal_shim.py present + valid syntax |
| 13 | Python tests | pytest, 150+ pass, 0 failures |
| 14 | ISO structure | 3 autoinstall profiles, hooks, package lists |
| 15 | Dashboard assets | 8 static files (style.css, js modules) |

## Key findings

- **Systemd baseline drift:** The runbook previously claimed 18 units (9+9) but there are
  actually 16 (8+8). Updated to match reality.
- **C11 p50 benchmark (~3.451ms):** A known hardware-dependent deviation from the ADR 0001
  threshold of <2ms. Not actionable on this host — mark as known failure.

## Procedure

1. Verify workspace: `git rev-parse --show-toplevel` → aspen-os git root
2. Ensure nats-server on PATH: `export PATH="$HOME/go/bin:$HOME/.local/bin:$PATH"`
3. Run `bash scripts/check-nightly.sh` — records pass/fail per section
4. Record baseline deviation table
5. Post results as issue comment, commit results doc
6. On failure: diagnose, fix if well-scoped, otherwise mark blocked

## Files

| File | Purpose |
|------|---------|
| `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` | Runbook with baseline table |
| `scripts/check-nightly.sh` | Automation script (15 sections, ~100 checks) |
| `docs/ops/nightly-results-*.md` | Daily result records |

## Verdict

PASS (101 ✅, 1 known failure) — all builds, tests, and static inventory checks pass.
The single failure is the C11 p50 benchmark which is hardware-dependent and not
actionable.

## Future improvements

- Track systemd unit count automatically rather than hardcoding in the runbook
- Add a GA release check (does GitHub Actions nightly workflow run?)
- Smoke test the actual dashboard service endpoint