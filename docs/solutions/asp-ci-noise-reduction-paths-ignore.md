# CI noise reduction: paths-ignore + concurrency groups

**Date:** 2026-08-25
**Tickets:** ASP-463 (CI inbox review), ASP-474 (hourly sweep)

## Problem

The Starship OS CI workflow fired on every push and pull request to master,
including docs-only changes. With 20+ open Hermes PRs (many docs-only), this
generated 43 of 50 unread GitHub notifications — all false-positive failures
from rebuilds of stale PR tips that had not been rebased onto latest master.

## Solution

Two changes to `.github/workflows/ci.yml`:

1. **`paths-ignore`** — Skip `docs/**` and `**/*.md` on push events. Docs-only
   commits no longer waste CI minutes or generate CheckSuite notifications.

2. **`concurrency` group** — Group by workflow + ref, cancel-in-progress.
   When a new commit is pushed to a PR branch, the previous in-progress run
   is cancelled immediately instead of both running to completion.

## Reflection

This is a low-cost, high-impact fix: two YAML blocks eliminated the dominant
source of CI noise. The inbox review doc (`docs/ops/GITHUB_CI_INBOX_REVIEW_2026-08-25.md`)
correctly identified paths-ignore and concurrency as "highest leverage" items.

## Files changed

- `.github/workflows/ci.yml` — `paths-ignore` on push events + `concurrency`
  stanza

## Related

- ASP-463 (CI assertion hardening — complementary fix for NATS + sandbox_run)
- `docs/ops/GITHUB_CI_INBOX_REVIEW_2026-08-25.md` — full inbox analysis