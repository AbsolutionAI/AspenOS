# Stale `/opt/starship-os-build` path fallback cleanup

**Date:** 2026-08-25
**Tickets:** ASP-479 (hourly implementation sweep)

## Problem

Two `server.py` files (dashboard and Python lib dashboard) had a stale `Path("/opt/starship-os-build/starship-os")` branch in their `PROJECT_DIR` fallback chain. This path was a remnant from the brand-era "starship-os" naming convention — the canonical root is now `/opt/starship`. Leaving it in the fallback list is noise at best and a deployment hazard at worst (it could mask a missing canonical root).

## Solution

Replaced `/opt/starship-os-build/starship-os` with `/opt/starship` in both files:

- `dashboard/server.py:37`
- `src/python/lib/dashboard/server.py:41`

This is a one-line change per file — `s|starship-os-build/starship-os|starship|`.

## Affected files

| File | Before | After |
|------|--------|-------|
| `dashboard/server.py` | `Path("/opt/starship-os-build/starship-os")` | `Path("/opt/starship")` |
| `src/python/lib/dashboard/server.py` | `Path("/opt/starship-os-build/starship-os")` | `Path("/opt/starship")` |

## Reflection

The stale path was easy to find via grep (`starship-os-build` only appeared in these two locations) but easy to miss in review because `server.py` has been refactored several times since the brand rename. A broader cleanup of brand-era naming residues across the codebase is probably warranted, but this fix addresses the only production-relevant instance — everything else is in git history, archive files, or obsolete docs.
