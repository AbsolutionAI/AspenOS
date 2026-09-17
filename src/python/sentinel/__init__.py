"""
Aspen Sentinel package — audit trail + fleet overview subsystem (ADR-0007).

Exports:
- AuditEventPublisher: JSONL + JetStream publisher.
- AuditEventConsumer: Local-first consumer (journal + optional NATS live).
- FleetOverviewProducer: fleet heartbeat fan-in → ``aspen.sentinel.fleet.overview``.
- build_event / utc_now / SUBJECT_* helpers.
"""

from .audit import (
    DEFAULT_STREAM_NAME,
    SUBJECT_AUDIT_EVENT,
    AuditEventPublisher,
    build_event,
    utc_now,
)
from .consumer import AuditEventConsumer, SUBJECT_FLEET_OVERVIEW
from .fleet_overview import (
    SUBJECT_FLEET_HEARTBEAT,
    SUBJECT_FLEET_OPS_STATUS,
    SUBJECT_FLEET_REGISTER,
    FleetOverviewProducer,
)

__all__ = [
    "DEFAULT_STREAM_NAME",
    "SUBJECT_AUDIT_EVENT",
    "SUBJECT_FLEET_OVERVIEW",
    "SUBJECT_FLEET_HEARTBEAT",
    "SUBJECT_FLEET_OPS_STATUS",
    "SUBJECT_FLEET_REGISTER",
    "AuditEventPublisher",
    "AuditEventConsumer",
    "FleetOverviewProducer",
    "build_event",
    "utc_now",
]