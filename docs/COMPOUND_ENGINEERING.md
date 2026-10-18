# Compound Engineering (SDLC gates) — Aspen OS

**Linear:** BEL-133  
**Plugin install:** Every Inc Compound Engineering for OpenCode at ~/.config/opencode/ (skills ce-*, agents ce-*).

## Non-negotiable pipeline

Coding work must not jump to file edits. Enforce:

1. Problem Discovery (ce-brainstorm / ce-ideate)
2. Tech Evaluation / Architecture (ce-plan) — write docs/plans/<ticket>.md
3. Implementation (ce-work) — only after plan exists — **OpenCode**. Never `done` here.
4. **Aider QA** — run/add tests; surgical test fixes; `AIDER_QA_PASS` or `CE-GATE`
5. **Auditor approve** — security/threat-model; `AUDITOR_APPROVE` or `CE-GATE`. Never `done`.
6. Compound (ce-compound) — docs/solutions/ learnings
7. **aspen** local tree+test proof → `done`

Captain 2026-09-07: Aider and Auditor jointly gate all produced code. One wake at a time.

## Paperclip enforcement

- aspen: accepts/rejects plans; closes a code parent only after local proof and the commit is on `origin/master`
- Opencode / Aspen Fast Coder: plan doc before code; hand off with the encoding below. Do not invent a status the API rejects
- Aider: test gate. Re-GET the id before assign (snapshot `3dc7889f-57a8-4db1-b67b-ed044f88f2d0`)
- Auditor: security approve. Re-GET the id before assign (snapshot `4203b00e-f928-49b2-a7b0-20ef3b103e40`). Never sets the gate `done` (CHG-0029)
- Review fail: comment `CE-GATE: <criteria>` and reopen to the implementer. Never silent re-code

## QA handoff encoding (ASP-744, corrected ASP-773 / CHG-0029)

Agent-authored `in_review` plus an agent assignee is `400 invalid_issue_disposition`. An agent assignee is not a review path. Do not work around that 400 by setting `blocked` with an empty `blockedBy`. ASP-725 tracks the resolver default. Until it ships, use only this encoding.

1. Implementer creates one QA-gate child. Assignee = Aider. Status = `todo`. Description carries the commit, files, tests, and the worktree cwd.
2. Implementer sets the parent `blocked` with `blockedByIssueIds` set to that child. Comment `READY_FOR_AIDER_QA` on the parent. Never mark the parent `done`.
3. One Aider invoke for the child. The process adapter does not auto-wake from assign. Do not invoke a second agent.
4. Aider pass: comment `AIDER_QA_PASS` plus counts. PATCH the gate `in_progress`, assignee = Auditor. Do not set `in_review`. Do not mark the gate `done`. Do not set `blocked` with an empty blocker list.
5. Aider fail: comment `CE-GATE: <criteria>`. PATCH the gate `in_progress`, assignee = the implementer.
6. Auditor pass: comment `AUDITOR_APPROVE` with the checks. PATCH the gate `in_progress`, assignee = aspen. Auditor never sets `done`. A comment with no status change is what the recovery resolver turns into `blocked: []`.
7. Aspen runs `auditor-evidence-check.py`. A non-zero exit voids the approval: comment `CE-GATE: auditor evidence check failed` and hand the gate back to Auditor `in_progress`. Never local-proof a failed check.
8. Aspen posts `LOCAL_PROOF` (issue, pr, head, cwd, command, exit, output tail). Only then may Aspen set the gate `done`.
9. Parent `done` only when local proof exists and `git merge-base --is-ancestor <commit> origin/master` is true.

PR 64 step 6 (Auditor sets the gate `done`) is superseded. Do not merge that PR.

Re-GET agent ids before every assign. A stale UUID is `404 Agent not found`.

## Ticket template

## Spec (required before code)
- Problem:
- Success criteria:
- Plan doc: docs/plans/BEL-N.md
- Out of scope:

## Implementation
## QA


## Proof run (ASP-3 / BEL-133)

- **When:** 2026-08-03T19:49:18Z
- **Plan first:** `docs/plans/ASP-3-ce-gate-proof.md`
- **Result:** CE gate demonstrated — plan file created before this section was appended.
- **OpenCode CE:** installed at `~/.config/opencode/` (ce-brainstorm, ce-plan, ce-work, ce-code-review, ce-compound, …)
- **Paperclip:** coding agents AGENTS.md updated with mandatory CE pipeline; failed reviews use `CE-GATE:` reopen comments.
