# Plan: ASP-353 — Deduplicate starship-health-checker.service

## Spec (required before code)
- **Problem:** `starship-health-checker.service` exists twice:
  - `systemd/starship-health-checker.service` — canonical; installed by
    `scripts/install-health-checker.sh`.
  - `config/starship-health-checker.service` — unreferenced near-duplicate
    (only deltas: longer Description, `# Security hardening` comment).
  Two copies drift independently (this already happened around the ASP-16 path
  fix, which had to patch both).
- **Success criteria:**
  1. Exactly one `starship-health-checker.service` remains in the repo
     (`systemd/`, referenced by the installer).
  2. No runtime references to `config/starship-health-checker.service` remain.
  3. Canonical unit keeps the more descriptive Description from the deleted copy.
- **Out of scope / unchanged:**
  - `config/cron.d/starship-health-checker` — distinct run mode (cron every
    2 min vs systemd every 30s), documented as an alternative in README;
    not a duplicate of the unit file.
  - Historical docs (`docs/plans/ASP-16-*`, `docs/solutions/asp-16-*`) — they
    record past state and stay as-is.

## Approach
1. Merge the richer Description into `systemd/starship-health-checker.service`.
2. Delete `config/starship-health-checker.service`.
3. Verify with grep + diff that no references remain and only one unit exists.
4. Commit with Paperclip co-author; no push (push auth still blocked per FOUNDATION).

## Files
- `systemd/starship-health-checker.service` (Description update)
- `config/starship-health-checker.service` (delete)

## Acceptance
- [x] Only one unit file in repo; installer still points at it
- [x] `rg "config/starship-health-checker.service"` returns no runtime hits
      (historical plan/solution docs may keep mentions)
- [x] Committed with disposition recorded on ASP-353

## Disposition (ASP-480 sweep — 2026-08-25)

**Status: Completed.** All acceptance criteria met. Only one unit file (`systemd/starship-health-checker.service`) remains in the repo. `config/starship-health-checker.service` was deleted. No runtime references remain. Implementation confirmed on current branch.
