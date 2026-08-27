# ADR-0008: Authenticated operator-of-record binding for DualHumanGate

## Status
Proposed — 2026-08-27  
**ASP-426:** Weekly Architecture Review recommendation (D2)  
**Prerequisite:** Before any non-sim arm (G9+)

## Context

The DualHumanGate (ADR-0003 §Safety, H-016/G8) requires two distinct human principals to authorize each `propose_act` before an edge RRM executes it. However, there is currently no mechanism that **binds a given bus message (`authorize`, `authorize_clear`) to a verified human identity** that survives replay, operator impersonation, or stale session tokens.

Without operator-of-record binding, the following attack surfaces exist at G9+:

1. **Replay:** A captured `authorize` message could be replayed against a different proposal or after the authorizing operator has been revoked.
2. **Impersonation:** Any agent or process that can publish to `aspen.edge.<node>.authorize` can claim to be any human ID.
3. **Cross-plant contamination:** A single compromised NATS credential could authorize acts on every edge node.
4. **No audit root:** Incident forensics cannot prove *which human* authorized any given act — only which NATS client published the message.

## Decision

### Binding model

Every safety-adjacent bus message (`authorize`, `authorize_clear`, and `estop` when non-sim) carries a **detached cryptographic proof** of the human operator's identity. The proof is verified by the receiving RRM before the message is processed.

```
┌────────────────────────────────────────────────────────────────┐
│ Operator                                                         │
│   id: human_id (drawn from existing fleet identity/SSO)          │
│   key: Ed25519 key pair (hardware-backed where available)        │
│   proof: sig(key.private, message_id || proposal_id || ts)       │
└──────────────────────────┬─────────────────────────────────────┘
                           │ sign
                           ▼
┌────────────────────────────────────────────────────────────────┐
│ Bus message                                                      │
│   subject: aspen.edge.<node>.authorize                           │
│   payload: { proposal_id, human_id, note?, signature, ts, nonce }│
│   envelope: event-envelope.schema.json (per ADR-0003)            │
└──────────────────────────┬─────────────────────────────────────┘
                           │ verify
                           ▼
┌────────────────────────────────────────────────────────────────┐
│ Edge RRM gate                                                     │
│   1. Reject if human_id not in active operator registry          │
│   2. Reject if signature fails verification against registry key  │
│   3. Reject if nonce replayed or ts outside drift window (30s)   │
│   4. Accept → hold for second distinct authorization             │
└────────────────────────────────────────────────────────────────┘
```

### Key management

| Concern | Approach |
|---------|----------|
| Key generation | At operator onboarding (existing fleet registration flow) |
| Key storage | Operator device; **never** stored in bus messages or NATS payloads |
| Public key registry | Fleet state (`aspen.fleet.node.register` includes operator `pubkey`) or dedicated `aspen.fleet.operator.register` |
| Revocation | `aspen.fleet.operator.revoke` with estop-like fanout; RRM caches last-known-valid set |
| Rotation | Operator re-registers new key; old key revoked after TTL overlap (default 24h) |
| Hardware binding | Recommended but not required at G9; bare Ed25519 software keys acceptable at G9, hardware required before G10 |

### Message integrity envelope

All G8/G9 safety messages must include:

| Field | Type | Description |
|-------|------|-------------|
| `human_id` | string | Operator identifier from fleet registry |
| `signature` | hex | Ed25519 sig over canonical message bytes |
| `nonce` | hex | 16-byte random, prevents replay |
| `ts` | integer | Unix milliseconds, ±30s drift window |
| `message_id` | string | Per-message unique ID (envelope already provides `id`) |

### What this does NOT cover

- **Authentication of the NATS client itself** — NATS TLS client certs and nkeys remain the transport-level identity; operator binding is an additional payload-level proof.
- **Authorization policy** — Who may authorize what act categories is outside this ADR (future ACL work, ASP-369).
- **SSO integration** — The `human_id` namespace must be decided at deploy time; this ADR only requires uniqueness within a plant.

### Rules

1. **Sim mode (`ASPEN_SIM=1`):** Signature verification MAY be skipped on sim-only fleets. This preserves existing sim dual-human gate behavior (ASP-364, ASP-384) without requiring key infrastructure for dev loops.
2. **Signatures are NOT optional in non-sim mode:** An unsigned `authorize` message in production must be rejected with a stable audited reason.
3. **Nonce uniqueness per message_id:** The RRM must reject duplicate (message_id, nonce) pairs to prevent cross-node replay.
4. **Registry is eventually consistent:** RRMs cache the operator registry and accept a configurable staleness (default 60s). Revocations propagate via NATS JetStream with at-least-once delivery.
5. **Audit trail:** Every verified authorization appends to the edge audit log (local SQLite, T1 memory) with the full message payload including signature.

## Consequences

### Positive
- Provides cryptographic proof of operator identity for incident forensics
- Prevents replay and impersonation across plants
- Lightweight — Ed25519 verification is sub-millisecond, viable on edge hardware
- No new PKI or CA required — fleet operator self-registers keys at onboarding

### Negative / costs
- Operator onboarding flow must be extended to generate and register a key pair
- RRM must verify signatures (modest CPU cost, but non-zero on constrained edge nodes)
- Nonce / replay state must be persisted across RRM restarts (edge audit log)
- Existing sim dual-human test harnesses must conditionally skip verification

### Follow-ups (not in this ADR's acceptance)
1. Schema extension for `aspen.fleet.operator.register` / `revoke` subjects
2. Operator key generation CLI command in `starshipctl` or edge-rrm tooling
3. Registry cache TTL and staleness configuration in edge-rrm config
4. G10 requirement: hardware-backed key storage (TPM / YubiKey)

## Alternatives rejected

| Alternative | Why rejected |
|-------------|--------------|
| **NATS nkey-only** | nkeys authenticate the *client process*, not the human operator; does not prevent script-kiddie-on-compromised-host |
| **TLS client cert per human** | CA overhead, cert rotation burden, no binding to operator identity in bus payload |
| **OIDC / OAuth token in payload** | Requires live SSO at time of authorization; breaks offline edge (ADR-0002 offline rule) |
| **No binding (status quo for sim)** | Acceptable for sim-only; unacceptable at G9+ per architecture review safety stance |
| **Blockchain / distributed ledger** | Over-engineered for current scale; Ed25519 + local audit log sufficient until multi-plant federation |

## References

- `docs/adr/ADR-0003.md` — G8 dual-human gate contract, safety subjects
- `docs/adr/ADR-0002.md` — Offline edge store-and-forward rules
- `docs/security/ACT_GATE_CONTRACT.md` — Act gate contract (does not exist on this branch; should be restored or created alongside this ADR)
- `aspen-edge-rrm` — Gate library location, verify/reject logic
- `scripts/sim_dual_human_gate.py` — Sim proof harness (conditional sig skip)

## Decision log

| Date | Event |
|------|-------|
| 2026-08-27 | Drafted under ASP-514 daily implementation sweep / ASP-426 architecture review recommendation; status **Proposed** — plan-only until G9+ |