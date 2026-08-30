# ASP-525: Daily Implementation Sweep — ADR-0007/8/9, Gatekeeper Shim, Package Classification, Fleet Subjects, Nightly v3

## Summary

Batched implementation sweep advancing three proposed ADRs (ADR-0007, ADR-0008,
ADR-0009) with supporting documentation, a gatekeeper prototype, package
classification matrix, and nightly check v3. All changes committed and verified
(80/81 nightly check pass).

## Changes

| Area | Files | Description |
|------|-------|-------------|
| **ADR-0007 (Proposed)** | `docs/adr/ADR-0007-nats-subject-contracts-sentinel-c2.md` | NATS subject contracts for Aspen Sentinel + C2. Cross-references ADR-0003, ADR-0009. |
| **ADR-0008 (Proposed)** | `docs/adr/ADR-0008-package-classification-core-plugin-devonly.md` | AspenGrove package classification into three tiers (Core / Plugin / Dev-only). Single source of truth in PACKAGES.md. |
| **ADR-0009 (Proposed)** | `docs/adr/ADR-0009-capability-based-gatekeepers.md` | Capability-based gatekeeper pattern — no broad API keys. propose_act + dual-human gate for safety-adjacent actions. |
| **ADR index** | `docs/adr/README.md` | Added ADR-0007/0008/0009 to index. Renumbered open candidates from 0008/0009 to 0011/0012. |
| **PACKAGES.md** | `docs/PACKAGES.md` | Package classification matrix (Core/Plugin/Dev-only) with examples and rules. |
| **Gatekeeper shim** | `src/python/gatekeeper/minimal_shim.py` | Local-first, offline-capable gatekeeper prototype per ADR-0009. Validates capabilities, handles dual-human safety gate, issues short-lived scoped tokens. |
| **FLEET.md** | `docs/FLEET.md` | Updated NATS subject table from dual-publish to primary `aspen.` prefix per ADR-0007. Added authz gate, capability grant subjects per ADR-0009. |
| **Nightly check v3** | `scripts/check-nightly.sh`, `.github/workflows/ci.yml`, `.github/workflows/nightly.yml`, `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` | nats-server v2.14.3→v2.14.5; Gatekeeper Section 12; baseline refresh (80+1). |
| **ASP-524 compound** | `docs/solutions/asp-524-nightly-check-improvements.md` | Compound learning doc for nightly check improvements. |

## Result

- All 14 files committed (508 insertions, 24 deletions).
- Nightly check: **80 passed, 1 failed** (C11 p50 — known, hardware-dependent).
- ADR index links valid, FLEET.md cross-references match filed ADRs.

## What was learned

- **ADR renumbering:** Adding new ADRs (0007/0008/0009) requires renumbering open
  candidates. Keeping candidates at the end of the index with explicit "not yet
  filed" status avoids confusion.
- **Gatekeeper prototype pattern:** Writing a minimal shim alongside a proposed
  ADR (ADR-0009) lets the architecture be validated before acceptance, without
  committing to the full pattern. The nightly check should gate on prototype
  presence + syntax from day one.
- **Package classification documentation:** A separate PACKAGES.md matrix works
  better than embedding classification rules in the ADR itself. ADR-0008 becomes
  the decision record; PACKAGES.md is the operational reference. Cross-links
  keep them connected.
- **NATS subject migration strategy:** Updating FLEET.md from dual-publish
  (`starship.*` / `agnetic.*`) to primary `aspen.` prefix was documentation-led.
  No code change was needed because no consumers exist yet on the new subjects.
  The migration note and cross-ADR references make the transition path clear.
- **Sweep pattern:** Batching multiple ADRs + implementation + nightly check in a
  single sweep commit works well when ADRs are related (subjects, packages,
  gatekeepers all touch the fleet layer). The commit message should itemize each
  area independently for cherry-picking.