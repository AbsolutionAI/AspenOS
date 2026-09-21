# ASP-628 — Gatekeeper production packaging placement

**Status:** DONE (decision + docs)  
**Issue:** ASP-628 · Parent ASP-627  
**Date:** 2026-09-21

## Summary

Recorded packaging placement for monorepo `src/python/gatekeeper/` under ADR-0009 residual:

- **Production target:** plugin **`aspen-gatekeeper`** (ADR-0008 `plugin`)
- **Plant profile:** default **ON** when plant has actuators; OFF only for observation-only / Light-read
- **Not:** always-on core-edge second binary (keeps ADR-0004 light core)
- **Core residual:** `aspen-safety` + edge-rrm G8 dual-human unchanged
- **Deferred:** package extract, image matrix, durable token store (Redis/PG) — need Captain for prod image expand

## Artifacts

| Path | Role |
|------|------|
| `docs/plans/ASP-628-gatekeeper-packaging.md` | Decision + rationale |
| `docs/PACKAGES.md` | Classification row + plugin section |
| `docs/adr/ADR-0009-…` | Packaging residual line → ASP-628 |
| `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-09-21.md` | Re-landed from orphan ASP-627 commit + residual marked decided |

## Verification

- Docs-only; no production image / deb / ISO change
- No host policy apply
- Related hardening suites left green from prior local-proof (fleet ACL + tool anomaly)

## Out of scope (correctly deferred)

- Live JetStream consumer for tool-anomaly findings
- Redis/PG token backend
- Cutting the package repo / catalog install hook
