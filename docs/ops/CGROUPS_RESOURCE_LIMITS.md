# Cgroup Resource Limits (ASP-376 / F-012)

CPU, memory, and PID (tasks) ceilings for every Starship OS service unit are
shipped as systemd **drop-ins** committed to the repo — they take effect on
install/reload on any node; nothing is applied to a live host by the repo
itself.

## How it works

Each unit `systemd/<unit>.service` has a matching drop-in
`systemd/<unit>.service.d/10-cgroup-limits.conf`. systemd merges `*.d/*.conf`
directories that sit on the unit search path, so the packaged units need no
modification:

- **.deb path** — `scripts/build-deb.sh` stages every `systemd/*.service.d/`
  directory into `lib/systemd/system/` (drop-in dirs resolve at the same search
  path level as the units).
- **dev/VM path** — `scripts/install-systemd.sh` copies each unit's drop-in to
  `/etc/systemd/system/<unit>.service.d/`. Because `/etc` has higher precedence
  than `/usr/lib`, operators can still pin their own overrides there.

## Knobs

| Knob | cgroup controller | What it does |
|------|-------------------|--------------|
| `MemoryMax=` | memory | hard ceiling; cgroup is OOM-killed above it |
| `MemoryHigh=` | memory | soft throttle; reclaim pressure applied above it (below `MemoryMax`) |
| `CPUQuota=` | cpu | absolute CPU cap as % of one core across the cgroup |
| `TasksMax=` | pids | hard cap on threads/processes the cgroup may spawn |
| `…Accounting=yes` | cpu/memory/tasks | explicit accounting so `systemctl show` reports usage |

## Per-unit limits

| Unit | Role | CPUQuota | CPUWeight | MemoryHigh | MemoryMax | TasksMax | IO |
|------|------|----------|-----------|-----------|-----------|----------|----|
| `agnetic-agent@.service` | agent daemon (each `%i` instance) | 50% | 100 | 384M | 512M | 128 | yes |
| `agnetic-message-history.service` | message persistence | 50% | 100 | 384M | 512M | 128 | yes |
| `agnetic-nats.service` | NATS bus | 100% | 200 | 192M | 256M | 256 | yes |
| `agnetic-dashboard.service` | web dashboard | 25% | 50 | 192M | 256M | 128 | no |
| `agnetic-staragent.service` | guard binary | 25% | 50 | 96M | 128M | 64 | no |
| `agnetic-status-bridge.service` | tray/status bridge | 25% | 50 | 96M | 128M | 64 | no |
| `starship-fleet.service` | fleet manager | 50% | 100 | 384M | 512M | 128 | yes |
| `starship-health-checker.service` | health probe | 25% | 25 | 96M | 128M | 32 | no |

Rationale: the node runs Ollama/llama-server outside these units, so agent
units (the per-instance orchestrators) share a moderate 50% profile with the
fleet manager so they cannot starve the host's LLM workers; NATS — the bus
backbone — gets one full core and the highest CPU weight; lightweight bridges
a quarter core. `TasksMax` bounds the pids-controller risk (leaked threads /
fork storms) the way NATS caps bound connection floods.

## Overriding

To raise a ceiling on one node, drop a higher-precedence file in `/etc`:

```ini
# /etc/systemd/system/agnetic-agent@.service.d/50-local.conf
[Service]
MemoryMax=2G
```

`/etc` beats `/usr/lib`, so install-systemd's copies do not clobber local pins.

## Verification

Static checks guard existence and bounds:

```bash
python3 -m pytest tests/test_cgroup_limits.py -v
bash scripts/check-nightly.sh        # Section 20
```

Live verification of effective values on a node where the units are installed
and running:

```bash
systemctl show agnetic-agent@proxy -p MemoryMax,MemoryHigh,CPUQuotaSec,TasksMax
systemd-analyze cat-config systemd/system/agnetic-agent@.service.d 2>/dev/null \
  | grep -E "MemoryMax|MemoryHigh|CPUQuota|TasksMax"
```