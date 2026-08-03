# Plan: ASP-8 FOUNDATION.md checkbox sync

## Problem
`docs/FOUNDATION.md` `## Known follow-ups` still shows `[ ] Agent Zero docker image pull + UI config (ASP-6)` but ASP-6 is `done` (board closed 2026-08-03T20:18Z after verifying image, container on 127.0.0.1:50080, UI HTTP 200). The snapshot is out of sync with the queue.

## Approach
1. Write this plan first (no edits before it).
2. Update `docs/FOUNDATION.md` Known follow-ups checkbox for ASP-6 to `[x]`.
3. Commit with Paperclip co-author, comment summary on ASP-8.

## Files
- `docs/plans/ASP-8-foundation-checkbox-sync.md` (this file)
- `docs/FOUNDATION.md` (checkbox only)

## Non-goals
- No runtime/agent code changes
- No new follow-up tickets (GitHub auth, Google Workspace OAuth, BEL-135+ stay as open follow-ups owned by aspen)

## Acceptance
- [ ] Plan file written before FOUNDATION.md edit
- [ ] ASP-6 checkbox reflects `[x]`
- [ ] Commit present, ASP-8 swept and closed
