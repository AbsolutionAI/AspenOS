# Solution: ASP-432 H-022 HITL vault approval gate

## What shipped
- `src/python/gatekeeper/vault_gate.py` — durable HITL SQLite + Obsidian note bridge for physical cell acts
- `minimal_shim.py` — `PHYSICAL_ACT_SUBJECTS`, `is_physical_cell_act`, request-time vault ensure, grant-time vault check (fail-closed)
- `services/hitl_vault.py` — small robustness fix for note lookup
- `tests/test_gatekeeper_vault_gate.py` — 19 tests (classify, create, refuse, grant, restart)
- Threat model v2.2 H-022 → Implemented

## Gates
- Dual-human still required; vault is an *additional* layer
- Estop stays plain dual-human (no vault latency)
- light-cell profile skips vault; unknown profiles fail closed as physical
- Refuse reasons: `vault_approval_required`, `vault_unavailable`

## Proof (Aspen local 2026-09-23)
```
.venv/bin/pytest tests/test_gatekeeper_vault_gate.py \
  tests/test_gatekeeper_dual_human.py tests/test_gatekeeper_nats.py \
  tests/test_gatekeeper_phase2.py tests/test_gatekeeper_rate_limiting.py -q
# 152 passed
```

## Non-goals (still open)
- ASP-433 H-023 hardware estop watchdog
- ASP-418 physical D1 bring-up
- Live host SSH/UFW (ASP-370 apply)
