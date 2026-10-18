# ASP-432 Auditor Approval — H-022: HITL Vault Approval Gate

**Run:** 856f55e2-f242-4d98-8c35-d01c5a4f6922 (evidence re-verified by bf81bad9)
**Date:** 2026-09-23
**Agent:** Auditor (hermes_local)
**Model:** DeepSeek V4-Flash

## Test Results (verified this heartbeat)

| Suite | Tests | Result |
|-------|-------|--------|
| test_gatekeeper_vault_gate.py | 19/19 | ALL PASS |
| test_gatekeeper_phase2.py | 77/77 | ALL PASS |
| test_gatekeeper_dual_human.py | 22/22 | ALL PASS |
| test_gatekeeper_rate_limiting.py | 13/13 | ALL PASS |
| test_gatekeeper_nats.py | 21/21 | ALL PASS |
| **Total** | **152/152** | **ALL PASS** |

## Security Review Checklist

### 1. No new secrets or credentials
- vault_gate.py: zero hardcoded credentials, API keys, tokens, or passwords
- Imports services/hitl.py and services/hitl_vault.py via importlib — no credential exposure
- minimal_shim.py wiring: no credential handling in new code
- hitl_vault.py bugfix: .get() -> direct key access (not credential-related)

### 2. Fail-closed on every vault failure path
- check_vault_approval(): returns False (never grants) on:
  - Missing hitl_request_id -> False
  - Row not found or status != "approved" -> False
  - Note file missing -> False
  - Any exception -> False (defensive catch)
- ensure_vault_approval(): raises on vault-layer error
- request_capability() catch: _mark_refused("vault_unavailable") with audit event
- _vault_gate(): refuses with vault_approval_required on any vault failure
- All paths confirmed by tests (test_vault_unavailable_fails_closed, test_missing_note_file_refused, etc.)

### 3. Dual-human preserved as additional gate layer
- Physical cell acts require BOTH: 2 distinct humans AND vault approval
- authorize_gate_request: first collects dual-human, THEN checks vault
- vault gate is an additional enforcement layer, not a replacement

### 4. Estop path unmodified (safety-critical)
- "aspen.safety.estop:execute" does NOT match PHYSICAL_ACT_SUBJECTS
- Estop keeps the plain dual-human proposal path (fast)
- Test test_estop_stays_plain_dual_human confirms no vault_approval_id in response

### 5. Threat model alignment
- H-022 entry in SECURITY_THREAT_MODEL_v2.2.md updated (commit diff)
- CVSS 8.5 (AV:N/AC:L) — correctly rated Critical
- Mitigation description matches implementation
- Status: Implemented (ASP-432)

### 6. IEC 62443 alignment
- CR 3.4 (Software and information integrity) — durable, human-reviewable approval record
- CR 5.1 (Fail-closed) — every vault failure path denies, never grants
- Dual-human + vault gate provides defense-in-depth

### 7. Light-cell profile scoping (ADR-0012)
- is_physical_cell_act(capability, "light-cell") returns False
- Light-cell (sim/plain) profiles never take the vault path
- Unknown profiles fail closed (treated as physical)

### 8. Hermetic testing
- All tests use per-test tmp_path for HITL_DB and HITL_VAULT_DIR
- No real hardware, no shared state, no ASPEN_SIM required
- SQLite rows survive restart test (TestRestartPersistence)

## Disposition

**AUDITOR_APPROVE** — H-022 vault gate implementation is audited and approved.

- 152/152 gatekeeper tests pass with fresh evidence
- Zero new secrets or credentials
- Fail-closed on every vault failure path
- Dual-human preserved
- Estop path unmodified
- Threat model v2.2 H-022 entry updated

**Next steps (aspen):**
1. git add the modified/untracked files
2. Commit with message referencing ASP-432 and H-022
3. Push to origin/master
4. Mark issue in_review -> done after local proof

## API Note
Paperclip API unreachable (curl exit 7) — AUDITOR_APPROVE cannot be posted to issue. Re-verified bf81bad9 — all 152/152 tests still pass, diff unchanged. Recovery disposition at run scratch dir bf81bad9/recovery-disposition.md.

When API recovers: PATCH issue with AUDITOR_APPROVE comment, set status to in_review.