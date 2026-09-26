# ADR-0013: Per-issue git worktree execution workspaces

**Status:** Accepted — 2026-09-26  
**Paperclip:** ASP-661 (parent ASP-657)  
**Linear:** [BEL-316](https://linear.app/bellahtech/issue/BEL-316/adr-0013-per-issue-git-worktree-execution-workspaces-asp-661)  
**Review:** Architect decision on ASP-661. This record is the review. Live policy flip is a follow-up, not this ADR's commit.  
**Related:** ASP-659 flock (`3d88b1a`, local master, not yet on `origin/master`) · ASP-658 `.paperclip/` gitignore · ASP-660 runbook baseline

---

## Context

Paperclip runs for project AspenOS share one execution workspace:

- Project workspace cwd: `/home/tech/projects/aspen-dev/repos/aspen-os`
- Issue preference observed on ASP-661: `reuse_existing`
- Settings mode: `shared_workspace`
- Realized strategy: `project_primary`
- Active example: ASP-657 execution workspace `0afaf848-a778-40aa-b37a-1ac4579d60bf`, cwd = that primary checkout

That is not theoretical. One sweep produced two failures:

1. Two `scripts/check-nightly.sh` runs overlapped in the same tree. The checks mutate in-tree state (`scripts/build-deb.sh` removes `PKG_ROOT`; section 3 relinks C11 binaries). Each run reported the other's damage as failures. ASP-659 added an flock on that one script. It does not cover `make`, pytest, ISO smoke, or two agents editing the same files.
2. ASP-659 was checked out by a second run of the same agent while the first run still held it. The second commit landed without a work product from the first run (HTTP 409 `Issue run ownership conflict`). They converged by luck.

Secondary: repo-local `user.name` / `user.email` is the placeholder `Your Name <you@example.com>`, which overrides the global identity. Recent commits, including ones on this host, use that placeholder. Do not treat that as the intended author.

Hermes CLI sessions already create `.worktrees/hermes-*`. That is a different layer. It does not change Paperclip's execution cwd. Agents and the nightly script mutate the primary checkout.

Paperclip already implements the isolation this ticket asked for. It is not turned on.

| Knob | Values | AspenOS today |
|------|--------|----------------|
| `executionWorkspacePolicy.defaultMode` | `shared_workspace`, `isolated_workspace`, `operator_branch`, `adapter_default` | unset (issues fall through to `shared_workspace`) |
| `workspaceStrategy.type` | `project_primary`, `git_worktree`, `adapter_managed`, `cloud_sandbox` | realized `project_primary` |
| Branch template default | `{{issue.identifier}}-{{slug}}` | unused |
| Worktree parent default | `<repo>/.paperclip/worktrees` | unused |

Realization, reuse, base refresh, and close (`git_worktree_remove`, and `git_branch_delete` for runtime-created branches) already exist in the Paperclip server. Inventing a second worktree manager would split the grove.

Nightly results are a related maintenance leak. This worktree tracks 25 `docs/ops/nightly-results-*.md` files. The primary checkout has more, including several from the same calendar day. Each new file is another commit on the shared branch, which is the race above. The runbook already requires a results comment on the run issue. The dated files are a second copy with a real git cost.

## Decision

### 1. Isolation: per-issue git worktree (option 1, product mechanism)

AspenOS agent execution uses Paperclip `isolated_workspace` + `git_worktree`.

Not option 2. A project-wide workspace lock would stop the corruption by serializing every ticket, including ones that do not touch the same files. Captain's one-wake rule on a critical path stays a pipeline rule. It is not a substitute for isolation. Nightlies and implementation overlap by design.

Not option 3. Convention failed inside one sweep.

Not a new per-run worktree lifecycle. Paperclip isolates **per issue** and reuses that worktree across continuations (`reuse_existing`, branch `{{issue.identifier}}-{{slug}}`). A per-run tree would fight that reuse and multiply branches for one ticket. Same-issue overlap is a checkout problem plus the ASP-659 flock, not a second tree.

Hermes `.worktrees/hermes-*` does **not** satisfy this ADR.

Target project policy (apply in the follow-up, not in this commit):

```json
{
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
```

`allowIssueOverride: false` so an agent cannot flip a ticket back to the shared checkout. A board PATCH of one issue is the exception, not the default.

`baseRef: master` is the integration branch name. Paperclip resolves a local branch to `origin/<name>` when that remote-tracking ref exists. On 2026-09-26 local `master` was 6 commits ahead of `origin/master` (including the flock and the `.paperclip/` gitignore). A worktree cut from `origin/master` before those commits are pushed will miss them. The policy follow-up must confirm `origin/master` contains `3d88b1a` (flock) and the `.paperclip/` gitignore before the first isolated run, or the new trees fork stale.

Worktree parent is `.paperclip/worktrees`, not `.worktrees/`. ASP-658 gitignores `.paperclip/`. Do not commit worktree contents.

### 2. Primary checkout is integration-only after the flip

After the policy is live, agents do not edit, build, or run mutating scripts in `/home/tech/projects/aspen-dev/repos/aspen-os` on `master`.

That includes `make`, `scripts/build-deb.sh`, `scripts/check-nightly.sh`, pytest that writes under the tree, and any file edit. Those run inside the issue worktree.

Merge-back, before workspace close:

1. QA gates (Aider, Auditor, architect local-proof) finish on the issue branch.
2. The closing run merges that branch into `master` (fast-forward or a merge commit) from the issue worktree or a short-lived merge step.
3. Only then may the execution workspace close. Close plans `git worktree remove --force` and, for runtime-created branches, `git branch -d`. Closing first deletes the branch that has not been merged.

Do not commit implementation directly onto `master` from the primary checkout. That is the bug.

### 3. Same-issue overlap stays guarded

A per-issue worktree does not stop two runs of the same issue. ASP-659's flock on `/tmp/starship-nightly.lock` stays. Do not remove it when the policy flips.

Operator rule: do not invoke a second heartbeat on an issue whose `checkoutRunId` is already set. The 409 on ASP-659 was a stolen checkout, not a missing flock. This repo does not patch Paperclip's checkout service. The rule is the control.

### 4. Git identity

Repo-local `user.name=Your Name` and `user.email=you@example.com` is a defect. It is shared `.git/config`, so every worktree inherits it.

Do not change that config while other heartbeats are committing. The policy follow-up, in a quiet window (no other AspenOS heartbeat running), unsets the local placeholder so the global identity applies. Until then, any commit this decision requires uses an explicit `git -c user.name=aspen -c user.email=aspen@bellahtech.com` and does not write the shared config.

### 5. Nightly results: rolling file + issue artifact

Stop adding `docs/ops/nightly-results-YYYY-MM-DD*.md` to git.

| What | Where |
|------|--------|
| Baseline the next run and a human diff | One tracked file, `docs/ops/NIGHTLY_LATEST.md` (overwrite in place: verdict, pass/fail counts, deviations, git SHA, timestamp) |
| Run record the assignee wakes on | Issue comment, as the runbook already requires |
| Full transcript | Paperclip work product on that issue, not a new dated file |

Existing dated files stay. Do not mass-delete them in the decision commit. They are history. A later prune is optional and out of scope.

The nightly owner commits `NIGHTLY_LATEST.md` on the nightly issue branch, then merges with that issue. It does not commit a new dated file onto `master` from the primary checkout.

## Consequences

- Cross-ticket corruption of `PKG_ROOT`, C11 binaries, and the git index stops once the policy is live, because those writes happen in different worktrees.
- Parallel tickets can run. Same-issue double-invoke can still collide. Flock + checkout rule cover that.
- `master` moves only by merge-back. Unmerged close deletes the work. The follow-up must say that in the implementer prompt.
- First isolated runs are wrong if `origin/master` is behind local `master`. Push hygiene is a precondition, not a side effect of this ADR.
- Dated nightly files stop accumulating. The runbook baseline table (ASP-660) should be compared against `NIGHTLY_LATEST.md`, not against whichever dated file an agent happens to open.
- This commit does **not** PATCH the project. ASP-657 still holds the shared workspace. Flipping the default while that workspace is active can make a continuation resolve a different cwd than the persisted one (`persisted_cwd_mismatch` / `git_worktree_provider_ref_mismatch`).

## Alternatives considered

| Option | Why not |
|--------|---------|
| Project-wide checkout lock | Stops the race by forbidding parallel tickets. Nightly vs implementation would queue. Paperclip already has issue checkout; the hole is the shared tree, not the absence of a coarser lock. |
| Convention only | Failed in the sweep that opened this ticket. |
| Custom per-run worktree script | Duplicates Paperclip `realizeExecutionWorkspace`. Two managers, two cleanup paths. |
| Hermes `.worktrees/hermes-*` as the control | Session isolation for this CLI. Paperclip adapters still receive the project execution cwd. |
| Keep dated nightly files | Same-day duplicates already exist. Each file is another shared-branch commit. |
| Attachments only, no in-repo baseline | ASP-660 exists because the runbook baseline went stale. One rolling file is the diff target. Attachments are the audit trail. |

## Follow-ups (not this commit)

1. Apply the project policy after no active `shared_workspace` execution workspace remains on AspenOS. Confirm `origin/master` contains the flock commit and `.paperclip/` gitignore first. Unset the placeholder git identity in that quiet window. Assignee: aspen. Blocked by ASP-657 while `0afaf848` is active.
2. Point the nightly runbook at `NIGHTLY_LATEST.md`. Stop writing new dated results files. Keep the flock. Implement from a tree that already has the ASP-659 runbook section, not from a stale `origin/master` worktree.

Plan: `docs/plans/ASP-661-execution-workspace-isolation.md`.
