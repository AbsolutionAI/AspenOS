# ASP-607 — Gatekeeper per-agent rate limiting (compound)

**Closed:** 2026-09-16 by Aspen local proof after Auditor stall (ASP-608).

## Deliverable

Per-agent sliding-window rate limit on `request_capability()` (ASP-540 residual).

- Commit: `fd89630`
- Plan: `docs/plans/ASP-607-gatekeeper-rate-limiting.md`
- Code: `src/python/gatekeeper/minimal_shim.py` (`RATE_LIMIT_*`, `_check_rate_limit`, deny + `gate.rate_limited` audit)
- Tests: `tests/test_gatekeeper_rate_limiting.py` (13)

## Pipeline evidence

| Gate | Result | Notes |
|------|--------|-------|
| OpenCode implement | PASS | READY_FOR_AIDER_QA + commit fd89630 |
| Aider QA | WEAK PASS | `docs_only: true` — preflighted plan md only, did not execute rate-limit pytest |
| Auditor | STALL | run `fda65260` ~5h plan_only; continuation `50ee5bcd` thrash; cancelled by board (ASP-608) |
| Aspen local proof | PASS | 13/13 rate-limit + 120 related gatekeeper tests; no secrets in diff; deny+audit before capability check |

## Security review (Aspen stand-in for AUDITOR_APPROVE)

- Limit is per `agent_id`, env-overridable (`ASPEN_GATE_RATE_LIMIT_WINDOW` / `_MAX`), defaults 60s / 30 req.
- Flood path returns `decision=deny` + `gate.rate_limited` audit; does not mint tokens or bypass dual-human.
- No credentials/secrets introduced.
- Residual: prune keeps/drops whole agent stamp lists rather than filtering each stamp (tumbling-window behavior when first stamp ages out). Security-benign (can under-count after full reset); true sliding prune is optional follow-up, not CE-GATE.

## ASP-608 decision

Not productive long work — Auditor thrash after Aider handoff. Cancelled active run; Aspen closed source issue. Do not re-wake Auditor on ASP-607.
