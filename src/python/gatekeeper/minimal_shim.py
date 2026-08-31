#!/usr/bin/env python3
"""
Minimal Gatekeeper Shim (ADR-0009) — NATS-integrated
====================================================
Local-first, offline-capable mediator between agents and real systems.

Flow:
1. Agent emits propose_act on aspen.authz.gate.request (or calls directly)
2. Shim validates capability against profile (Light Cell / Full Plant)
3. If safety-adjacent → require dual-human (simulated here)
4. Issue short-lived scoped token or deny + audit log
5. Never hands out broad credentials

Offline-capable fallback:
- When no NATS broker is available, events buffer locally.
- All published subjects are *best-effort*: the shim never blocks on NATS.
- Agent credentials are NEVER embedded in this code.

Run as daemon:
    python3 minimal_shim.py                    # offline mode
    ASPEN_NATS_URL=nats://localhost:4222 python3 minimal_shim.py
    python3 minimal_shim.py --nats-url nats://broker:4222

Importable:
    from gatekeeper.minimal_shim import request_capability, log_audit
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("gatekeeper.shim")

# ---------------------------------------------------------------------------
# Core in-memory capability store (replace with PG/Redis in real impl)
# ---------------------------------------------------------------------------
CAPABILITY_STORE: Dict[str, list] = {
    "aspen-fleet-edge": [
        "aspen.fleet.node.heartbeat:read",
        "aspen.edge.*.propose_act:write",
    ],
    "aspen-sentinel": [
        "aspen.sentinel.*:read",
        "aspen.authz.gate.decision:write",
    ],
}

AUDIT_LOG: list[Dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Audit (local + optional NATS)
# ---------------------------------------------------------------------------
_nats_client: Any = None  # Optional NATSGateClient reference


def log_audit(event: Dict[str, Any]) -> None:
    """Record an audit event to the local buffer (always) and NATS (best-effort).

    The local AUDIT_LOG is the durable write-path. NATS publishing is
    attempted when a client reference has been registered.
    """
    event["ts"] = event.get("ts") or (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    AUDIT_LOG.append(event)

    # Print is the simplest always-available display
    print(f"[AUDIT] {json.dumps(event)}", flush=True)

    # Best-effort NATS publish if client is registered
    if _nats_client is not None:
        try:
            # Use the running event loop; fire-and-forget
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_nats_client.publish_audit(event))
        except RuntimeError:
            pass  # No running loop — skip NATS publish


def set_nats_client(client: Any) -> None:
    """Register a NATSGateClient for best-effort event publishing."""
    global _nats_client
    _nats_client = client


# ---------------------------------------------------------------------------
# Core decision engine
# ---------------------------------------------------------------------------
SAFETY_SUBJECTS = [
    "aspen.safety.",
    "aspen.edge.*.command",
    "aspen.fleet.mission.start",
]


def request_capability(
    agent_id: str,
    capability: str,
    resource: str,
    context: Dict,
) -> Dict[str, Any]:
    """Core gatekeeper decision point.

    Args:
        agent_id: The identity requesting a capability
        capability: The capability string (e.g. "aspen.fleet.node.heartbeat:read")
        resource: Target resource (e.g. "plant:chae-cell-01")
        context: Dict with "profile" key ("light-cell" | "full-plant"), etc.

    Returns:
        Dict with "decision" ("grant"|"deny"|"propose_act") and supporting fields.
    """
    request_id = str(uuid.uuid4())
    profile = context.get("profile", "light-cell")

    # 1. Basic capability check
    allowed_caps = CAPABILITY_STORE.get(agent_id, [])

    def _cap_match(requested: str, allowed: str) -> bool:
        """Check if a requested capability matches an allowed pattern.

        Supports glob-like wildcards via '.*':
        - "aspen.fleet.*:read" matches "aspen.fleet.node.heartbeat:read"
        - "aspen.sentinel.*:read" matches "aspen.sentinel.audit.event:read"
        - "aspen.edge.*.propose_act:write" matches "aspen.edge.cell01.propose_act:write"
        """
        if ".*" in allowed:
            prefix, _, suffix = allowed.partition(".*")
            if not requested.startswith(prefix):
                return False
            if suffix and not requested.endswith(suffix):
                return False
            return True
        return requested == allowed

    has_match = any(
        _cap_match(capability, allowed) or _cap_match(capability.split(":")[0], allowed)
        for allowed in allowed_caps
    )

    if not has_match:
        log_audit({
            "type": "capability.deny",
            "request_id": request_id,
            "agent_id": agent_id,
            "capability": capability,
            "reason": "capability_not_granted",
        })
        return {"decision": "deny", "reason": "capability_not_granted", "request_id": request_id}

    # 2. Safety-adjacent check
    is_safety = any(s in capability for s in SAFETY_SUBJECTS)

    if is_safety:
        log_audit({
            "type": "propose_act.safety",
            "request_id": request_id,
            "agent_id": agent_id,
            "capability": capability,
            "resource": resource,
            "note": "awaiting dual-human authorization",
        })
        return {
            "decision": "propose_act",
            "request_id": request_id,
            "requires": "dual_human",
            "message": "Emit aspen.authz.gate.request and wait for decision",
        }

    # 3. Grant short-lived token
    token = {
        "token_id": str(uuid.uuid4()),
        "agent_id": agent_id,
        "capability": capability,
        "resource": resource,
        "expires": (
            datetime.now(timezone.utc) + timedelta(minutes=15)
        ).isoformat().replace("+00:00", "Z"),
        "scope": profile,
    }

    log_audit({
        "type": "capability.grant",
        "request_id": request_id,
        "agent_id": agent_id,
        "capability": capability,
        "token_id": token["token_id"],
    })

    return {"decision": "grant", "token": token, "request_id": request_id}


# ---------------------------------------------------------------------------
# NATS handler — processes messages from aspen.authz.gate.request
# ---------------------------------------------------------------------------
async def _handle_gate_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle an incoming gate request from NATS.

    This is the callback registered with NATSGateClient.subscribe().
    It calls request_capability() and publishes the result on gate.decision.
    """
    agent_id = data.get("agent_id", data.get("proposer_agent_id", "unknown"))
    capability = data.get("capability", "")
    resource = data.get("resource", "")
    context = data.get("context", {})
    profile = data.get("profile", context.get("profile", "light-cell"))

    if not capability:
        return {"decision": "deny", "reason": "missing_capability", "request_id": str(uuid.uuid4())}

    result = request_capability(agent_id, capability, resource, {**context, "profile": profile})
    return result


