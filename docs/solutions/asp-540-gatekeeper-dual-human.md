# ASP-540: Gatekeeper dual-human authorization (ADR-0009 Phase 1)

## Problem

ADR-0009 (H-008, CVSS 8.5) requires mediating agent access to real systems: a
local proxy intercepts `propose_act` on safety-adjacent subjects and enforces
**dual-human authorization** before forwarding. The pre-ASP-540 shim only
*announced* `requires: dual_human`; it never held a proposal, never collected
approvals, and never refused a bare forward — `propose_act` self-authorization
was unmitigated.

## Solution

### Decision engine (`src/python/gatekeeper/minimal_shim.py`)

- `SAFETY_SUBJECTS` = `aspen.safety.*`, `aspen.edge.*.command`,
  `aspen.fleet.mission.start`, matched by a new `_subject_match()` supporting
  NATS wildcards. A **trailing** `*` behaves as a subtree wildcard (so
  `aspen.safety.*` covers `aspen.safety.estop` and deeper), while a mid-pattern
  `*` matches exactly one token. The capability's `:action` suffix is stripped
  before matching.
- `PROPOSALS` registry keyed by `request_id` with `state` (pending/granted/
  refused), `humans[]`, and `expires_at` (5-min window, mirrors ASP-538
  `CLEAR_AUTH_WINDOW`). `request_capability()` now *registers* a pending
  proposal for safety capabilities and returns `propose_act` +
  `status=awaiting_authorization` — never a token.
- `authorize_gate_request(request_id, human_id)`:
  - first/second **distinct** human → audit `gate.authorize`; at 2 → mint a
    short-lived scoped token (`aspen.authz.capability.grant`), audit
    `capability.grant`;
  - **duplicate** human → ignored + audited `gate.authorize.duplicate`
    (H-009 distinct-principal);
  - unknown / refused / window-expired → `refuse` with stable audited reasons
    (`unknown_request`, `authorization_window_expired`, `insufficient_humans`).
- `forward_proposal(request_id)` is the forward gate: refuses any bare/1-human
  forward; idempotent after grant.

### NATS wiring (`src/python/gatekeeper/nats_client.py`)

- New `decision_handler` → subscribes to `aspen.authz.gate.decision`.
- **Feedback-loop guard:** only messages carrying a singular `human_id` +
  `request_id` are treated as approvals, so the gatekeeper's own emits on the
  same subject can never self-approve.
- `_publish_result()` mirrors grant tokens to `aspen.authz.capability.grant`
  and publishes the outcome on `aspen.authz.gate.decision` last.

### Audit

Every propose / authorize / duplicate / refuse / grant flows through
`log_audit` → ASP-537 `AuditEventPublisher` (JSONL always + JetStream
`aspen.sentinel.audit.event`, ADR-0007 `{event_id, actor, action, target,
result, ts}` envelope). Verified in the JSONL journal for a full cycle.

## Key gotchas

- **NATS wildcard semantics trap.** `*` is single-token in NATS. The DoD string
  `aspen.safety.*` was meant colloquially as "anything under aspen.safety", but
  strict NATS matching would require `aspen.safety.>`. Treating a *trailing* `*`
  as a subtree wildcard matches both the DoD on `aspen.safety.*` and real NATS
  users' intent — and preserves the old prefix behavior (`"aspen.safety." in cap`).
- **Naive/aware datetimes.** `datetime.fromisoformat("...Z")` returns tz-aware;
  comparing to `datetime.now(timezone.utc)` directly is correct. Naive
  conversion papered nothing over — compare aware-to-aware.
- **Self-subscription loops.** A component that both publishes and subscribes a
  subject must distinguish its own emits structurally (singular
  `human_id` vs batched `humans[]`), never by "don't subscribe to your own
  subject" — that breaks on multi-instance deployments.
- **Refused is terminal.** Once `forward_proposal` refuses (insufficient
  humans), the proposal stays refused; a fresh `propose_act` is a new
  `request_id`. Demo and tests create separate proposals for the refusal and
  happy paths.
- **Store needs real safety capabilities.** The default `CAPABILITY_STORE` had
  no safety entries, so the propose-act path was dead in the demo. Added
  `aspen.safety.*:execute`, `aspen.edge.*.command:write`,
  `aspen.fleet.mission.start:execute` to `aspen-fleet-edge` (ADR-0009 manifest)
  — `_cap_match` still denies `aspen.fleet.mission.start` (no `:execute`) which
  keeps the ASP-531 negative test green.

## Outcome

- 22 new tests (`tests/test_gatekeeper_dual_human.py`); full run:
  **200 passed, 3 skipped** (gatekeeper + sentinel + whole suite).
- DoD Phase 1 met: intercept, dual-human, refuse bare/1-human forward,
  full audit, gate.request/decision-only contract.
- Threat model H-008 / H-009 / CR 2.3 / P0#3 marked Phase-1 implemented;
  Phase 2 residual (token consumption, credential strip, H-020 redundancy)
  tracked in §4.3.