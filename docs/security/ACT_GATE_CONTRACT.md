# Act Gate Authorize Contract — H-016 / ASP-364 (G8)

Status: **wired in sim control path** (`aspen_edge.gate.DualHumanGate` +
`EdgeRRM`). Cell stays `status: sim_only`; no physical motion, no
`ASPEN_SIM=0` drivers. Matrix bridge is a front-end onto this contract and is
**not** required for G8.

## Threat-model basis

CRITICAL finding F-017 (Security Threat Model v2.2, [ASP-298](/ASP/issues/ASP-298)):
safety-adjacent subjects may only publish `propose_act` until two distinct human
principals authorize. Master Spec hard rule; see
`docs/plans/ASP-364-dual-human-wire.md` and
`docs/plans/BEL-192-phase-d-physical-cell-gate.md`.

## Control-path contract

| Step | Subject / call | Payload | Result |
| --- | --- | --- | --- |
| Propose | `EdgeRRM.handle_propose(ProposeAct)` | `risk_class` defaults to `safety_adjacent` (fail-safe) | audit `propose_act result=held_dual_auth`, carries `proposal_id` |
| Authorize | bus `aspen.edge.<node>.authorize` or `EdgeRRM.authorize(pid, human_id, note)` | `{proposal_id, human_id, note?}` | audit `gate.authorize count=n/2` |
| Enable | automatic after 2nd distinct principal | — | audit `gate.enable_act principals_seen=[A,B]`, window 600 s (`ASPEN_GATE_WINDOW_S`) |
| Act | `EdgeRRM.request_act(pid, executor)` | — | verifies two-principal record + live window immediately before act → audit `act result=executed_sim` |

Refuse reasons (stable strings, always audited):
`insufficient_principals`, `duplicate_principal`, `self_approval`,
`expired`, `unknown_proposal`, plus pre-existing `estop_latched`.

Identity rules:

- Principals are **stable human ids**, not sessions/devices; the same id twice
  is refused as `duplicate_principal`.
- The proposer's operator-of-record cannot authorize (`self_approval`).
  EdgeRRM binds it via `operator_of_record`; production wiring MUST set this
  from an authenticated identity source — see
  [`docs/adr/ADR-0008-operator-of-record-binding.md`](../adr/ADR-0008-operator-of-record-binding.md)
  (Proposed; required before G9 / non-sim arm).

## Estop clear (human-only)

Press (`aspen.safety.estop`, carries `actor`) latches. Clear requires two
distinct `aspen.safety.authorize_clear {human_id}` messages before
`aspen.safety.clear` unlatches; a bare clear message can never unlatch. The
stop-causer is refused (`self_approval`). Mirrors G7 sim semantics.

## Matrix #aspen-authz front-end schema

The room is a human front-end that emits exactly the authorize payload above.
One approval message per principal; the bridge MUST attach the authenticated
Matrix user id (`event.sender` MXID) as `human_id` (never display names) and
MUST NOT synthesize a second principal from one account. Binding rules:
ADR-0008.

```json
{
  "proposal_id": "<uuid from held_dual_auth record>",
  "human_id": "@operator2:aspen.example",
  "note": "reviewed jog_arm target home on camera feed"
}
```

Announcement direction (gate → room): post the `held_dual_auth` record with
`proposal_id`, `subject`, `action`, `risk_class`, and `expires_at`. Until the
bridge ships, two humans drive approvals through the same payload over NATS /
local channel (see `scripts/sim_act_gate_wire.py` step 6); a Sentinel UI would
emit the identical payload.

## Audit trail

All gate events flow through the hash-chained `AuditLog`
(`ASPEN_AUDIT_PATH`, default `/tmp/aspen-audit-<node>.jsonl`) under the
`gate.*` prefix plus RRM-level `propose_act` / `act` records. Tamper-evidence:
`EdgeRRM.verify_audit()`.

## Sim isolation

Every executable path here runs sim-only: no driver starts, no joint motion,
cell profile keeps `acl_outbound: []` and `status: sim_only`.

Proof harnesses:

```
python3 scripts/sim_dual_human_gate.py   # library refuse suite + happy path
python3 scripts/sim_act_gate_wire.py     # end-to-end RRM wire drill (exit 0 ⇒ verify_audit ok)
```
