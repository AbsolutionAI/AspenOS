#!/usr/bin/env python3
"""
Minimal Gatekeeper Shim (ADR-0009) — NATS-integrated
====================================================
Local-first, offline-capable mediator between agents and real systems.

Flow:
1. Agent emits propose_act on aspen.authz.gate.request (or calls directly)
2. Shim validates capability against profile (Light Cell / Full Plant)
3. If safety-adjacent → register a pending proposal, NEVER forward until two
   distinct humans authorize via aspen.authz.gate.decision; a bare forward or
   single-human forward is refused
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
        "aspen.edge.*.command:write",
        "aspen.safety.*:execute",
        "aspen.fleet.mission.start:execute",
    ],
    "aspen-sentinel": [
        "aspen.sentinel.*:read",
        "aspen.authz.gate.decision:write",
    ],
}

AUDIT_LOG: list[Dict[str, Any]] = []

# Dual-human authorization window (mirrors ASP-538 CLEAR_AUTH_WINDOW).
DUAL_HUMAN_REQUIRED = 2
AUTH_WINDOW_SECONDS = 300

# Pending dual-human authorization proposals, keyed by request_id.
PROPOSALS: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Audit (local + optional NATS + optional sentinel publisher)
# ---------------------------------------------------------------------------
_nats_client: Any = None  # Optional NATSGateClient reference
_audit_publisher: Any = None  # Optional sentinel.AuditEventPublisher


def log_audit(event: Dict[str, Any]) -> None:
    """Record an audit event to the local buffer (always) and NATS (best-effort).

    The local AUDIT_LOG is the durable write-path. NATS publishing is
    attempted when a client reference has been registered. When a sentinel
    AuditEventPublisher is registered (ASP-537) events also fan into the
    durable aspen.sentinel.audit.event JSONL + JetStream trail.
    """
    event["ts"] = event.get("ts") or (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    AUDIT_LOG.append(event)

    # Print is the simplest always-available display
    print(f"[AUDIT] {json.dumps(event)}", flush=True)

    # Durable sentinel audit trail (JSONL always + JetStream best-effort)
    if _audit_publisher is not None:
        try:
            _audit_publisher.record_event_sync(event)
        except Exception as exc:
            logger.warning("Sentinel audit publish failed: %s", exc)

    # Best-effort NATS publish if client is registered
    if _nats_client is not None:
        try:
            # Use the running event loop; fire-and-forget
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_nats_client.publish_audit(event))
        except RuntimeError:
            pass  # No running loop — skip NATS publish


def set_audit_publisher(publisher: Any) -> None:
    """Register a sentinel.AuditEventPublisher for the durable audit trail."""
    global _audit_publisher
    _audit_publisher = publisher


def set_nats_client(client: Any) -> None:
    """Register a NATSGateClient for best-effort event publishing."""
    global _nats_client
    _nats_client = client


# ---------------------------------------------------------------------------
# Core decision engine
# ---------------------------------------------------------------------------
SAFETY_SUBJECTS = [
    "aspen.safety.*",
    "aspen.edge.*.command",
    "aspen.fleet.mission.start",
]


def _subject_match(pattern: str, subject: str) -> bool:
    """Match a NATS-style subject pattern.

    ``\\*`` matches a single token; ``\\>`` matches the whole tail. A trailing
    ``*`` (e.g. ``aspen.safety.*``) additionally matches the full subtree, so
    ``aspen.safety.*`` covers ``aspen.safety.estop`` and deeper paths.
    """
    parts = pattern.split(".")
    tokens = subject.split(".")

    # Trailing "*" behaves as a subtree wildcard.
    if parts[-1] == "*":
        prefix = parts[:-1]
        if len(tokens) < len(prefix):
            return False
        return all(p == t for p, t in zip(prefix, tokens))

    if ">" in parts:
        idx = parts.index(">")
        if len(tokens) < idx:
            return False
        for i in range(idx):
            if parts[i] != "*" and parts[i] != tokens[i]:
                return False
        return True

    if len(parts) != len(tokens):
        return False
    for p, t in zip(parts, tokens):
        if p != "*" and p != t:
            return False
    return True


def is_safety_capability(capability: str, patterns=None) -> bool:
    """True when a capability targets a safety-adjacent subject.

    The pattern is matched against the capability's subject portion (any
    ``:action`` suffix is stripped). Supports '\\*' (single token) and '\\>'
    (tail) wildcards.
    """
    subject = capability.split(":", 1)[0]
    return any(_subject_match(p, subject) for p in (patterns or SAFETY_SUBJECTS))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_expired(proposal: Dict[str, Any]) -> bool:
    try:
        expires = datetime.fromisoformat(proposal["expires_at"])
    except (KeyError, ValueError):
        return True
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= expires


def _register_proposal(
    agent_id: str,
    capability: str,
    resource: str,
    profile: str,
    request_id: str,
) -> Dict[str, Any]:
    """Register a pending dual-human proposal (safety-adjacent path)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=AUTH_WINDOW_SECONDS)
    proposal: Dict[str, Any] = {
        "request_id": request_id,
        "agent_id": agent_id,
        "capability": capability,
        "resource": resource,
        "profile": profile,
        "state": "pending",
        "humans": [],
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
    }
    PROPOSALS[request_id] = proposal
    return proposal


