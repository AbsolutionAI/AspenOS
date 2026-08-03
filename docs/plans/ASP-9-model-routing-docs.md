# Plan: ASP-9 commit model-routing documentation

## Problem
The working tree holds uncommitted model-routing docs from the 2026-08-03 model
rationalization (local Ollama retired for Paperclip heartbeats; aspen → Grok 4.5,
domain Hermes agents → DeepSeek V4-Flash, OpenCode/Aider → DeepSeek V4-Flash):

- `docs/FOUNDATION.md` — model routing summary section added
- `docs/MODEL_ROUTING.md` — new full routing table + budget + escalate ladder

These are coherent, self-contained docs that should be committed so the routing
decision is durable (mirrors the ASP-8 checkbox-sync pattern).

## Approach
1. Write this plan first (no edits before it).
2. Commit the two doc files with Paperclip co-author.
3. Do not push (GitHub push auth is an open follow-up, `[ ] GitHub auth for push/PR`).

## Files
- `docs/plans/ASP-9-model-routing-docs.md` (this file)
- `docs/MODEL_ROUTING.md` (new)
- `docs/FOUNDATION.md` (model routing section)

## Non-goals
- No runtime/agent code changes
- No push/PR (auth follow-up stays open, owned by aspen)
- No new routing decisions — capturing the state already in the tree

## Acceptance
- [ ] Plan file written before commit
- [ ] `docs/MODEL_ROUTING.md` committed
- [ ] `docs/FOUNDATION.md` model routing section committed
- [ ] ASP-9 swept with a summary comment
