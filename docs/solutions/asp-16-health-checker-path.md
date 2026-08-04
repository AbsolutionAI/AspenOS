# Learning: Health-checker runtime paths must match the canonical install layout

**Ticket:** ASP-16 (source: ASP-10 finding #10, flagged in ASP-15)

## Problem

`systemd/starship-health-checker.service`, `config/starship-health-checker.service`,
and `config/cron.d/starship-health-checker` all pointed `ExecStart` / cron at
`/opt/starship-os/scripts/agent-health-checker.py`. That path does not exist in
the canonical install layout: `install-daemon.sh` installs Python scripts to
`/opt/starship/lib/starship/scripts/` (e.g. `message_history.py`). Any unit or
cron entry referencing `/opt/starship-os/...` fails at runtime with the
executable not found.

## Fix

- Replaced `/opt/starship-os/scripts/agent-health-checker.py` with
  `/opt/starship/lib/starship/scripts/agent-health-checker.py` in all three
  runtime files (systemd unit, config copy, cron.d).
- Switched the interpreter to `/opt/starship/venv/bin/python3` so the checker's
  `aiohttp`/`PyYAML` deps resolve (matching `agnetic-message-history.service`).
- `scripts/install-health-checker.sh` now also installs
  `agent-health-checker.py` into `/opt/starship/lib/starship/scripts/` — the
  unit was previously registered with no backing script at all.
- Also cleaned the stale `/home/tech/agnetic-os/...` cron comment in
  `scripts/backup-cron.sh` (and its `src/python/lib/scripts/` duplicate).

## Patterns to reuse

1. **Canonical root is `/opt/starship`; scripts live at
   `/opt/starship/lib/starship/scripts/`.** When editing any unit in
   `systemd/` or `config/`, verify `ExecStart` paths against what
   `install-daemon.sh` / `debian/DEBIAN/postinst` actually install.
2. **Python systemd services should use the venv interpreter
   `/opt/starship/venv/bin/python3`**, not `/usr/bin/python3`, so bundled deps
   (aiohttp, PyYAML, nats-py) resolve.
3. **Dual copies exist** (`scripts/` and `src/python/lib/scripts/`). Keep path
   fixes mirrored across both (verified via `diff` → they were identical).

## Verification

- `grep -rn 'opt/starship-os' systemd config scripts src/python/lib/scripts` → no hits
- `bash -n` clean on `install-health-checker.sh`, both `backup-cron.sh` copies
- `python3 -m py_compile scripts/agent-health-checker.py` passes

## Related

- `docs/plans/ASP-16-health-checker-path-fix.md`
- Prior installer path fixes: `docs/solutions/asp-15-install-systemd-path.md`,
  `docs/solutions/asp-11-12-13-deb-upgrade-paths.md`
- Still open: `deploy/` stale units (finding #9) and
  `scripts/test-iso-auto.sh` embedded `/home/tech/agnetic-os` runcmd — both
  need an Architect decision.
