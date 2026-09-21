# Security

The gatekeeper is the ADR-0009 authorization boundary for capability requests.

- **Safety subjects** (`aspen.safety.*`, edge commands, mission start) are never forwarded
  until **two distinct human** authorizations land (`aspen.authz.gate.decision`); a bare
  forward or single-human clear is refused (H-007, ASP-540/ASP-573).
- **Fail-closed:** the plugin refuses when safety subjects are proposed without an
  authorization window; the core `aspen-safety` estop + `authorize_clear` contracts remain
  always-present last lines of defense (ASP-628 safety-residual table).
- **Credential strip** proxy removes agent credentials before forwarding non-safety work.
- **Rate limits** cap per-agent capability requests (sliding window) to bound audit volume
  and proposal flooding.
- Tokens are in-memory and fail-closed on process restart; a durable Redis/PG backend is a
  deferred packaging-sprint item (ADR-0009).

Runbook / threat model: `docs/SECURITY_THREAT_MODEL_v2.2.md`, `docs/plans/ASP-628-gatekeeper-packaging.md`.