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

- aspen: accepts/rejects plans; closes only after local proof and the commit is on `origin/master`
- Opencode / Aspen Fast Coder: plan doc before code; hand off with the encoding below. Do not invent a status the API rejects
- Aider: test gate. Re-GET the id before assign (snapshot `3dc7889f-57a8-4db1-b67b-ed044f88f2d0`)
- Auditor: security approve. Re-GET the id before assign (snapshot `4203b00e-f928-49b2-a7b0-20ef3b103e40`)
- Review fail: comment `CE-GATE: <criteria>` and reopen to the implementer. Never silent re-code

## QA handoff encoding (ASP-744)

Agent-authored `in_review` is rejected unless a real review path exists: a pending issue-thread interaction, a linked pending approval, a human `assigneeUserId`, a typed `executionState.currentParticipant`, or a scheduled issue monitor. An agent assignee is not a review path.

```
PATCH {"status":"in_review","assigneeAgentId":"<agent>"}
→ 400 invalid_issue_disposition
```

Do not instruct that step. Do not work around the 400 by setting `blocked` with an empty `blockedBy`. That status reads as a dependency and the recovery resolver leaves it there (`blockedBy: []`), which freezes the parent. ASP-725 tracks the resolver default. Until that server change ships, use only the encoding below. It uses status transitions the API accepts today.

1. Implementer creates one QA-gate child. Assignee = Aider. Status = `todo`. Description carries the commit, files, tests, and the worktree cwd.
2. Implementer sets the parent `blocked` with `blockedByIssueIds` set to that child. Comment `READY_FOR_AIDER_QA` on the parent (files and tests). Never mark the parent `done`.
3. One `POST /api/agents/{aiderId}/heartbeat/invoke` for the child. Aider's process adapter does not auto-wake from assign. Do not invoke a second agent.
4. Aider pass: comment `AIDER_QA_PASS` plus counts. PATCH the gate `in_progress`, assignee = Auditor. Do not set `in_review`. Do not mark the gate `done` (security review has not happened). Do not set `blocked` with an empty blocker list.
5. Aider fail: comment `CE-GATE: <criteria>`. PATCH the gate `in_progress`, assignee = the implementer. Same prohibition on `in_review` and on empty `blocked`.
6. Auditor pass: comment `AUDITOR_APPROVE` with the checks. PATCH the gate `done`. That is the last agent gate. Do not set `in_review`. Do not set `blocked` with an empty blocker list. A comment with no status change is what the recovery resolver turns into `blocked: []`.
7. Auditor fail: `CE-GATE: <criteria>`, status `in_progress`, assignee = the implementer (or Aider if the hole is tests).
8. The parent wakes on `issue_blockers_resolved`. Aspen local-proofs. Aspen marks the parent `done` only when `git merge-base --is-ancestor <commit> origin/master` is true. Otherwise leave the parent `todo` and unassigned, and name the PR or branch. Do not mark `done` on agent comments alone.

Re-GET agent ids before every assign. A stale UUID is `404 Agent not found`.

`executionState.currentParticipant` and an issue monitor are also legal review paths. They are not the grove default: implementers do not have a typed execution policy to set, and a monitor does not wake Aider. Do not document them as the handoff.

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
