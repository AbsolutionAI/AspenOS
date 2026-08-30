#!/usr/bin/env python3
"""
Minimal Gatekeeper Shim (ADR-0009 prototype)
Local-first, offline-capable mediator between agents and real systems.

Flow:
1. Agent emits propose_act on aspen.authz.gate.request
2. Shim validates capability against profile (Light Cell / Full Plant)
3. If safety-adjacent → require dual-human (simulated here)
4. Issue short-lived scoped token or deny + audit log
5. Never hands out broad credentials

Run: python3 minimal_shim.py
"""

import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

# Simple in-memory capability store (replace with PG/Redis in real impl)
CAPABILITY_STORE: Dict[str, list] = {
    "aspen-fleet-edge": ["aspen.fleet.node.heartbeat:read", "aspen.edge.*.propose_act:write"],
    "aspen-sentinel": ["aspen.sentinel.*:read", "aspen.authz.gate.decision:write"],
}

AUDIT_LOG = []

def log_audit(event: Dict[str, Any]) -> None:
    """Write to aspen.sentinel.audit.event (stub — real impl publishes to NATS)."""
    event["ts"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    AUDIT_LOG.append(event)
    print(f"[AUDIT] {json.dumps(event)}")

def request_capability(agent_id: str, capability: str, resource: str, context: Dict) -> Dict[str, Any]:
    """
    Core gatekeeper decision point.
    Returns grant token or deny with reason.
    """
    request_id = str(uuid.uuid4())
    profile = context.get("profile", "light-cell")

    # 1. Basic capability check
    allowed_caps = CAPABILITY_STORE.get(agent_id, [])
    if not any(cap in allowed_caps or cap.endswith(".*") for cap in allowed_caps):
        # simplistic wildcard match
        if not any(c.startswith(capability.split(":")[0]) for c in allowed_caps):
            log_audit({
                "type": "capability.deny",
                "request_id": request_id,
                "agent_id": agent_id,
                "capability": capability,
                "reason": "capability_not_granted"
            })
            return {"decision": "deny", "reason": "capability_not_granted", "request_id": request_id}

    # 2. Safety-adjacent check (simplified)
    safety_subjects = ["aspen.safety.", "aspen.edge.*.command", "aspen.fleet.mission.start"]
    is_safety = any(s in capability for s in safety_subjects)

    if is_safety:
        # In real system: emit propose_act and wait for aspen.authz.gate.decision (dual human)
        log_audit({
            "type": "propose_act.safety",
            "request_id": request_id,
            "agent_id": agent_id,
            "capability": capability,
            "resource": resource,
            "note": "awaiting dual-human authorization"
        })
        return {
            "decision": "propose_act",
            "request_id": request_id,
            "requires": "dual_human",
            "message": "Emit aspen.authz.gate.request and wait for decision"
        }

    # 3. Grant short-lived token
    token = {
        "token_id": str(uuid.uuid4()),
        "agent_id": agent_id,
        "capability": capability,
        "resource": resource,
        "expires": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat().replace("+00:00", "Z"),
        "scope": profile
    }

    log_audit({
        "type": "capability.grant",
        "request_id": request_id,
        "agent_id": agent_id,
        "capability": capability,
        "token_id": token["token_id"]
    })

    return {"decision": "grant", "token": token, "request_id": request_id}

# Demo
if __name__ == "__main__":
    print("=== Minimal Gatekeeper Shim (ADR-0009) ===\n")

    # Example 1: Normal heartbeat (non-safety)
    result = request_capability(
        "aspen-fleet-edge",
        "aspen.fleet.node.heartbeat:read",
        "plant:chaé-cell-01",
        {"profile": "light-cell"}
    )
    print("Result 1:", json.dumps(result, indent=2))

    # Example 2: Safety-adjacent (estop)
    result2 = request_capability(
        "aspen-fleet-edge",
        "aspen.safety.estop:execute",
        "plant:chaé-cell-01",
        {"profile": "full-plant"}
    )
    print("\nResult 2:", json.dumps(result2, indent=2))

    print("\nAudit log entries:", len(AUDIT_LOG))
    print("Shim ready for integration with NATS / Paperclip adapters.")