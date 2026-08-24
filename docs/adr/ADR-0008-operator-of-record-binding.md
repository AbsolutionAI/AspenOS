# ADR-0008: Authenticated operator-of-record + human_id binding (DualHumanGate)

## Status
**Proposed** — 2026-08-24  
**Paperclip:** ASP-429 (draft) · ASP-426 Weekly Architecture Review D2 · ASP-364 / H-016 (G8 wire)  
**Linear:** BEL-192 Phase D (pre-G9)  
**Blocks:** any non-sim arm / `ASPEN_SIM=0` driver start / ASP-418 physical cell (G9)  
**Contract:** `docs/security/ACT_GATE_CONTRACT.md`  
**SoR:** Master Spec hard rule — safety-adjacent subjects emit `propose_act` only until dual human authorization  

Plan-only. No code, no physical motion, no `ASPEN_SIM=0`.

## Context

G8 (ASP-364) wired `aspen_edge.gate.DualHumanGate` into `EdgeRRM` so safety-adjacent
proposals hold until two distinct humans authorize, with stable refuse reasons
(`insufficient_principals`, `duplicate_principal`, `self_approval`, `expired`,
`unknown_proposal`) and hash-chained audit.

Identity is still **open**:

| Surface today | Behavior | Gap |
|---------------|----------|-----|
| `EdgeRRM.operator_of_record` | Free constructor string (sim drills use `op-alice`) | Production MUST bind from authenticated identity (`ACT_GATE_CONTRACT`) |
| Propose fallback | `operator_of_record or f"agent:{p.agent_id}"` | Agent id is **not** a human principal; self-approval becomes vacuous if authorizers use different namespaces |
| `authorize(..., human_id)` / bus payload | Client-supplied string | Spoofable on an open bus; session/device ids must not count as principals |
| Matrix `#aspen-authz` | Documented front-end | Bridge MUST attach **Matrix user id**, never display names |
| Estop clear | Same `human_id` strings | Same spoof/namespace risks as act authorize |

Without a binding ADR, G9 physical path can look dual-authorized while both
“principals” are forged strings or one human with two display names.

Weekly review ASP-426 D2: file ADR-0008 before G9.

## Decision

### 1. Canonical principal identity

A **principal** is a stable human (or tightly mapped human service account)
identifier from an **authenticated issuer**. It is never a session token,
device id, display name, Paperclip agent id, or free-form NATS field alone.

**Canonical forms** (exact string equality after binding; no case-fold of MXIDs):

| Issuer | Form | Example |
|--------|------|---------|
| Matrix | MXID | `@josiah:matrix.aspen.local` |
| Sentinel / site IdP | `sentinel:<stable_user_id>` | `sentinel:usr_01H…` |
| Plant ops roster (offline lab with signed map) | `plant:<plant_id>:<roster_id>` | `plant:plant-range:op-alice` |
| Sim-only lab literals | `sim:<label>` **or** bare lab labels | `sim:op-alice` / `op-alice` |

Rules:

1. **Display names are never principals.** Matrix `displayname`, Sentinel UI
   labels, and chat nicks are presentation only.
2. **One human → one principal string per issuer.** Two Matrix accounts are two
   principals (policy may later require roster linkage; gate still treats them
   as distinct — social collusion is out of band).
3. **Cross-issuer aliasing** (e.g. MXID ↔ Sentinel id) is allowed only via an
   explicit site **identity map** loaded at RRM start; mapped aliases collapse
   to one canonical principal **before** gate checks so the same human cannot
   approve twice under two issuers.
4. Empty / whitespace `human_id` or `operator_of_record` is refused as
   `unauthenticated_operator` (new stable reason; additive to G8 set).

### 2. Binding points (who may set the string)

```
┌─────────────────────┐     authenticated      ┌──────────────────────┐
│ Identity source     │ ─────────────────────→ │ Principal string     │
│ Matrix HS / IdP /   │      binding           │ (canonical form)     │
│ NATS creds→roster   │                        └──────────┬───────────┘
└─────────────────────┘                                   │
                                                          ▼
┌─────────────────────┐  operator_of_record    ┌──────────────────────┐
│ EdgeRRM (node)      │ ←───────────────────── │ Node bootstrap /     │
│                     │                        │ enrollment claim     │
└─────────┬───────────┘                        └──────────────────────┘
          │ propose(proposer_operator=…)
          ▼
┌─────────────────────┐  human_id from         ┌──────────────────────┐
│ DualHumanGate       │ ← transport binding ─ │ authorize path       │
│ self_approval /     │    NOT raw client      │ Matrix bridge /      │
│ duplicate checks    │    trust alone         │ Sentinel / NATS map  │
└─────────────────────┘                        └──────────────────────┘
```

| Field | Who binds it | Production rule |
|-------|--------------|-----------------|
| `operator_of_record` | Node bootstrap / fleet enrollment / site config attested at RRM start | MUST come from authenticated operator claim for that node; **constructor free-string only in sim** |
| `proposer_operator` on propose | EdgeRRM copies `operator_of_record`; if unset in **sim**, may use `agent:{id}` for drills only | Non-sim: empty OOR → refuse propose (`unauthenticated_operator`); **never** substitute bare `agent:*` as a human OOR |
| `human_id` on `authorize` / `authorize_clear` | **Transport adapter** after authentication | Payload `human_id` is advisory; adapter **overwrites** with authenticated principal or refuses on mismatch |
| Estop `actor` | Same binding rules as `human_id` | Stop-causer self_approval compares canonical principals |

**Matrix `#aspen-authz`:** bridge sets `human_id = event.sender` (MXID). Ignore
or hard-fail any client-supplied alternate id. One Matrix account MUST NOT
synthesize a second principal.

