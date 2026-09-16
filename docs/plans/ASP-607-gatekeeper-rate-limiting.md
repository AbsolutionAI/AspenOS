# ASP-607: Gatekeeper Rate Limiting (ASP-540 residual)

**Source:** Daily implementation sweep — flagged in `.paperclip/todos/ASP-540-liveness-disposition.md` as "not yet implemented (no issue filed)"
**ADR reference:** ADR-0009 (capability-based gatekeepers)
**Parent scope:** H-020 residual hardening

## Problem

The gatekeeper shim (`src/python/gatekeeper/minimal_shim.py`) has no rate limiting on `request_capability()`. A compromised or misbehaving agent can flood the gatekeeper with capability requests, exhausting in-memory state (PROPOSALS, TOKEN_REGISTRY), generating unbounded audit log volume, and consuming NATS bandwidth. Safety-adjacent requests are particularly concerning: flooding `propose_act` triggers dual-human authorization windows that create human-operator fatigue.

## Success Criteria

1. Per-agent sliding-window rate limiter applied at the top of `request_capability()`.
2. When rate-limited: audit event `gate.rate_limited` logged, result `{"decision": "deny", "reason": "rate_limited"}` returned.
3. Window and max-requests configurable via module constants (env-overridable).
4. Test file `tests/test_gatekeeper_rate_limiting.py` covers: basic allow/deny, window reset, safety-path under limit, env override, and reset helper.
5. All existing tests continue to pass (303+ passed, 0 failures).

## Design

### Sliding window (in-memory)

- `RATE_LIMIT_STATE: Dict[str, list[float]]` — maps agent_id to list of `time.time()` timestamps within the current window.
- `RATE_LIMIT_WINDOW_SECONDS = 60` — window length, overridable via `ASPEN_GATE_RATE_LIMIT_WINDOW`.
- `RATE_LIMIT_MAX_REQUESTS = 30` — max requests per window per agent, overridable via `ASPEN_GATE_RATE_LIMIT_MAX`.
- `_prune_rate_window(now)` — removes timestamps older than window from all agents, deletes empty entries.
- `_check_rate_limit(agent_id) -> bool` — prunes, checks count, appends current timestamp if under limit, returns True (allowed) or False (rate-limited).
- `_reset_rate_limits()` — clears `RATE_LIMIT_STATE` entirely (for tests and daemon resets).

### Hook point

Rate check goes at the very top of `request_capability()`, before the capability check. This blocks flooding even from unknown agents, preventing resource exhaustion on the proposal and audit paths.

### Audit event

```python
log_audit({
    "type": "gate.rate_limited",
    "request_id": request_id,
    "agent_id": agent_id,
    "capability": capability,
    "resource": resource,
    "decision": "deny",
    "reason": "rate_limited",
    "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
    "max_requests": RATE_LIMIT_MAX_REQUESTS,
})
```

### Non-goals

- Per-human authorization rate limiting (authorize_gate_request is human-initiated, low-volume).
- Per-capability or per-resource rate limiting (keep simple, per-agent only).
- Persistent/token-bucket — sliding window is sufficient for this defensive layer; token bucket adds complexity with no clear benefit here.

## Out of Scope

- Sentinel fleet-overview producer (separate design, ADR-0007 "Next")
- Plugin marketplace update stub
- ADR-0012 operator-of-record follow-ups
