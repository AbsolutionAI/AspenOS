# Nightly Packaging & Deployment Check

**Source:** `.github/workflows/nightly.yml`  
**Script:** `scripts/check-nightly.sh`  
**Schedule:** Daily at 02:00 UTC (`0 2 * * *`)  
**Manual trigger:** Yes, via `workflow_dispatch` in GitHub Actions

## Procedure (runbook)

1. **Workspace verification**
   - `git rev-parse --show-toplevel` resolves to the `aspen-os` git root.
   - `git remote get-url origin` points at `https://github.com/AbsolutionAI/AspenOS.git`.
2. **Toolchain**: ensure `nats-server` is on PATH:
   `export PATH="$HOME/go/bin:$HOME/.local/bin:$PATH"`.
3. **Smoke suites** (record pass/fail counts):
   - `bash scripts/check-nightly.sh` (~92 checks across 15 sections)
4. **Static inventory**:
   - systemd unit count (`*.service`/`*.timer`/`*.socket` across `systemd/`, `dist/pkgroot/lib/systemd/system/`, `deploy/`, `config/`)
   - Debian metadata presence (`debian/DEBIAN/{control,postinst,postrm,prerm}`)
   - `scripts/update.sh` present and executable
   - Windows packaging artifacts under `packaging/windows/` (`install.bat`, `configure.bat`, `uninstall.bat`, `staragent.exe`, `staragent.yaml`, `README.txt`)
   - Version consistency between `VERSION` file and `debian/DEBIAN/control`
5. **Build steps**: ISO/deb builds are SKIP by design on this host (Option B, see `ISO_BUILDER.md`); static checks only.
6. **Reporting**: post a results comment on the run issue with:
   - verdict line (PASS/FAIL)
   - pass/fail counts per suite
   - toolchain notes (nats-server version, etc.)
   - deviations from this baseline doc

On failure: diagnose, fix if well-scoped, otherwise mark the run issue blocked naming the failing check and owner.

## What gets checked

The nightly check runs in 15 sections:

| Section | Checks |
|---------|--------|
| 1. Go build | `make build`, `starshipctl version` |
| 2. Rust build | `cargo build --release` for staragent |
| 3. C11 components | sandbox_spike, policyexec, starshipd, heald |
| 4. Smoke tests | Full suite via `scripts/smoke-test.sh` (58 tests, including iso-firstboot-smoke, fleet-bus smoke against pinned sibling repos) |
| 5. Debian package | `scripts/build-deb.sh`, package size > 1MB |
| 6. Systemd units | All 9 canonical units exist on disk |
| 7. Shell syntax | `bash -n` on every `scripts/*.sh` and `packaging/*.sh` |
| 8. Key file presence | VERSION, Makefile, configs, NATS configs, pins.json, version consistency |
| 9. Debian metadata | control, postinst, postrm, prerm |
| 10. Windows packaging | install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt |
| 11. Update mechanism | scripts/update.sh present and executable |
| 12. Gatekeeper module | `src/python/gatekeeper/minimal_shim.py` present, valid Python syntax |
| 13. Python test suite | pytest importable, test suite runs (150+ pass), no pytest errors |
| 14. ISO build structure | autoinstall profiles (user-data.edge.yaml, user-data.server.yaml, user-data.ops.yaml), hooks, package lists |
| 15. Dashboard static assets | style.css, ui.js, dashboard.js, agents.js, chat.js, panels.js, incidents.js, boot.js |

## CI infrastructure

The nightly workflow clones sibling repositories (`aspen-edge-rrm`, `aspen-swarm-manager`) at pinned commits from `third_party/pins.json` to support the fleet-bus smoke test. Toolchain setup mirrors `ci.yml` (Go 1.22, Python 3.12, Rust stable, libseccomp-dev).

## Failure handling

- Each check is independent: a single failure does not halt the suite
- The exit code equals the number of failed checks (0 = all passed)
- The full run log is visible in GitHub Actions under the nightly workflow

## Baseline

| Check | Baseline |
| --- | --- |
| `scripts/check-nightly.sh` total | **101 passed, 1 known failure** (C11 p50 benchmark deviation = known, hardware-dependent) |
| Of which: smoke test suite | 58 passed, 1 failed (C11 p50 benchmark) |
| Python test suite | 152+ passed, 3 skipped (optional deps: aiohttp, mcp.server), 0 failures |
| nats-server | v2.14.5 |
| systemd unit files | 16 (8 in `systemd/`, 8 in `dist/pkgroot/lib/systemd/system/`) |
| Debian metadata | `debian/DEBIAN/`: control (starship-os 2.2.0 amd64), postinst, postrm, prerm |
| `scripts/update.sh` | present, executable |
| Windows packaging | `packaging/windows/`: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt |
| Version consistency | VERSION matches debian/DEBIAN/control |
| Gatekeeper module | `src/python/gatekeeper/minimal_shim.py` present, valid Python syntax |
| ISO build structure | 3 autoinstall profiles (edge/server/ops YAMLs), chroot hooks present, package lists present |
| Dashboard static assets | 8 files present (style.css, ui.js, dashboard.js, agents.js, chat.js, panels.js, incidents.js, boot.js) |
| Shell syntax coverage | 35 scripts (34 in `scripts/`, 1 in `packaging/`), all pass `bash -n` |

Update this table when suites gain or lose checks so future nightly runs can report meaningful deviations.

## Known deviations

### C11 sandbox p50 benchmark (`make smoke` check 53 of 59)

The ADR 0001 criterion requires `c11_internal p50 < 2ms`. On this control-plane host,
the measured p50 is ~3.451ms. This is a hardware-dependent benchmark: the threshold may
be met on dedicated CI runners with newer processors or lower latency profiles.

**Not actionable** unless the sandbox is moved to a different host or optimized. The
nightly check records this as a single known failure (1 of 59 smoke tests).

## What is NOT checked

- ISO build from source (requires root / nested virt, not feasible in CI; directory structure is statically checked in Section 14)
- Windows packaging build from source (no CI build host)
- Docker image build (`make docker`)
- Performance benchmarks (use `make bench`)
- Integration tests against real NATS mesh

## Previous findings from manual audits

See `docs/solutions/` for historical packaging issues:
- `asp-11-12-13-deb-upgrade-paths.md` — Debian upgrade safety
- `asp-15-install-systemd-path.md` — Stale systemd path
- `asp-16-health-checker-path.md` — Health checker path fix
- `asp-18-canonical-repo-urls.md` — GitHub URL hygiene
- `asp-190-health-checker-unit-deployment.md` — Health checker unit packaging
- `asp-192-deploy-stale-units.md` — Stale units cleanup
- `asp-478-c11-kernel7-allowlist.md` — C11 seccomp allowlist drift
- `asp-512-nightly-check.md` — Initial nightly check
- `asp-518-nightly-check-fixes.md` — Shell syntax + sibling repo hardening
- `asp-521-nightly-check-complete.md` — Debian metadata, Windows packaging, update mechanism
- `asp-524-nightly-check-improvements.md` — nats-server v2.14.5, gatekeeper module, baseline refresh
- `asp-543-nightly-check-improvements.md` — Python test suite, ISO structure, dashboard assets

## Adding new checks

Edit `scripts/check-nightly.sh` and add a `check "description" command-to-run` line in the appropriate section, or create a new section. Update this ops doc with the new check and the baseline table.
