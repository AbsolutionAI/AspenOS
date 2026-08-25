# Plan: Hourly Implementation Sweep (ASP-475)

**Date:** 2026-08-25
**Issue:** [ASP-475](/ASP/issues/ASP-475)
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

1. **Compound learning: CI assertion hardening (commit `eb5879b` + `236f7b1`)**
   - Two CI hardening commits exist: one that hardens NATS install and sandbox_run assertions (`eb5879b`), and one that hardens NATS PATH and C11 help assertions (`236f7b1`). Compound learning `asp-463-ci-assertion-hardening.md` exists but may need updating to cover the second hardening batch.
   - **Check** if existing solution doc covers both changes.

2. **Compound learning: NATS credential scrub (commit `191020e`, ASP-365/H-017)**
   - Security fix that scrubs hardcoded NATS credentials from `server.conf`. Compound learning exists for ASP-169/170/171/172/173/417 but ASP-365 specific learning may be partial or absent.

3. **Compound learning: fleet D1 cell profile seeds (commit `75417c9`, ASP-381/BEL-192)**
   - Plant-range D1 cell profile seeds for G6/G7 were merged. Compound learning for BEL-192 G5/G6/G7 may be needed.

4. **Packaging forward-port branch health check**
   - `hermes/asp-459-packaging-forward-port` is the current branch. Check if any commits need to be merged to master or if branch needs reconciliation.

5. **Stale branch assessment**
   - Many `hermes/hermes-*` branches (orphan hash-named branches from prior sessions). Check if they are fully contained in other branches or can be cleaned.

6. **Check for plan drift** — verify that existing plans reference correct issue IDs, branch names, and that their dispositions are recorded.

## Disposition (completed 2026-08-25)

### Done this heartbeat

1. **Compound learning: fleet D1 cell profile seeds** — Added `docs/solutions/asp-381-plant-range-d1-cell-profile.md` covering the D1 cell profile YAML, hold-to-enable runbook, estop audit drill runbook, sim profile contract script, fleet ACL integration, and plant-range robotics role. (commit `75417c9`)

2. **Stale branch cleanup** — Deleted 10 local branches that were fully merged into HEAD: `asp-169`, `asp-171`, `asp-172`, `asp-173`, `asp-174`, `asp-36`, `asp-364`, `asp-384`, `asp-417`, and `hermes/asp-364-dual-human-wire`.

### Previously completed (commit `95daac9`)

3. **Compound learning: ASP-365 NATS credential scrub** — Added `docs/solutions/asp-365-nats-credential-scrub.md`.
4. **Compound learning: ASP-463 CI hardening v2** — Updated `docs/solutions/asp-463-ci-assertion-hardening.md` for contract tests.
5. **CI noise reduction learning** — `asp-ci-noise-reduction-paths-ignore.md` already present.

### Items assessed with no action needed

- **Packaging forward-port branch health** — `hermes/asp-459-packaging-forward-port` is ahead of `origin/master` by 30 commits (all features, fixes, and docs). No merge conflicts; no reconciliation needed. The branch is the active development branch.

- **Stale origin `hermes/hermes-*` branches** — 20 orphan hash-named branches on origin. These are stale worktree artifacts from prior Hermes sessions. Cannot delete remote branches without confirmation — flagged for future sweep.

### Not actionable this heartbeat

- ASP-454 (backlog starship-health-checker deb) — already resolved by `48d5b57` on this branch. Can be closed.
