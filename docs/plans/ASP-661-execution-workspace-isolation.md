# ASP-661 execution workspace isolation — implementation plan

**Goal:** Make ADR-0013 true on the live AspenOS project without disturbing the shared workspace ASP-657 already holds.

**Architecture:** Paperclip `isolated_workspace` + `git_worktree`, per issue. No new worktree manager. No project-wide lock.

**Do not:** PATCH the project in the decision commit. Do not edit the primary checkout. Do not delete historical `docs/ops/nightly-results-*.md`. Do not remove the ASP-659 flock.

---

### Task 1: Apply execution workspace policy

**Objective:** New AspenOS issues realize a git worktree instead of the primary checkout.

**Blocked until:** No execution workspace on project AspenOS is `status=active` and `mode=shared_workspace`. On 2026-09-26 that is ASP-657 workspace `0afaf848-a778-40aa-b37a-1ac4579d60bf`.

**Precondition:** `origin/master` contains flock commit `3d88b1a` and the `.paperclip/` gitignore (ASP-658). Paperclip bases `master` on `origin/master` when that ref resolves. Do not cut the first worktree from a stale origin.

**Step 1: Re-GET**

`GET /api/projects/2f2b9b10-cfc4-423a-8d6f-ea8e54303b7f`

Confirm `executionWorkspacePolicy` is still null and list active execution workspaces. If any `shared_workspace` is still active, stop. Do not PATCH.

**Step 2: Quiet git identity**

If no other AspenOS heartbeat is running and `git config --local --get user.email` is `you@example.com`, unset local `user.name` and `user.email` so the global identity applies. Do not print other config. Do not do this if another run is committing.

**Step 3: PATCH the project**

```json
{
  "executionWorkspacePolicy": {
    "enabled": true,
    "defaultMode": "isolated_workspace",
    "allowIssueOverride": false,
    "workspaceStrategy": {
      "type": "git_worktree",
      "baseRef": "master",
      "branchTemplate": "{{issue.identifier}}-{{slug}}",
      "worktreeParentDir": ".paperclip/worktrees"
    }
  }
}
```

Use the board or agent API. Re-GET. The stored policy must match. A 200 that did not persist is not done.

**Step 4: Prove the next realization**

The follow-up issue's own continuation, or the next new issue, must show `currentExecutionWorkspace.strategyType=git_worktree` and a cwd under `.paperclip/worktrees/`, not the primary checkout. If the follow-up was created before the PATCH, create one fresh todo issue and confirm its workspace, then close that probe.

**Step 5: Comment the proof**

Policy JSON from the re-GET, the workspace id, and the cwd. No secrets.

### Task 2: Nightly results rolling file

**Objective:** New nightly runs update one tracked baseline and stop adding dated files.

**Base:** A tree that already has the ASP-659 concurrency section in `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md`. Do not re-apply that section from a stale branch.

**Files:**

- Create or overwrite: `docs/ops/NIGHTLY_LATEST.md`
- Modify: `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` reporting section only
- Do not modify: `scripts/check-nightly.sh` flock behavior
- Do not delete: `docs/ops/nightly-results-*.md`

**NIGHTLY_LATEST.md shape:**

```markdown
# Nightly latest

- Timestamp (UTC):
- Git SHA:
- Verdict: PASS or FAIL
- check-nightly: <pass>/<total>
- Deviations:
- Issue:
```

**Runbook change:** Reporting step points at this file plus the issue comment. Explicit line: do not add a new `docs/ops/nightly-results-*.md`.

**Done when:** A dry read of the runbook cannot be followed into creating another dated results file, the flock section is still present, and `NIGHTLY_LATEST.md` exists with the fields above (a placeholder is enough if no nightly is due this wake).

### Verification

- `git check-ignore -v .paperclip/worktrees` matches the ASP-658 ignore, on the base ref the policy will use.
- Policy re-GET matches Task 1.
- No active shared workspace remains before the PATCH.
- Runbook diff does not remove the flock section.
