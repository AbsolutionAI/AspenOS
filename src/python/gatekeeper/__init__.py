"""
Gatekeeper package — ADR-0009 capability-based authorization shim.

Exports:
- NATSGateClient: NATS client wrapper with offline-fallback buffer
- request_capability: core gatekeeper decision logic (from minimal_shim)
- authorize_gate_request: record a human authorization toward dual-human grant
- forward_proposal: forward gate — refuses until two distinct humans authorize
- log_audit: audit event writer (local buffer + optional NATS publish)
"""

from .minimal_shim import (
    AUDIT_LOG,
    CAPABILITY_STORE,
    PROPOSALS,
    authorize_gate_request,
    forward_proposal,
    is_safety_capability,
    log_audit,
    request_capability,
)
from .nats_client import NATSGateClient

__all__ = [
    "AUDIT_LOG",
    "CAPABILITY_STORE",
    "PROPOSALS",
    "NATSGateClient",
    "authorize_gate_request",
    "forward_proposal",
    "is_safety_capability",
    "log_audit",
    "request_capability",
]