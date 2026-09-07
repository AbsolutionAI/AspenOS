# ADR-0012: Authenticated operator-of-record binding for DualHumanGate

**Status:** Proposed — 2026-08-31  
**Paperclip:** ASP-534 · Parent ASP-530 (Weekly Architecture Review)  
**Related:** ADR-0003 (fleet/edge safety contracts) · ADR-0007 (authz subjects) · ADR-0009 (capability gatekeepers) · H-016 / G8 DualHumanGate (`aspen-edge-rrm`)  
**Trigger:** Before any non-sim arm (G9+)  
**Scope of this ADR:** Plan / decision record only — **no physical path implementation**

---

## Context

`aspen-edge-rrm` ships a **DualHumanGate** (H-016 / G8) that holds safety-adjacent `propose_act` until **two distinct human principals** authorize, then re-verifies the two-principal record immediately before `execute_act`. Stable refuse reasons already include:

| Reason | Meaning |
|--------|---------|
| `insufficient_principals` | fewer than two distinct authorizers |
| `duplicate_principal` | same `human_id` twice |
| `self_approval` | authorizer equals `proposer_operator` (operator-of-record on the proposal) |
| `expired` | enable window closed |
| `unknown_proposal` | no held proposal |

Bus contracts (ADR-0003) already name the wire shape:

- `aspen.edge.<node_id>.authorize` → `{proposal_id, human_id, note?}`
- `aspen.safety.authorize_clear` → `{human_id}`
- dual `authorize_clear` then `aspen.safety.clear` (bare clear never unlatches)

**Gap for G9+ (non-sim arm):** sim proofs treat `human_id` and `proposer_operator` as free strings. That is correct for lab/`ASPEN_SIM=1`, but a free string is **not** an operator-of-record for physical cells. Without authenticated binding:

1. Any bus peer could inject `authorize` with invented principal IDs and satisfy “two distinct humans.”
2. UI channels (Matrix, dashboard, voice) could display one person while publishing another `human_id`.
3. Audit trails would not withstand manufacturing / liability review.

Weekly Architecture Review (2026-08-24) recorded this as **D2** (originally candidate “ADR-0008”; filed here as **ADR-0012** after ADR-0007–0009 claimed those numbers). Recommendation then: Matrix/`#aspen-authz` binds display identity only; NATS payload is SoR.

Master Spec hard rule still stands: agents emit only `propose_act` on safety-adjacent subjects until dual human authorization. This ADR does not weaken that rule; it defines **who counts as a human principal** when authorization is recorded.

---

## Decision

### 1. System of record for authorize principals

**The NATS (or in-process fleet-bus) payload field `human_id` is the System of Record for DualHumanGate authorization events.**

- Gate logic (`DualHumanGate.authorize` / RRM clear path) **must** key principal distinctness, self-approval, and audit on `data.human_id` only.
- Envelope `source` (e.g. `human/bob`) is **telemetry / routing hint**, not the principal SoR.
- Display names, Matrix MXIDs, chat nicks, dashboard labels, and voice phrases are **not** principals unless resolved into `human_id` before publish.

### 2. Operator-of-record (OoR) on proposals

- Every safety-adjacent proposal records `proposer_operator` (already in DualHumanGate) as the **operator-of-record** for that proposal.
- For non-sim arm profiles, `proposer_operator` **must** be a bound principal ID from the same registry as authorize `human_id` (not `sim`, not empty, not a service account pretending to be human).
- Self-approval remains forbidden: `human_id == proposer_operator` → `self_approval`.

### 3. Binding model (layers)

```text
┌─────────────────────────────────────────────────────────────┐
│ Presentation (optional)                                     │
│  Matrix #aspen-authz · Sentinel/HMI · voice · Simplex       │
│  → display identity / UX only                               │
└────────────────────────────┬────────────────────────────────┘
                             │ resolve + authenticate
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ Auth binding (required for G9+ non-sim)                     │
│  Operator registry → stable human_id                        │
│  Proof: short-lived capability / nkey claim / local session │
│  (ADR-0009 gatekeeper issues scoped grant when present)     │
└────────────────────────────┬────────────────────────────────┘
                             │ publish only after bind
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ Control plane SoR                                           │
│  aspen.edge.<node>.authorize  { proposal_id, human_id, … }  │
│  aspen.safety.authorize_clear { human_id }                  │
│  DualHumanGate / EdgeRRM consume human_id only              │
└─────────────────────────────────────────────────────────────┘
```

**Rules:**

| Layer | May bind? | Counts as dual-human principal? |
|-------|-----------|----------------------------------|
| Matrix / `#aspen-authz` display | Display identity only | **No** (until resolved to `human_id` and published on NATS) |
| Dashboard / HMI session | UI session | **No** alone — must emit NATS authorize with bound `human_id` |
| NATS `human_id` after auth binding | **Yes — SoR** | **Yes** |
| Agent / Paperclip / LangGraph service IDs | Service actors | **Never** as dual-human principals |
| `sim` / empty / `anonymous` | Lab only | **Forbidden** on non-sim arm profiles |

### 4. `human_id` format (normative for G9+)

