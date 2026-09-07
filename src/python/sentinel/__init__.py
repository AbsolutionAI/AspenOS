"""
Aspen Sentinel package — audit trail subsystem (ADR-0007 / H-015 / ASP-537).

Exports:
- AuditEventPublisher: JSONL + JetStream publisher for the
  ``aspen.sentinel.audit.event`` subject with the {event_id, actor, action,
  target, result, ts} envelope.
- build_event / SUBJECT_AUDIT_EVENT helpers.
"""

from .audit import (
    DEFAULT_STREAM_NAME,
    SUBJECT_AUDIT_EVENT,
    AuditEventPublisher,
    build_event,
    utc_now,
)

__all__ = [
    "DEFAULT_STREAM_NAME",
    "SUBJECT_AUDIT_EVENT",
    "AuditEventPublisher",
    "build_event",
    "utc_now",
]