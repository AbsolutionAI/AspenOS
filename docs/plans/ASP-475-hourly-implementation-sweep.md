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

## Implementation order

1. Assess existing compound learnings for gaps (check asp-463-ci-assertion-hardening.md for coverage of latest CI hardening).
2. Write missing compound learning for CI assertion hardening v2 if needed.
3. Write compound learning for NATS credential scrub (ASP-365) if missing.
4. Assess stale hermetic branches for cleanup.
5. Post disposition on ASP-475.
