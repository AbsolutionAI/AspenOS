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

- aspen: accepts/rejects plans; closes only after local proof
- Opencode / Aspen Fast Coder: plan doc before code; hand `READY_FOR_AIDER_QA`
- Aider: test gate (`3dc7889f-57a8-4db1-b67b-ed044f88f2d0`)
- Auditor: security approve (`4203b00e-f928-49b2-a7b0-20ef3b103e40`)
- Review fail: comment CE-GATE: <criteria> and reopen to implementer

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
