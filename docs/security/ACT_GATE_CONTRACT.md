# Act gate contract (index)

**Status:** Index of implemented gates. Not a new decision.
**Drafted:** ASP-676 (2026-09-28), on a branch that did not merge.
**Landed:** ASP-739 (2026-10-05), after re-reading the subject lists and the watchdog clear rule.
**SoR for decisions:** ADR-0003, ADR-0009, ADR-0012 (Proposed). Code wins if this index drifts.

This file does not authorize physical arm, live GPIO, or a new principal registry.

## Gates (order)

1. **propose_act only.** Agents do not emit actuator setpoints. ADR-0002 / ADR-0003.
2. **Dual human.** Safety-adjacent capabilities hold until two distinct `human_id` values authorize inside the window. Single-principal, duplicate, and self-approval refuse. Estop clear is the same rule: two `authorize_clear`, then `clear`. Bare clear never unlatches.
3. **Physical vault (H-022 / ASP-432), additional.** If `is_physical_cell_act` is true, the gatekeeper also requires a durable HITL vault row whose status is `approved`, plus the reviewable note. Missing, pending, denied, or any vault-layer error refuses `vault_approval_required` (fail closed). This does **not** replace dual-human.
4. **Estop stays fast.** `aspen.safety.estop` is not a physical-cell act. It does not take the vault path.
5. **Light-cell skips the vault.** Profile `light-cell` is never a physical cell act.
6. **Independent watchdog (H-023 / ASP-433).** `src/python/safety/estop_watchdog.py` trips fail-closed if heartbeats stop, the backend fails, or config is invalid. `tick` never clears a trip. `clear` needs two distinct authorizers. It does not trust the agent loop or the gatekeeper. Sim and file backends only. Live GPIO is not this contract.
7. **Operator-of-record (ADR-0012) is not in force.** Sim still accepts free-string `human_id`. Non-sim arm is not allowed until that ADR is Accepted and a bind proof exists. H-022's vault row is an approval record, not that bind.

## Where it lives

| Piece | Path |
|-------|------|
| Subject names | ADR-0003. Edge package stub: `aspen-edge-rrm/CONTRACTS.md` (names only) |
| Capability gate | `src/python/gatekeeper/minimal_shim.py` |
| Physical subjects | `PHYSICAL_ACT_SUBJECTS`: `aspen.edge.*.act`, `aspen.safety.*.act`, `aspen.edge.*.command` |
| Safety subjects (no vault by themselves) | `SAFETY_SUBJECTS`: `aspen.safety.*`, `aspen.edge.*.act`, `aspen.edge.*.command`, `aspen.fleet.mission.start` |
| Vault row | `src/python/gatekeeper/vault_gate.py` |
| Watchdog | `src/python/safety/estop_watchdog.py` |
| Threat rows | `docs/SECURITY_THREAT_MODEL_v2.2.md` H-022, H-023 |

`aspen.edge.*.act` and `aspen.edge.*.command` appear in both lists. Those capabilities take dual-human **and** the vault when the profile is not `light-cell`. Estop (`aspen.safety.estop`) matches safety only.

## Non-goals

- No authenticated `human_id` registry (ADR-0012, Proposed).
- No live cell wire.
- No second scheduler. Paperclip remains the org SoR (ADR-0005).
