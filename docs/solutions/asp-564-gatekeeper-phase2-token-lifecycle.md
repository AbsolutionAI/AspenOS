# ASP-564: Gatekeeper Phase 2 — Token Lifecycle, Credential Strip, Safety Enforcement

**Parent:** ADR-0009 · **Linear:** BEL-215 (residual)  
**Branch:** master (2 ahead)  
**Tests:** 77/77 pass (Phase 2) + 43/43 pass (Phase 1) — no regressions

## Overview

ADR-0009 Phase 2 completes the gatekeeper implementation by adding three
capabilities that Phase 1 (proposal interception + dual-human + audit) left
explicitly out of scope:

1. **Short-lived capability token lifecycle** — issue, consume (one-shot),
   refresh (TTL extension), expire (forced expiry), and stale cleanup
2. **GatekeeperProxy / NATSAgentProxy** — credential strip adapter: agents
   hold no broad credentials, only a gatekeeper endpoint reference
3. **SafetySubjectEnforcer** — immutable proxy enforcement: direct publishes
   to safety-adjacent NATS subjects without a valid gatekeeper token are
   denied

## Files Changed

### Source code (3 files, 4 edits)

| File | Change | Lines |
|---|---|---|
| `src/python/gatekeeper/minimal_shim.py` | Added `log_audit` for unknown-token deny paths in `refresh_token()` and `expire_token()` (bugfix: Phase 1 audit coverage gap) | +10 |
| `src/python/gatekeeper/gatekeeper_proxy.py` | Fixed `request_capability` to extract `token_id` from nested `result["token"]` dict — caching and tests depend on it | +3 |
| `src/python/gatekeeper/__init__.py` | Already exported all Phase 2 symbols; no change needed | 0 |

### Tests (1 file, 1 fix)

| File | Change |
|---|---|
| `tests/test_gatekeeper_phase2.py` | Fixed `test_patterns_are_immutable_tuple` to test tuple immutability via `TypeError` on item assignment instead of `AttributeError` on attribute reassignment (tuple's natural protection, not a custom property) |

## Token Lifecycle — Design

All tokens are tracked in `TOKEN_REGISTRY: Dict[str, Dict]` (in-memory;
replace with Redis/PG for production). States: `active` → `consumed` |
`expired`.

| Operation | Function | Behavior | Audit type |
|---|---|---|---|
| Issue | `_register_token()` | Creates token with TTL (default 15 min), registers in registry | (called by grant path) |
| Consume | `consume_token(id)` | One-shot; idempotent on already-consumed; refuses expired | `token.consumed` / `token.consume.deny` |
| Refresh | `refresh_token(id, ext)` | Extends TTL (default +15 min); refuses consumed/expired | `token.refresh` / `token.refresh.deny` |
| Expire | `expire_token(id)` | Force-expire before natural TTL; idempotent on expired; refuses consumed | `token.expired` / `token.expire.deny` |
| Cleanup | `_cleanup_stale_tokens()` | Purges tokens expired >1h ago; no effect on active or recently-expired | (none) |

## Credential Strip — Proxy Layer

`GatekeeperProxy` (abstract base) and `NATSAgentProxy` (NATS transport):

- Agents instantiate a proxy with only an endpoint URL (no API keys, no
  passwords, no NATS nkey)
- Every external action acquires a fresh token via `request_capability()`
- `execute_with_token()` runs the action then consumes the token (one-shot)
- No credential fields (`api_key`, `password`, `secret`, `auth_token`,
  `credential`) exist on proxy instances — verified by test

## Safety Enforcement — Proxy Enforcement

`SafetySubjectEnforcer`:

- Immutable after construction: pattern list is stored as a `tuple`
- Subject patterns compiled from `SAFETY_SUBJECTS` + optional extras
- Gate: non-safety subjects pass freely; safety subjects require a valid
  active token
- Fail-closed: unknown/expired/consumed tokens → deny

## Bugs Fixed During Testing

1. **`refresh_token` missing audit for unknown tokens** — the deny path for
   non-existent tokens returned a dict without calling `log_audit`, creating a
   blind spot in the audit trail. Added.

2. **`expire_token` missing audit for unknown tokens** — same pattern; added.

3. **`GatekeeperProxy.request_capability` token_id extraction** — the helper
   checked `"token_id" in result` but the shim's `request_capability` nests
   token data inside `result["token"]`. Fixed to extract `token_id` from
   `result["token"]["token_id"]` and promote it to the top-level result dict.

These were all audit-logging gaps, not logic errors — the credential strip
and safety enforcement designs were correct.

## Threat Model Impact

Updates `docs/SECURITY_THREAT_MODEL_v2.2.md`:

- **H-010** (Stale capability tokens, Medium) — design for Phase 2 is now
  implemented: short TTL + active check + refuse if expired; mark In Progress
- **H-008** (Gatekeeper shim, CVSS 8.5) — Phase 2 completes ADR-0009; mark
  In Progress (pending dual-human gate hardening as separate item)
- **Item 7** (ADR-0009 Phase 2 list item in §8) — implemented

## Future Work (Phase 3 / Residual)

- Persistent token store (Redis/PG) for production deployments
- H-020 gatekeeper redundancy / SPOF mitigation
- Live Hermes/Paperclip adapter wiring (currently standalone proxy only)
- Token revocation list for multi-gatekeeper topologies

## References

- `docs/adr/ADR-0009-capability-based-gatekeepers.md`
- `docs/SECURITY_THREAT_MODEL_v2.2.md`
- `src/python/gatekeeper/minimal_shim.py` (lines 68–531)
- `src/python/gatekeeper/gatekeeper_proxy.py` (whole file, 343 lines)
- `src/python/gatekeeper/safety_enforcer.py` (whole file, 181 lines)
- `tests/test_gatekeeper_phase2.py` (902 lines, 77 tests)