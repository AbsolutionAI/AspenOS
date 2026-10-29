# Nightly latest

- Timestamp (UTC): 2026-10-29T08:02:12Z
- Git SHA: edbc440
- Verdict: PASS
- check-nightly: 158/159
- Deviations: C11 p50 ~3.5ms (known hardware deviation; ADR 0001 threshold is 2ms). Same single known failure as the recorded baseline — 159 checks across 23 sections, 158 pass / 1 known fail. Static inventory matched baseline on every row (8 systemd unit files per tree, 8 cgroup drop-in dirs per tree, `debian/DEBIAN/` 4 files, `scripts/update.sh` executable, 6 Windows packaging artifacts, VERSION 2.2.0 == control 2.2.0, 45 shell scripts, nats-server v2.14.5). Python suite measured 516 passed / 4 skipped vs. 500 in the baseline table — a benign +16 net from added unit tests, 0 failures, same 4 optional-dependency skips (`aiohttp`, `mcp.server`, `nats-py`, Hermes `ruamel`). No baseline drift, no new deviations.
- Issue: ASP-828