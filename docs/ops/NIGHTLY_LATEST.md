# Nightly latest

- Timestamp (UTC): 2026-09-30T14:37:35Z
- Git SHA: 3eaa31ad408b94089ea45f1fa3fa3d1242f239ca
- Verdict: PASS
- check-nightly: 149/150
- Deviations: C11 p50 3.555 ms (known hardware deviation; ADR 0001 threshold is 2 ms). One
  additional non-baseline failure on the first run of the night — the Python suite's
  holographic-dual-write test — was diagnosed and fixed in this run; see below.
- Issue: ASP-699

## First run of the night: 148/150

The initial run (at `4596b7c`, the checked-out commit) failed `Section 13: no pytest failures` in
addition to the known C11 p50 failure. `tests/test_holographic_ingest.py::test_explicit_db_env_writes_holographic`
died on `ModuleNotFoundError: No module named 'ruamel'` instead of skipping. Its guard only
recognised two missing-module names (`tools.registry`, `holographic`), so any other missing optional
dependency became a hard failure — and it also missed the case where Aspen's own `plugins/` package
shadows the Hermes checkout and the error becomes `No module named 'plugins.memory'`. Fixed to
classify the missing top-level package: skip when it is not one of ours, raise when it is.

## Final run of the night: 149/150 at `3eaa31a`

Only the known C11 p50 deviation remains. Smoke suite `Result: 61 passed, 1 failed`; Python suite
`466 passed, 4 skipped`; the 4 skips are optional deps (`aiohttp`, `mcp.server`, the nats-py-dependent
dashboard import, and `ruamel.yaml`). Run time 17.6s, exit 1 (= 1 failed check).

## Static inventory

| Item | Observed |
| --- | --- |
| systemd units (`*.service`/`*.timer`/`*.socket`) | 16 — 8 in `systemd/`, 8 staged into `dist/pkgroot/lib/systemd/system/` by section 5; `deploy/` and `config/` 0 |
| systemd cgroup drop-in dirs | 8 in `systemd/<unit>.service.d/`, 8 staged into `dist/pkgroot/lib/systemd/system/` |
| Debian metadata | `debian/DEBIAN/`: control (`starship-os 2.2.0 amd64`), postinst, postrm, prerm — all present |
| `scripts/update.sh` | present, executable (`-rwxr-xr-x`) |
| Windows packaging | `packaging/windows/`: install.bat, configure.bat, uninstall.bat, staragent.exe, staragent.yaml, README.txt — all 6 present |
| Version consistency | `VERSION` 2.2.0 == `debian/DEBIAN/control` 2.2.0 |
| Shell syntax coverage | 44 scripts (43 `scripts/*.sh`, 1 `packaging/*.sh`) |
| ISO/deb image builds | SKIP by design (Option B, `ISO_BUILDER.md`); section 5 stages the deb tree only |

## Toolchain

- nats-server v2.14.5 (matches baseline)
- go1.26.0 linux/amd64, cargo 1.93.1, gcc with libseccomp
- python3 3.14.4 — host python; the isolated worktree has no `.venv`, so `check-nightly.sh` falls
  back to host python3 per ASP-600

## Coverage gap recorded in the runbook

The nightly reports `0 failures` for Python while the holographic dual-write assertion never
executes, because `ruamel.yaml` is installed neither on this host nor in `nightly.yml`. Documented
under the runbook baseline table.

Do not add `docs/ops/nightly-results-*.md`; the next nightly overwrites this file in place.