**NATS / local bus:** do not trust `data.human_id` from an anonymous publisher.
Bind via (in order of preference): (1) mTLS/nkey user → roster map,
(2) signed authorize envelope whose subject matches the connection identity,
(3) sim-only allowlist under `ASPEN_SIM=1` / cell `status: sim_only`.

**Sentinel UI:** session → IdP stable user id → `sentinel:<id>` (or mapped MXID
if site chooses Matrix as canonical issuer).

### 3. Gate semantics (unchanged intent, tighter inputs)

DualHumanGate keep current refuse table. Binding layer guarantees inputs are
canonical principals:

| Case | Reason |
|------|--------|
| `< 2` distinct principals | `insufficient_principals` |
| Same canonical principal twice | `duplicate_principal` |
| Authorizer == proposal `proposer_operator` | `self_approval` |
| Outside enable window | `expired` |
| Missing/forged/unbound identity | `unauthenticated_operator` (**new**, binding layer or gate) |

Self-approval compares **canonical** strings after identity-map collapse.
Arm operator / hold-to-enable identity (G6) SHOULD use the same canonical form
so “operator-of-record cannot hold enable on own proposal” stays coherent.

### 4. Sim vs non-sim (freeze-safe)

| Mode | Detection (any) | Binding strictness |
|------|-----------------|--------------------|
| **Sim** | `ASPEN_SIM=1`, cell `status: sim_only`, proof harnesses | Lab literals (`op-alice`, `bob`) allowed; constructor OOR OK; proofs stay green without IdP |
| **Non-sim / G9 path** | `ASPEN_SIM=0` **or** cell leaving `sim_only` **or** live driver attach | Binding **mandatory**; refuse propose/authorize/clear without authenticated principals; `agent:*` OOR forbidden |

No ADR text authorizes physical motion. G9 still needs captain ceiling (ASP-418)
after this binding is **Accepted** and implemented.

### 5. Audit requirements

Every propose / authorize / enable / refuse / act / authorize_clear / clear
event MUST record:

- `principal` (canonical) and `issuer` (matrix \| sentinel \| plant \| sim)
- `binding` method (`mxid_sender` \| `nats_roster` \| `sentinel_session` \| `sim_literal`)
- proposal_id, decision/reason

Hash-chained `AuditLog` remains SoR for plant evidence (`ASPEN_AUDIT_PATH`).

### 6. Acceptance before G9 (implementation follow-up — not this ADR)

When this ADR is Accepted and coded (separate ticket):

1. Non-sim EdgeRRM refuses safety_adjacent propose if OOR unbound.
2. Authorize path unit tests: spoofed payload `human_id` ≠ transport principal → refuse.
3. Matrix bridge contract test: display name ≠ principal; sender MXID used.
4. Identity-map collapse: two issuer aliases → `duplicate_principal`.
5. Existing sim harnesses (`sim_dual_human_gate.py`, `sim_act_gate_wire.py`) remain exit 0 under sim literals.
6. `ACT_GATE_CONTRACT.md` + plant-range runbook cite this ADR; cell profile notes binding required for non-sim.

## Consequences

- G8 library can stay pure (string principals); **adapters bind**, gate compares.
- Site ops must maintain roster / IdP map for plant-range before live arm.
- Matrix becomes the preferred human front-end issuer where Hermes already runs;
  Sentinel may canonicalise to MXID or `sentinel:` per site profile.
- New refuse reason `unauthenticated_operator` must be added to contract + cell
  profile when implementing (additive; sim paths unused).
- ASP-418 / G9 checklist gains explicit “ADR-0008 Accepted + binding proofs green.”
- Does **not** replace hold-to-enable, estop hardware path, or captain $ gate.

## Alternatives rejected

| Option | Why rejected |
|--------|--------------|
| A. Keep free-string OOR forever | Fails F-017; dual-auth theater |
| B. Session tokens as principals | Breaks duplicate detection across devices; unstable |
| C. Display names | Trivial collision / rename attacks |
| D. Paperclip / Hermes agent id as OOR in production | Agents are not human second principals; Master Spec dual-**human** |
| E. Gate library calls Matrix/IdP directly | Wrong layer; breaks offline edge and sim; violates light-core |
| F. Crypto multi-sig wallets as only path | Valid future enhancer; too heavy for pre-G9 manufacturing ops |
| G. Accept ADR without sim escape hatch | Would break G8 proof harnesses and freeze-friendly drills |

## Implementation sketch (non-binding; future PR)

```text
aspen_edge/identity.py   # Principal, Issuer, normalize(), collapse(map)
aspen_edge/rrm.py        # bind OOR at start; authorize() takes BoundPrincipal
adapters/
  matrix_authz_bridge    # human_id = event.sender
  nats_authorize         # roster from nkey/account
  sentinel_session       # IdP subject → canonical
```

Config sketch:

```yaml
identity:
  canonical_issuer: matrix   # matrix | sentinel | plant
  map_path: /etc/aspen/identity-map.yaml
  sim_literals: true         # forced false when ASPEN_SIM=0
operator_of_record:
  source: enrollment         # enrollment | config | forbid_empty
```

## References

- `docs/security/ACT_GATE_CONTRACT.md` — G8 control-path contract  
- `docs/plans/ASP-364-dual-human-wire.md` — wire design  
- `docs/solutions/asp-364-dual-human-act-gate.md` — learning #5 (identity open)  
- `docs/robotics/plant-range-arm-runbook.md` — operator requirements  
- `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-08-24.md` — D2  
- ADR-0002 (layering), ADR-0003 (subjects including authorize)  
- Master Spec: propose_act until dual human authorization  

## Revision history

| Date | Change |
|------|--------|
| 2026-08-24 | Proposed (ASP-429) — plan-only binding rules pre-G9 |