def _awaiting_dict(proposal: Dict[str, Any], note: Optional[str] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "decision": "awaiting",
        "request_id": proposal["request_id"],
        "status": "awaiting_authorization",
        "humans": list(proposal["humans"]),
        "humans_required": DUAL_HUMAN_REQUIRED,
    }
    if note:
        result["note"] = note
    return result


def _refusal_dict(proposal: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "decision": "refuse",
        "request_id": proposal["request_id"],
        "reason": proposal.get("reason", "insufficient_humans"),
        "status": "refused",
        "humans": list(proposal["humans"]),
        "humans_required": DUAL_HUMAN_REQUIRED,
    }


def _grant_dict(proposal: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "decision": "grant",
        "request_id": proposal["request_id"],
        "token": proposal["token"],
        "humans": list(proposal["humans"]),
        "requires": "dual_human",
    }


def _mark_refused(proposal: Dict[str, Any], reason: str) -> None:
    proposal["state"] = "refused"
    proposal["decision"] = "refuse"
    proposal["reason"] = reason
    proposal["updated_at"] = _utc_now()
    log_audit({
        "type": "gate.refuse",
        "request_id": proposal["request_id"],
        "agent_id": proposal["agent_id"],
        "capability": proposal["capability"],
        "resource": proposal["resource"],
        "decision": "refuse",
        "reason": reason,
        "humans": list(proposal["humans"]),
        "humans_required": DUAL_HUMAN_REQUIRED,
    })


def _grant_proposal(proposal: Dict[str, Any]) -> Dict[str, Any]:
    """Mint a short-lived scoped token after dual-human authorization."""
    token = {
        "token_id": str(uuid.uuid4()),
        "agent_id": proposal["agent_id"],
        "capability": proposal["capability"],
        "resource": proposal["resource"],
        "expires": (
            datetime.now(timezone.utc) + timedelta(minutes=15)
        ).isoformat().replace("+00:00", "Z"),
        "scope": proposal["profile"],
        "authorized_by": list(proposal["humans"]),
    }
    proposal["state"] = "granted"
    proposal["decision"] = "grant"
    proposal["token"] = token
    proposal["updated_at"] = _utc_now()

    log_audit({
        "type": "capability.grant",
        "request_id": proposal["request_id"],
        "agent_id": proposal["agent_id"],
        "capability": proposal["capability"],
        "resource": proposal["resource"],
        "token_id": token["token_id"],
        "decision": "grant",
        "humans": list(proposal["humans"]),
        "humans_required": DUAL_HUMAN_REQUIRED,
    })
    return _grant_dict(proposal)


