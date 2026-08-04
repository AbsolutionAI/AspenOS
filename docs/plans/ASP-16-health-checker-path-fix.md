# Plan: ASP-16 — Fix health-checker stale `/opt/starship-os` path (ASP-10 finding #10)

## Spec (required before code)
- **Problem:** Three runtime files reference a non-existent install location
  `/opt/starship-os/scripts/agent-health-checker.py`:
  - `systemd/starship-health-checker.service`
  - `config/starship-health-checker.service`
  - `config/cron.d/starship-health-checker`
  The canonical script install directory is `/opt/starship/lib/starship/scripts`
  (see `install-daemon.sh` "Scripts" step; `message_history.py` lands there). A
  systemd unit or cron entry pointing at `/opt/starship-os/...` will fail with
  `ExecStart` not found. Flagged as MEDIUM finding #10 by the ASP-10 audit;
  explicitly left out of scope in ASP-15.
- **Success criteria:**
  1. All three runtime files reference the canonical script path
     `/opt/starship/lib/starship/scripts/agent-health-checker.py`.
  2. `scripts/install-health-checker.sh` also installs
     `agent-health-checker.py` into that canonical scripts directory so the
     unit actually starts.
  3. No `/opt/starship-os` hits remain in any runtime (`systemd/`, `config/`,
     `scripts/`) file.
  4. `bash -n` clean on edited shell scripts; Python file still compiles.
- **Plan doc:** docs/plans/ASP-16-health-checker-path-fix.md (this file)
- **Out of scope:** `deploy/` stale developer units (ASP-10 finding #9 —
  architectural decision delete vs keep; escalate to Architect),
  `scripts/test-iso-auto.sh` embedded `/home/tech/agnetic-os` runcmd
  (dev-machine test harness; escalate), `src/python/lib/dashboard/server.py`
  `_CANDIDATES` stale `/opt/starship-os-build` entry (harmless fallback, no
  runtime failure), GitHub push auth.

## Approach
1. Write this plan first (CE gate).
2. In `systemd/starship-health-checker.service`, `config/starship-health-checker.service`,
   and `config/cron.d/starship-health-checker`: replace
   `/opt/starship-os/scripts/agent-health-checker.py` with
   `/opt/starship/lib/starship/scripts/agent-health-checker.py`.
3. In `scripts/install-health-checker.sh`: after copying the unit, copy
   `$REPO_DIR/scripts/agent-health-checker.py` to
   `/opt/starship/lib/starship/scripts/`, `chmod +x`, and keep the
   `/var/lib/starship` setup. Note that the health checker resolves its
   `PROJECT_DIR` as `parent.parent` of the script, so installed at
   `/opt/starship/lib/starship/scripts/` it finds agents under
   `/opt/starship/lib/starship/agents` — matching the canonical layout.
4. Fix the stale `/home/tech/agnetic-os` cron-comment in `scripts/backup-cron.sh`
   (and its duplicate `src/python/lib/scripts/backup-cron.sh`) to the
   canonical `/opt/starship/lib/starship/scripts/backup-cron.sh` path.
5. Verify: `bash -n` on edited shell scripts; `python3 -m py_compile` on the
   checker; `grep -rn 'opt/starship-os' systemd config scripts src/python/lib/scripts`
   returns no runtime hits (plan/learning docs may reference the old path).
6. Commit with Paperclip co-author (`Co-Authored-By: Paperclip <noreply@paperclip.ing>`).
   No push (GitHub push auth is still blocked per FOUNDATION).

## Files
- `docs/plans/ASP-16-health-checker-path-fix.md` (this file)
- `systemd/starship-health-checker.service`
- `config/starship-health-checker.service`
- `config/cron.d/starship-health-checker`
- `scripts/install-health-checker.sh`
- `scripts/backup-cron.sh` (+ duplicate `src/python/lib/scripts/backup-cron.sh`)
- `docs/solutions/asp-16-health-checker-path.md` (compound learning)

## Non-goals
- No deletion/decision on `deploy/` stale units (Architect).
- No changes to `scripts/test-iso-auto.sh` embedded paths (Architect).
- No changes to dashboard `_CANDIDATES` fallback list.

## Acceptance
- [ ] Plan written before code edits
- [ ] `grep -rn 'opt/starship-os'` in runtime dirs returns nothing
- [ ] `install-health-checker.sh` installs the script to the canonical path
- [ ] `bash -n` clean on all edited shell scripts
- [ ] Python file compiles
- [ ] Working tree clean after commit; ASP-16 disposition recorded