# ---------------------------------------------------------------------------
# Main entry point — run as a daemon
# ---------------------------------------------------------------------------
async def run_daemon(
    nats_url: Optional[str] = None,
    log_level: str = "INFO",
    one_shot: bool = False,
) -> None:
    """Run the gatekeeper as a NATS-connected daemon.

    Args:
        nats_url: NATS broker URL (None = offline mode).
        log_level: Logging level.
        one_shot: If True, connect, run one demo cycle, and exit.
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    # Import here to avoid circular dependency
    from .nats_client import NATSGateClient

    client = NATSGateClient(
        nats_url=nats_url,
        offline_fallback=True,
        request_handler=_handle_gate_request,
    )
    set_nats_client(client)

    connected = await client.connect()
    if connected:
        logger.info("NATS connected — gatekeeper is online")
    else:
        logger.info("NATS offline — gatekeeper in local-only mode")

    if one_shot:
        # Run one demo cycle, then exit
        _run_demo(client)
        await asyncio.sleep(0.5)
        await client.close()
        return

    # Daemon mode: keep running, handling NATS messages
    print(f"\n=== Gatekeeper Daemon (ADR-0009) ===", flush=True)
    print(f"  Mode: {'ONLINE' if client.is_online else 'OFFLINE (local-only)'}", flush=True)
    print(f"  Listening on: {NATSGateClient.SUBJECT_REQUEST}", flush=True)
    print(f"  Publishing to: {NATSGateClient.SUBJECT_DECISION},", flush=True)
    print(f"                   {NATSGateClient.SUBJECT_AUDIT},", flush=True)
    print(f"                   {NATSGateClient.SUBJECT_GRANT}", flush=True)
    print("  Press Ctrl+C to stop.\n", flush=True)

    try:
        # Keep alive — NATS subscriptions run in the background
        while True:
            await asyncio.sleep(5)
            if client.offline_buffer_size:
                n = await client.drain_offline_buffer()
                if n:
                    logger.info("Drained %d queued events from offline buffer", n)
    except asyncio.CancelledError:
        pass
    finally:
        await client.close()
        logger.info("Gatekeeper daemon stopped")


def _run_demo(client: Any) -> None:
    """Run the demo capability request cycle (for one_shot mode)."""
    print("\n=== Demo: Gatekeeper Decision Cycle ===\n")

    # Example 1: Normal heartbeat (non-safety)
    result = request_capability(
        "aspen-fleet-edge",
        "aspen.fleet.node.heartbeat:read",
        "plant:chae-cell-01",
        {"profile": "light-cell"},
    )
    print("Request 1 (heartbeat):", json.dumps(result, indent=2, default=str))

    # Example 2: Safety-adjacent (estop)
    result2 = request_capability(
        "aspen-fleet-edge",
        "aspen.safety.estop:execute",
        "plant:chae-cell-01",
        {"profile": "full-plant"},
    )
    print("\nRequest 2 (estop):", json.dumps(result2, indent=2, default=str))

    # Example 3: Unknown agent (deny)
    result3 = request_capability(
        "aspen-unknown-agent",
        "aspen.fleet.mission.start",
        "plant:chae-cell-01",
        {"profile": "light-cell"},
    )
    print("\nRequest 3 (unknown agent):", json.dumps(result3, indent=2, default=str))

    print(f"\nAudit log entries: {len(AUDIT_LOG)}")
    print(f"NATS offline buffer: {client.offline_buffer_size}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ADR-0009 Gatekeeper Shim")
    parser.add_argument("--nats-url", help="NATS broker URL (default: $ASPEN_NATS_URL)")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument(
        "--demo", action="store_true",
        help="Run one-shot demo and exit (default: continuous daemon)",
    )
    args = parser.parse_args()

    nats_url = args.nats_url or os.environ.get("ASPEN_NATS_URL")

    if args.demo:
        asyncio.run(run_daemon(nats_url=nats_url, log_level=args.log_level, one_shot=True))
    else:
        try:
            asyncio.run(run_daemon(nats_url=nats_url, log_level=args.log_level))
        except KeyboardInterrupt:
            print("\nShutdown by user.")
            sys.exit(0)