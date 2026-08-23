# BEL-191 Durable audit log

Hash-chained JSONL in `aspen-edge-rrm` (`aspen_edge/audit.py`).

RRM writes propose_act, estop, clear, agent lifecycle events.

Verify: `AuditLog.verify()` / package tests `tests/test_audit.py`.

**Verified (2026-08-23):** chain + tamper detection green in package smoke (`@aa3f84d`).
