# ASP-376: F-012 — cgroup per-agent resource limits

**Status:** READY_FOR_AIDER_QA
**Mode:** IMPLEMENTATION

## Threat-model link

*Resource exhaustion / noisy neighbor* row of the ASP-298 refresh. NATS caps
bound connection floods (F-011); nothing bounded a single agent's CPU, memory,
or thread usage from starving siblings on the shared control-plane host. F-012
adds cgroup v2 ceilings per service unit.

## Key insight: drop-ins are the overrideable layer systemd already merges

Rather than editing the base `systemd/*.service` files (operators may pin
overrides), ship limits as `<unit>.service.d/10-cgroup-limits.conf`. systemd
unit(5) loads `*.d/*.conf` from the unit search path, so:

- **.deb path:** `build-deb.sh` stages `systemd/*.service.d/` into
  `lib/systemd/system/` and gates the build on the drop-in shipping.
- **dev/VM path:** `install-systemd.sh` copies each drop-in to
  `/etc/systemd/system/<unit>.service.d/`, which outranks the packaged unit —
  admin overrides keep working.
- Nothing is applied live to a host by the repo; limits follow packaging.

## Knobs (cgroup v2)

`MemoryMax` (hard OOM ceiling) + `MemoryHigh` (soft reclaim throttle) bound
memory; `CPUQuota` bounds CPU as absolute % of one core; `TasksMax` caps
threads/processes via the pids controller (the fork-bomb / leaked-thread
analogue of NATS `max_closed_clients`). Accounting set explicitly.

## Per-unit ceilings

Agent template gets headroom (`CPUQuota=150%`, `MemoryMax=1G`, `TasksMax=128`);
infra daemons one core / 512M; lightweight bridges a quarter core / 128M.
Details in `docs/ops/CGROUPS_RESOURCE_LIMITS.md`.

## Files changed

| File | Change |
|------|--------|
| `systemd/<unit>.service.d/10-cgroup-limits.conf` ×8 | new drop-ins (agent, message-history, nats, dashboard, staragent, status-bridge, fleet, health-checker) |
| `scripts/build-deb.sh` | stage `*.service.d` dirs, chmod confs, layout + post-build gate on drop-in presence |
| `scripts/install-systemd.sh` | install drop-ins to `/etc/systemd/system/<unit>.service.d/` |
| `docs/ops/CGROUPS_RESOURCE_LIMITS.md` | new operator reference (knobs, per-unit table, override, live verify) |
| `tests/test_cgroup_limits.py` | new fixture tests (5) |
| `scripts/check-nightly.sh` | +Section 20 gate |
| `tests/test_ci_assertions.py` | Section 20 presence assertion |
| `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` | Section 20 row + baseline (90 checks / 20 sections) |
| `docs/plans/ASP-376.md` | Plan document |

## Verification

```bash
python3 -m pytest tests/test_cgroup_limits.py -v   # 5 passed
python3 -m pytest tests/test_ci_assertions.py -q   # 14 passed
bash -n scripts/build-deb.sh scripts/install-systemd.sh scripts/check-nightly.sh
grep -c 'check "' scripts/check-nightly.sh        # 90 checks (5 new in Section 20)
```

No live systemd/cgroup application performed (board rule: `bt-asp-srv` untouched —
limits ship in git only).

Related: [ASP-375](/ASP/issues/ASP-375) (F-011 NATS rate limits), [ASP-373](/ASP/issues/ASP-373)
(F-009 mode 600) — same threat-model DoS family.