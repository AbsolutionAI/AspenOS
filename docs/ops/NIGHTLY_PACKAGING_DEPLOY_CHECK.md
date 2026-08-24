# Nightly Packaging & Deployment Check

Runbook for the nightly packaging & deployment health sweep on the control
plane host. Each run is executed by the assigned implementation agent against
the `aspen-os` git checkout.

## Scope

This host runs **static checks only**. ISO/deb build steps are SKIP by design
(Option B — separate ISO builder host, see `ISO_BUILDER.md`). Full builds are
validated on the builder host, not here.

## Procedure

1. **Workspace verification**
   - `git rev-parse --show-toplevel` resolves to the `aspen-os` git root.
   - `git remote get-url origin` points at
     `https://github.com/AbsolutionAI/AspenOS.git`.
2. **Toolchain**: ensure `nats-server` is on PATH:
   `export PATH="$HOME/go/bin:$HOME/.local/bin:$PATH"`.
3. **Smoke suites** (record pass/fail counts):
   - `make smoke`
   - `make iso-smoke`
4. **Static inventory**:
   - systemd unit count (`*.service`/`*.timer`/`*.socket` across
     `systemd/`, `dist/pkgroot/lib/systemd/system/`, `deploy/`, `config/`)
   - Debian metadata presence (`debian/DEBIAN/{control,postinst,postrm,prerm}`)
   - `scripts/update.sh` present and executable
   - Windows packaging artifacts under `packaging/windows/`
     (`install.bat`, `configure.bat`, `uninstall.bat`,
     `staragent.exe`, `staragent.yaml`, `README.txt`)
5. **Build steps**: ISO/deb builds are SKIP by design on this host (Option B);
   static checks only.
6. **Reporting**: post a results comment on the run issue with:
   - verdict line (PASS/FAIL)
   - pass/fail counts per suite
   - toolchain notes (nats-server version, etc.)
   - deviations from this baseline doc

On failure: diagnose, fix if well-scoped, otherwise mark the run issue
blocked naming the failing check and owner.

## Baseline (2026-08-24)

| Check | Baseline |
| --- | --- |
| `make smoke` | 67 passed, 0 failed |
| `make iso-smoke` | 32 passed, 0 failed |
| nats-server | v2.14.5 |
| systemd unit files | 20 (8 in `systemd/`, 8 in `dist/pkgroot/lib/systemd/system/`, 3 in `deploy/`, 1 in `config/`) |
| Debian metadata | `debian/DEBIAN/`: control (starship-os 2.2.0 amd64), postinst, postrm, prerm |
| `scripts/update.sh` | present, executable |
| Windows packaging | `packaging/windows/`: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt |

Update this table when suites gain or lose checks so future nightly runs can
report meaningful deviations.
