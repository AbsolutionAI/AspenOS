"""
Gatekeeper package — ADR-0009 capability-based authorization shim.

Exports:
- NATSGateClient: NATS client wrapper with offline-fallback buffer
- request_capability: core gatekeeper decision logic (from minimal_shim)
- log_audit: audit event writer (local buffer + optional NATS publish)
"""

from .minimal_shim import AUDIT_LOG, CAPABILITY_STORE, log_audit, request_capability
from .nats_client import NATSGateClient

__all__ = [
    "AUDIT_LOG",
    "CAPABILITY_STORE",
    "NATSGateClient",
    "log_audit",
    "request_capability",
]