def authorize_gate_request(
    request_id: str,
    human_id: str,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Record one human authorization toward the dual-human threshold.

    A proposal is forwarded (granted) only once two *distinct* humans have
    authorized within ``AUTH_WINDOW_SECONDS``. Duplicate humans never advance
    the count (H-009 distinct-principal enforcement).
    """
    proposal = PROPOSALS.get(request_id)
    human_id = (human_id or "").strip()

    if proposal is None or not human_id:
        log_audit({
            "type": "gate.refuse",
            "request_id": request_id,
            "actor": human_id or "unknown",
            "decision": "refuse",
            "reason": "unknown_request",
            "humans": [],
            "humans_required": DUAL_HUMAN_REQUIRED,
        })
        return {
            "decision": "refuse",
            "request_id": request_id,
            "reason": "unknown_request",
            "humans": [],
            "humans_required": DUAL_HUMAN_REQUIRED,
        }

    if proposal["state"] == "granted":
        return _grant_dict(proposal)
    if proposal["state"] == "refused":
        return _refusal_dict(proposal)

    if _is_expired(proposal):
        _mark_refused(proposal, "authorization_window_expired")
        return _refusal_dict(proposal)

    if human_id in proposal["humans"]:
        log_audit({
            "type": "gate.authorize.duplicate",
            "actor": human_id,
            "request_id": request_id,
            "agent_id": proposal["agent_id"],
            "capability": proposal["capability"],
            "resource": proposal["resource"],
            "decision": "duplicate",
            "humans": list(proposal["humans"]),
            "humans_required": DUAL_HUMAN_REQUIRED,
        })
        return _awaiting_dict(proposal, note="duplicate_human_ignored")

    proposal["humans"].append(human_id)
    proposal["updated_at"] = _utc_now()

    log_audit({
        "type": "gate.authorize",
        "actor": human_id,
        "request_id": request_id,
        "agent_id": proposal["agent_id"],
        "capability": proposal["capability"],
        "resource": proposal["resource"],
        "decision": "approved",
        "auth_count": len(proposal["humans"]),
        "humans_required": DUAL_HUMAN_REQUIRED,
        "note": note or "",
    })

    if len(proposal["humans"]) >= DUAL_HUMAN_REQUIRED:
        return _grant_proposal(proposal)
    return _awaiting_dict(proposal)


def forward_proposal(request_id: str) -> Dict[str, Any]:
    """Forward gate: a proposal may only be forwarded once authorized.

    Refuses bare / single-human / expired / unknown forwards. Grants return
    idempotently once previously authorized.
    """
    proposal = PROPOSALS.get(request_id)
    if proposal is None:
        return {
            "decision": "refuse",
            "request_id": request_id,
            "reason": "unknown_request",
            "humans": [],
            "humans_required": DUAL_HUMAN_REQUIRED,
        }
    if proposal["state"] == "granted":
        return _grant_dict(proposal)
    if proposal["state"] == "refused":
        return _refusal_dict(proposal)
    if _is_expired(proposal):
        _mark_refused(proposal, "authorization_window_expired")
    else:
        _mark_refused(proposal, "insufficient_humans")
    return _refusal_dict(proposal)


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

    # 2. Safety-adjacent check — register a pending proposal, never forward.
    if is_safety_capability(capability):
        proposal = _register_proposal(agent_id, capability, resource, profile, request_id)
        log_audit({
            "type": "propose_act.pending",
            "request_id": request_id,
            "agent_id": agent_id,
            "capability": capability,
            "resource": resource,
            "decision": "pending",
            "humans_required": DUAL_HUMAN_REQUIRED,
            "note": "awaiting dual-human authorization",
        })
        return {
            "decision": "propose_act",
            "request_id": request_id,
            "requires": "dual_human",
            "status": "awaiting_authorization",
            "humans_required": DUAL_HUMAN_REQUIRED,
            "humans": [],
            "message": "Awaiting two distinct humans on aspen.authz.gate.decision",
            "proposal": {
                "request_id": proposal["request_id"],
                "expires_at": proposal["expires_at"],
            },
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


async def _handle_gate_decision(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle an inbound human authorization on aspen.authz.gate.decision.

    Only messages that carry a singular ``human_id`` + ``request_id`` count as
    authorizations (so the gatekeeper's own emits on the same subject never
    self-approve). Returns None for non-authorization traffic.
    """
    human_id = data.get("human_id") or data.get("human")
    request_id = data.get("request_id")
    if not human_id or not request_id:
        return None
    return authorize_gate_request(str(request_id), str(human_id), note=data.get("note"))


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
        decision_handler=_handle_gate_decision,
    )
    set_nats_client(client)

    # Durable sentinel audit trail publisher (ADR-0007 / H-015 / ASP-537).
    try:
        from sentinel import AuditEventPublisher

        publisher = AuditEventPublisher(nats_url=nats_url)
        await publisher.start()
        set_audit_publisher(publisher)
        logger.info("Sentinel audit publisher active (journal: %s)", publisher.audit_log_path)
    except Exception as exc:
        logger.warning("Sentinel audit publisher unavailable: %s", exc)

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
    print(f"  Listening on: {NATSGateClient.SUBJECT_REQUEST},", flush=True)
    print(f"                {NATSGateClient.SUBJECT_DECISION} (human authz)", flush=True)
    print(f"  Publishing to: {NATSGateClient.SUBJECT_DECISION},", flush=True)
    print(f"                   {NATSGateClient.SUBJECT_AUDIT},", flush=True)
    print(f"                   {NATSGateClient.SUBJECT_GRANT}", flush=True)
    print("  Press Ctrl+C to stop.\n", flush=True)

    try:
        # Keep alive — NATS subscriptions run in the background
        while True:
            await asyncio.sleep(5)
            if _audit_publisher is not None and _audit_publisher.pending_count:
                n = await _audit_publisher.replay_pending()
                if n:
                    logger.info("Drained %d queued events to the sentinel audit trail", n)
            if client.offline_buffer_size:
                n = await client.drain_offline_buffer()
                if n:
                    logger.info("Drained %d queued events from offline buffer", n)
    except asyncio.CancelledError:
        pass
    finally:
        if _audit_publisher is not None:
            try:
                await _audit_publisher.close()
            except Exception:
                pass
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

    # Example 2: Safety-adjacent (estop) → dual-human authorization cycle
    print("\nRequest 2 (estop):")
    result2 = request_capability(
        "aspen-fleet-edge",
        "aspen.safety.estop:execute",
        "plant:chae-cell-01",
        {"profile": "full-plant"},
    )
    print(json.dumps(result2, indent=2, default=str))

    print("\nBare forward BEFORE any human authorization = REFUSED:")
    print(json.dumps(forward_proposal(result2["request_id"]), indent=2, default=str))

    print("\nRequest 2b (estop, fresh proposal) → one human alone does NOT authorize:")
    result2b = request_capability(
        "aspen-fleet-edge",
        "aspen.safety.estop:execute",
        "plant:chae-cell-01",
        {"profile": "full-plant"},
    )
    print(json.dumps(authorize_gate_request(result2b["request_id"], "operator-1"), indent=2, default=str))
    print("Duplicate same human still does NOT authorize:")
    print(json.dumps(authorize_gate_request(result2b["request_id"], "operator-1"), indent=2, default=str))
    print("Second distinct human → GRANT (token minted):")
    print(json.dumps(authorize_gate_request(result2b["request_id"], "operator-2"), indent=2, default=str))
    print("Forward after authorization → idempotent GRANT:")
    print(json.dumps(forward_proposal(result2b["request_id"]), indent=2, default=str))

    # Example 3: Unknown agent (deny)
    print("\nRequest 3 (unknown agent):")
    result3 = request_capability(
        "aspen-unknown-agent",
        "aspen.fleet.mission.start",
        "plant:chae-cell-01",
        {"profile": "light-cell"},
    )
    print(json.dumps(result3, indent=2, default=str))

    print(f"\nAudit log entries: {len(AUDIT_LOG)}")
    print(f"Pending proposals: {len([p for p in PROPOSALS.values() if p['state'] == 'pending'])}")
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