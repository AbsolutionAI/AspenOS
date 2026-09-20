# ASP-376: H-012 — cgroups per-agent CPU/memory/PID limits

**Status:** IMPLEMENTED (git only — no live systemd applied)
**Mode:** IMPLEMENTATION
**Parent:** ASP-298 Biweekly Security Threat-Model refresh

## Threat-model link

F-012 of the ASP-298 refresh addresses resource-exhaustion DoS from a single
agent instance consuming all CPU, memory, or process slots on the host.
Without cgroup limits, a runaway agent loop, memory leak, or file-descriptor
storm in one agent can starve sibling agents or host services.

## Design

Each agent systemd unit gets a drop-in override at
`<unit>.d/10-cgroup-limits.conf` that enables resource accounting and sets
hard caps.  Drop-ins merge into the unit at load time — no unit file changes
are needed.

### Cgroup knobs used

| Key               | Effect                                         |
|-------------------|------------------------------------------------|
| CPUAccounting=yes | Enable CPU usage tracking                      |
| MemoryAccounting=yes | Enable memory usage tracking                 |
| TasksAccounting=yes | Enable task (PID) tracking                    |
| IOAccounting=yes  | Enable I/O tracking (I/O-intensive units only) |
| CPUQuota=         | Hard CPU limit (% of one core)                |
| CPUWeight=        | Relative CPU share at contention (default 100)|
| MemoryMax=        | Hard memory limit (incl. swap)                |
| MemoryHigh=       | Soft throttle threshold                        |
| TasksMax=         | Max PID count per unit                        |

### Per-unit profiles

| Unit                        | CPUQuota | CPUWeight | MemoryMax | MemoryHigh | TasksMax |
|-----------------------------|----------|-----------|-----------|------------|----------|
| agnetic-agent@.service      | 50%      | 100       | 512M      | 384M       | 128      |
| agnetic-staragent.service   | 25%      | 50        | 128M      | 96M        | 64       |
| agnetic-dashboard.service   | 25%      | 50        | 256M      | 192M       | 128      |
| agnetic-status-bridge.svc   | 25%      | 50        | 128M      | 96M        | 64       |
| agnetic-message-history.svc | 50%      | 100       | 512M      | 384M       | 128      |
| starship-fleet.service      | 50%      | 100       | 512M      | 384M       | 128      |
| starship-health-checker.svc | 25%      | 25        | 128M      | 96M        | 32       |
| agnetic-nats.service        | 100%     | 200       | 256M      | 192M       | 256      |

### Design rationale

- **Agent template (agnetic-agent@) and fleet manager** get identical profiles:
  both are Python agent processes with similar resource profiles.  Memory
  headroom (512M hard, 384M soft) accommodates LLM response processing and
  tool execution without preemptively killing healthy agents.

- **NATS server** gets the highest CPU quota (100% = 1 core) because message
  routing is latency-critical and the bus is the backbone.  Memory is
  conservatively capped at 256M; NATS is designed for low-memory operation
  (go-runtime, minimal per-connection state).

- **Health checker** gets the most restrictive profile (25% CPU, 128M, 32
  tasks) because it's a periodic polling script that runs briefly every 30s.

- **I/O-intensive units** (NATS, message-history, fleet) get IOAccounting=yes;
  other units skip it to reduce cgroup-v1 overhead.

## Files changed

| File | Change |
|------|--------|
| `systemd/agnetic-agent@.service.d/10-cgroup-limits.conf` | New: agent cgroup drop-in |
| `systemd/agnetic-staragent.service.d/10-cgroup-limits.conf` | New: staragent cgroup drop-in |
| `systemd/agnetic-dashboard.service.d/10-cgroup-limits.conf` | New: dashboard cgroup drop-in |
| `systemd/agnetic-status-bridge.service.d/10-cgroup-limits.conf` | New: status-bridge cgroup drop-in |
| `systemd/agnetic-message-history.service.d/10-cgroup-limits.conf` | New: message-history cgroup drop-in |
| `systemd/starship-fleet.service.d/10-cgroup-limits.conf` | New: fleet-manager cgroup drop-in |
| `systemd/starship-health-checker.service.d/10-cgroup-limits.conf` | New: health-checker cgroup drop-in |
| `systemd/agnetic-nats.service.d/10-cgroup-limits.conf` | New: NATS cgroup drop-in |
| `scripts/install-systemd.sh` | Install drop-ins alongside units |
| `scripts/build-deb.sh` | Stage drop-in directories + validate in package |
| `scripts/check-nightly.sh` | Section 20: cgroup drop-in checks |
| `tests/test_cgroup_limits.py` | New: 6 fixture tests for drop-in correctness |
| `tests/test_ci_assertions.py` | Section 20 presence assertion |
| `docs/solutions/asp-376-cgroups.md` | This document |

## Verification (git-only — no live systemd)

```bash
# All 8 drop-ins exist
for u in agnetic-agent@.service agnetic-message-history.service \
         agnetic-nats.service agnetic-dashboard.service \
         agnetic-staragent.service agnetic-status-bridge.service \
         starship-fleet.service starship-health-checker.service; do
  test -f "systemd/$u.d/10-cgroup-limits.conf" || echo "MISSING: $u"
done

# Agent drop-in has required keys
grep -q "CPUQuota=50%" systemd/agnetic-agent@.service.d/10-cgroup-limits.conf
grep -q "MemoryMax=512M" systemd/agnetic-agent@.service.d/10-cgroup-limits.conf
grep -q "TasksMax=128" systemd/agnetic-agent@.service.d/10-cgroup-limits.conf

# Syntax validation via systemd-analyze (requires systemd on host)
# systemd-analyze verify systemd/agnetic-agent@.service 2>/dev/null || true

# Fixture tests (6 tests, all pass)
python3 -m pytest tests/test_cgroup_limits.py -v
```

## Deployment

Drop-ins install to `/etc/systemd/system/<unit>.d/` (admin overrides) via
`install-systemd.sh`, which takes priority over `/usr/lib/systemd/system/`
and survives package upgrades.  For first-time install via DEB, drop-ins land
at `/lib/systemd/system/<unit>.d/` and are picked up by systemd automatically.

After deployment:
```
sudo systemctl daemon-reload
# Verify active limits:
systemctl show agnetic-agent@proxy | grep -E "(CPUQuota|MemoryMax|TasksMax)"
# Watch throttling:
systemd-cgtop
```
