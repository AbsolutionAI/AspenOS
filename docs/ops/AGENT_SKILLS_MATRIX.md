# Paperclip agent skills matrix

**Updated:** 2026-08-04

Company skill libraries: full Paperclip catalog installed (18 skills/co; ramp skipped).
Per-agent assignment via `POST /api/agents/{id}/skills/sync` + `desiredSkills`.

## Assignment
- **Absolution Studios / Reflection Coach** (`claude_local`): reflection-coach, paperclip
- **Absolution Studios / Summarizer** (`claude_local`): summarize-status, paperclip
- **Bellah Content Studio / Content Lead** (`hermes_local`): paperclip, release-announcement, last30days, design-critique, task-planning, issue-triage, doc-maintenance, agent-browser, wireframe
- **Bellah Content Studio / Reflection Coach** (`claude_local`): reflection-coach, paperclip
- **Bellah Content Studio / Summarizer** (`claude_local`): summarize-status, paperclip
- **Bellah Content Studio / Pipeline Ops** (`hermes_local`): paperclip, task-planning, agent-browser, qa-acceptance, doc-maintenance, para-memory-files
- **Aspen OS Development Company / Agent Zero** (`process`): _none — process adapter_
- **Aspen OS Development Company / Reflection Coach** (`claude_local`): reflection-coach, paperclip
- **Aspen OS Development Company / Summarizer** (`claude_local`): summarize-status, paperclip
- **Aspen OS Development Company / Dashboard** (`hermes_local`): paperclip, design-critique, wireframe, doc-maintenance, agent-browser, paperclip-capsules, task-planning
- **Aspen OS Development Company / robotics** (`hermes_local`): paperclip, paperclip-converting-plans-to-tasks, para-memory-files, task-planning, issue-triage, doc-maintenance, github-pr-workflow
- **Aspen OS Development Company / Runtime** (`hermes_local`): paperclip, paperclip-converting-plans-to-tasks, para-memory-files, task-planning, issue-triage, doc-maintenance, github-pr-workflow
- **Aspen OS Development Company / Auditor** (`hermes_local`): paperclip, issue-triage, qa-acceptance, doc-maintenance, task-planning, para-memory-files, agent-browser
- **Aspen OS Development Company / packndeploy** (`hermes_local`): paperclip, paperclip-converting-plans-to-tasks, para-memory-files, task-planning, issue-triage, doc-maintenance, github-pr-workflow
- **Aspen OS Development Company / Aspen Fast Coder** (`opencode_local`): paperclip, paperclip-converting-plans-to-tasks, para-memory-files, github-pr-workflow, qa-acceptance, doc-maintenance, agent-browser, task-planning, issue-triage, wireframe
- **Aspen OS Development Company / aspen** (`hermes_local`): paperclip, paperclip-board, paperclip-create-agent, paperclip-converting-plans-to-tasks, para-memory-files, issue-triage, task-planning, summarize-status, reflection-coach, doc-maintenance, github-pr-workflow, qa-acceptance, agent-browser, design-critique +4
- **Aspen OS Development Company / Opencode** (`opencode_local`): paperclip, paperclip-converting-plans-to-tasks, para-memory-files, github-pr-workflow, qa-acceptance, doc-maintenance, agent-browser, task-planning, issue-triage, wireframe
- **Aspen OS Development Company / Compliance** (`hermes_local`): paperclip, issue-triage, qa-acceptance, doc-maintenance, task-planning, para-memory-files, agent-browser
- **Aspen OS Development Company / Aider** (`process`): _none — process adapter_
- **Absolution Digital Commerce / Digital Marketer** (`hermes_local`): paperclip, release-announcement, last30days, design-critique, summarize-status, task-planning, issue-triage, doc-maintenance, agent-browser
- **Absolution Digital Commerce / Digital CEO** (`hermes_local`): paperclip, paperclip-board, paperclip-create-agent, paperclip-converting-plans-to-tasks, para-memory-files, issue-triage, task-planning, summarize-status, reflection-coach, doc-maintenance
- **Absolution Digital Commerce / Digital Packager** (`opencode_local`): paperclip, paperclip-converting-plans-to-tasks, para-memory-files, github-pr-workflow, qa-acceptance, doc-maintenance, agent-browser, task-planning, issue-triage, wireframe
- **Absolution Digital Commerce / Reflection Coach** (`claude_local`): reflection-coach, paperclip
- **Absolution Digital Commerce / Summarizer** (`claude_local`): summarize-status, paperclip
- **Absolution Digital Commerce / Digital CTO** (`hermes_local`): paperclip, paperclip-board, paperclip-create-agent, paperclip-converting-plans-to-tasks, para-memory-files, issue-triage, task-planning, summarize-status, reflection-coach, doc-maintenance, github-pr-workflow, qa-acceptance, agent-browser

## Role recipes
- **Architect (aspen):** full board + engineering + design + research suite
- **CEO/CTO:** board ops + planning/triage + core paperclip
- **Coder (OpenCode/Packager):** github-pr, qa, browser, docs, task-planning
- **Marketer/Content:** release-announcement, last30days, design
- **Auditor/Compliance:** qa, triage, browser, docs
- **Process (Aider/A0):** skill sync unsupported — host tools + AGENTS.md note

## Tools connections
No external MCP tool connections installed yet (gallery available).
Hermes profile tools/MCP remain separate (e.g. Linear on aspen).
