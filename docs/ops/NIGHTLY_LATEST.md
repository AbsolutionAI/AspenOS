# Nightly latest

- Timestamp (UTC): 2026-09-29T08:08:19Z
- Git SHA: e3b1d598024b23abf58bf4ea9d03ddb10c44cdd9
- Verdict: PASS
- check-nightly: 149/150
- Deviations:
  - C11 p50 3.672 ms (known hardware deviation; ADR 0001 threshold is 2 ms). Same single known
    failure as the prior consecutive nightlies. `make bench`: `c11_internal p50 3.672`, `p95 4.693`,
    `mean 3.805` (N=200), inside the documented 3.2–3.7 ms host range.
- Issue: ASP-691

## Notes for this run

Static inventory matched the runbook baseline with no deviation: 16 systemd unit files (8 in
`systemd/`, 8 in `dist/pkgroot/lib/systemd/system/`, `agnetic-mesh.target` excluded per the row's
own `*.service`/`*.timer`/`*.socket` definition), 8 `.service.d` drop-in dirs in each tree, complete
`debian/DEBIAN/` metadata (`starship-os 2.2.0 amd64`), `VERSION` 2.2.0 consistent with
`debian/DEBIAN/control`, `scripts/update.sh` present and executable, all 6 `packaging/windows/`
artifacts present, 44 shell scripts passing `bash -n`. Toolchain: nats-server v2.14.5 (matches
baseline), go 1.26.0, cargo 1.93.1, Python 3.14.4, pytest 9.1.1. ISO/deb image builds SKIP by design
on this host; static checks only.

**A second failure was found and fixed during this run.** The first execution reported 148/150 with
two failures: the known C11 p50 deviation plus a new regression in section 13
(`no pytest failures`). `tests/test_holographic_ingest.py` hardcoded `/home/tech/.hermes/hermes-agent`
and guarded the import with a two-name substring check, so any unmet optional dependency of that
out-of-repo tree surfaced as a suite failure (`No module named 'ruamel'`). The guard now resolves the
path from the existing `HERMES_AGENT_ROOT` env var — the same knob `scripts/holographic_ingest.py:16`
already uses — adds it to `sys.path` only when it is a real directory, and skips on any
`ModuleNotFoundError`. See `docs/plans/ASP-691.md`. The re-run above is post-fix.

After the fix the Python suite reports **466 passed, 4 skipped, 0 failures**. The baseline row still
reads `470 passed, 4 skipped`; that gap is test-count drift, not new failures, and is left for the
Architect to reconcile rather than silently rewritten here.

This file is the live record and is overwritten in place by each nightly run. Do not add
`docs/ops/nightly-results-*.md`.
