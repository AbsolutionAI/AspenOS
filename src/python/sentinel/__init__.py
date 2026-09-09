"""
Aspen Sentinel package — audit trail subsystem (ADR-0007 / H-015 / ASP-537).

Exports:
- AuditEventPublisher: JSONL + JetStream publisher.
- AuditEventConsumer: Local-first consumer (journal + optional NATS live).
- build_event / SUBJECT_AUDIT_EVENT helpers.
"""

from .audit import (
    DEFAULT_STREAM_NAME,
    SUBJECT_AUDIT_EVENT,
    AuditEventPublisher,
    build_event,
    utc_now,
)
from .consumer import AuditEventConsumer, SUBJECT_FLEET_OVERVIEW

__all__ = [
    "DEFAULT_STREAM_NAME",
    "SUBJECT_AUDIT_EVENT",
    "SUBJECT_FLEET_OVERVIEW",
    "AuditEventPublisher",
    "AuditEventConsumer",
    "build_event",
    "utc_now",
]