- Opaque, stable string from the **plant operator registry** (local-first).
- Recommended shape: `op:<plant_id>:<stable_slug>` or UUID keyed in registry (exact schema lives in aspen-contracts when implementation lands).
- Must be **comparable with string equality** (DualHumanGate today); no case-folding surprises — registry issues canonical form.
- Emails and Matrix IDs may appear as **aliases** in the registry; the gate still sees only the canonical `human_id`.

### 5. Authentication requirements before publish (G9+)

Before any process may publish `aspen.edge.<node>.authorize` or `aspen.safety.authorize_clear` on a **non-sim** plant profile:

1. Caller presents a **bound operator session** (local token, nkey/JWT subject claim, or gatekeeper capability from ADR-0009) that maps 1:1 to `human_id`.
2. Publisher **sets `human_id` from the bound session**, never from free-typed chat text alone.
3. Bus ACLs (when NATS JWT/nkeys are on) allow authorize subjects only to operator principals / gatekeeper — not to micro-agents.
4. Every authorize/clear event is audited with `{proposal_id?, human_id, plant_id, node_id, binding_method, ts}` (hash-chained audit already on edge-rrm).

**Sim profile (`ASPEN_SIM=1` / plant-range sim_only):** free-string `human_id` remains allowed for tests and smoke; production non-sim configs must refuse unbound principals at the publisher boundary (implementation follow-up — not this ADR’s code scope).

### 6. Dual-human semantics (unchanged, restated)

- Two **distinct** bound `human_id` values required.
- Neither may equal `proposer_operator` (self-approval).
- Enable window (default 600s) still applies; execute re-checks immediately before act.
- Estop clear: two distinct `authorize_clear` `human_id`s, then `clear`; stop-causer policy remains product-level (already tested in edge-rrm).

### 7. Explicit non-goals (this ADR)

- **No physical cell bring-up**, joint streaming, or ASP-418 Phase D hardware work.
- No requirement to pick a single IdP vendor (Auth0, Keycloak, etc.) yet — local operator registry + NATS claims is enough for first non-sim lab.
- No change to propose_act-only agent path or ADR-0002 layering.
- Matrix bridge remains optional front-end (weekly review D7).

---

## Consequences

### Positive

- Clear SoR: auditors and gate code agree on one field (`human_id`).
- Presentation channels can stay convenient without becoming the control plane.
- Aligns with ADR-0009 gatekeeper (capabilities grant who may publish authorize, not a second principal namespace).
- Unblocks G9 checklist design without implementing physical motion.

### Trade-offs

- Operators must enroll in a local registry before non-sim arm; chat-only approval is insufficient.
- Gatekeeper / NATS ACL work (ADR-0009 / BEL-196) becomes a hard dependency for production non-sim, not optional polish.
- Alias mapping (email ↔ MXID ↔ `human_id`) needs careful UX to avoid mistaken dual-approval by one human with two aliases — registry must enforce **one human → one canonical human_id**.

### Risks & mitigations

| Risk | Mitigation |
|------|------------|
| One person two aliases counts as dual human | Registry uniqueness; refuse second live alias on same natural person |
| Compromised dashboard session forges authorize | Short-lived tokens; step-up / second factor on RED/BLACK (future); bus ACL |
| Agents forge human_id | Never issue authorize publish caps to agents; only propose_act |
| Docs drift (candidate was “ADR-0008”) | This file is canonical; index moves 0012 from candidates → filed |

---

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| **Matrix MXID as SoR** | Chat identity ≠ plant liability identity; offline plant may lack Matrix; display-only keeps bridge optional |
| **Envelope `source` as principal** | Too easy to spoof; not validated today; gate already keys on `human_id` |
| **Paperclip / Hermes agent identity as human** | Violates Master Spec dual-**human** rule; agents stay propose_act-only |
| **Cryptographic multi-sig inside gate without registry** | Heavier than needed for first G9; can layer later on same `human_id` |
| **Keep free strings for non-sim** | Unacceptable for manufacturing safety / audit |

---

## Acceptance criteria (this draft)

- [x] ADR filed under `docs/adr/ADR-0012-operator-of-record-binding.md` with status **Proposed**
- [x] Index: removed from **Open candidates**; added to main ADR table
- [x] States: NATS `human_id` is SoR; Matrix/`#aspen-authz` display-only
- [x] States: no physical path implementation in this change
- [ ] **Accepted** only after Weekly Architecture Review or explicit human accept (ASP-530 lineage)

## Implementation follow-ups (out of scope here)

1. Operator registry schema in aspen-contracts + local JSON/SQLite enrollment CLI  
2. Publisher binding check in edge-rrm / gatekeeper when profile ≠ sim  
3. NATS authorize subject ACLs tied to operator nkeys  
4. Sentinel/HMI “approve” button resolves session → `human_id` then publishes  
5. Optional Matrix bot: resolve MXID → registry → publish authorize (never trust raw room text as `human_id`)  
6. G9 checklist row: “ADR-0012 Accepted + binding proof on plant-range non-sim dry-run (no free motion)”

---

## References

- `aspen-edge-rrm/aspen_edge/gate.py` — DualHumanGate  
- `docs/adr/ADR-0003-fleet-edge-safety-contracts.md` — authorize subjects  
- `docs/adr/ADR-0009-capability-based-gatekeepers.md` — no broad keys; dual auth  
- `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-08-24.md` — D2 / D7  
- `docs/FLEET.md` — subject table  
- Master Spec v4.0 — propose_act until dual human authorization  
