"""
Gatekeeper package — ADR-0009 capability-based authorization shim.

Exports:
- NATSGateClient: NATS client wrapper with offline-fallback buffer
- request_capability: core gatekeeper decision logic (from minimal_shim)
- authorize_gate_request: record a human authorization toward dual-human grant
- forward_proposal: forward gate — refuses until two distinct humans authorize
- log_audit: audit event writer (local buffer + optional NATS publish)
- Phase 2 (ADR-0009):
  - TOKEN_REGISTRY, consume_token, refresh_token, expire_token
  - GatekeeperProxy, NATSAgentProxy, SafetySubjectEnforcer
- Rate limiting:
  - RATE_LIMIT_WINDOW_SECONDS, RATE_LIMIT_MAX_REQUESTS, _check_rate_limit, _reset_rate_limits
"""

from .minimal_shim import (
    AUDIT_LOG,
    CAPABILITY_STORE,
    PROPOSALS,
    TOKEN_REGISTRY,
    TOKEN_DEFAULT_TTL_MINUTES,
    TOKEN_REFRESH_DELTA_MINUTES,
    TOKEN_CLEANUP_MAX_AGE_SECONDS,
    RATE_LIMIT_WINDOW_SECONDS,
    RATE_LIMIT_MAX_REQUESTS,
    authorize_gate_request,
    consume_token,
    forward_proposal,
    expire_token,
    is_safety_capability,
    log_audit,
    refresh_token,
    request_capability,
    _cleanup_stale_tokens,
    _check_rate_limit,
    _reset_rate_limits,
)
from .nats_client import NATSGateClient
from .gatekeeper_proxy import GatekeeperProxy, NATSAgentProxy
from .safety_enforcer import SafetySubjectEnforcer

__all__ = [
    "AUDIT_LOG",
    "CAPABILITY_STORE",
    "PROPOSALS",
    "TOKEN_REGISTRY",
    "TOKEN_DEFAULT_TTL_MINUTES",
    "TOKEN_REFRESH_DELTA_MINUTES",
    "TOKEN_CLEANUP_MAX_AGE_SECONDS",
    "RATE_LIMIT_WINDOW_SECONDS",
    "RATE_LIMIT_MAX_REQUESTS",
    "NATSGateClient",
    "GatekeeperProxy",
    "NATSAgentProxy",
    "SafetySubjectEnforcer",
    "authorize_gate_request",
    "consume_token",
    "forward_proposal",
    "is_safety_capability",
    "log_audit",
    "refresh_token",
    "expire_token",
    "_cleanup_stale_tokens",
    "_check_rate_limit",
    "_reset_rate_limits",
    "request_capability",
]
