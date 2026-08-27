# Plan: Hourly Implementation Sweep (ASP-479)

**Date:** 2026-08-25
**Issue:** [ASP-479](/ASP/issues/ASP-479)
**Source:** Recurring sweep

## Spec

- **Problem:** Open coding tasks need triage and forward progress. The implementation queue accumulates small well-scoped items that should be cleared rather than left to pile up.
- **Success criteria:**
  1. Identify at least one actionable item and make progress toward completion.
  2. Close or unblock at least one stalled/backlog task.
  3. Write compound learnings for recently completed work that lacks them.
  4. Clean up workspace state (stale branches, unmerged docs drift).
- **Out of scope:** Architecturally significant design decisions; new feature work that requires an upstream plan.

## Triage

### Candidate items for this heartbeat

1. **Stale path reference: `/opt/starship-os-build`**
   - `dashboard/server.py:37` and `src/python/lib/dashboard/server.py:41` reference `Path("/opt/starship-os-build/starship-os")` — this is a stale brand-era path from before the rename to `/opt/starship`. These paths were originally used during the starship-os build process and are no longer valid.
   - Fix: Replace with canonical `/opt/starship` path or remove the stale reference.

2. **Plan drift check**
   - Several older plan files (ASP-11, ASP-15, ASP-16) have unchecked acceptance checkboxes but the work appears to have been done through other initiatives (packaging hygiene, canonical root migration).
   - Check if dispositions need updating or if the plans should be marked superseded.

3. **Compound learning coverage check**
   - Verify last 5 non-docs commits have matching solution docs in `docs/solutions/`.

4. **Workspace hygiene**
   - Check for stale branches, untracked files, worktree artifacts.
   - Verify branch health for `hermes/asp-459-packaging-forward-port`.

## Disposition

### Done this heartbeat (2026-08-25)

1. **Stale path fix** — Replaced `/opt/starship-os-build/starship-os` → `/opt/starship` in `dashboard/server.py` and `src/python/lib/dashboard/server.py`.

2. **Plan drift assessment** — Reviewed 7 plan files (ASP-11, ASP-13, ASP-15, ASP-16, ASP-192, ASP-352, ASP-364) for stale checkboxes / dispositions. All are substantively completed or superseded: the code changes landed via `ox/packaging-hygiene` and the canonical root migration.

3. **Compound learning coverage** — All 5 non-docs commits on this branch have matching solution docs. No gaps.
   - **Updated:** Added `docs/solutions/asp-479-stale-starship-os-build-path.md` for the stale path fix commit.

4. **Workspace hygiene** — Repo clean. No untracked files, no stale worktrees, no branches with gone remotes. Forward-port branch is synced with origin/master.

### Items assessed with no action needed

- **Hashed Hermes remote branches** — 20x `origin/hermes/hermes-*` branches exist on remote, each with unique unmerged work. Not safe to prune.
- **Local branches** — All 5 local branches have active remote tracking; none are stale.
- **Compound learning** — Full coverage for last 5 non-docs commits.
