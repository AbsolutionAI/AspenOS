#!/usr/bin/env python3
"""
GatekeeperProxy — Hermes/Paperclip credential strip adapter (ADR-0009 Phase 2)
================================================================================

Agents never hold broad credentials. Instead they hold only a gatekeeper
endpoint reference. All outbound external calls (NATS, API, ROS2, etc.) are
routed through the gatekeeper's ``request_capability`` flow, which issues
short-lived scoped capability tokens.

Key principles:
1. **No broad credentials in agent images.** Agent images reference
   ``GatekeeperProxy`` with a NATS endpoint only.
2. **Short-lived tokens.** Every external action acquires a fresh token from
   the gatekeeper, which is consumed (one-shot) on success.
3. **Token refresh.** Long-running operations may refresh tokens before expiry.
4. **Audit-traced.** Every acquire, consume, refresh, and deny is logged.

Usage:
    from gatekeeper.gatekeeper_proxy import GatekeeperProxy, NATSAgentProxy

    proxy = NATSAgentProxy(
        agent_id="aspen-fleet-edge",
        gatekeeper_endpoint="nats://localhost:4222",
    )
    await proxy.connect()

    # Acquire a capability token
    result = proxy.request_capability(
        "aspen.edge.cell-01.command:write",
        "plant:chae-cell-01",
    )
    if result["decision"] == "grant":
        # Execute the action (token will be consumed)
        proxy.execute_with_token(
            result["token_id"],
            lambda: publish_command("cell-01", "stop"),
        )

    await proxy.close()
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("gatekeeper.proxy")


class GatekeeperProxy:
    """Agent-side gatekeeper proxy that routes external calls through the
    gatekeeper authorization flow.

    Agents instantiate this proxy instead of holding broad credentials. The
    proxy interacts with the gatekeeper via ``request_capability()`` to obtain
    short-lived scoped tokens.

    Subclasses implement the wire transport (NATS, HTTP, etc.) via the
    ``_send_request()`` and ``_send_decision()`` abstract methods.
    """

    def __init__(self, agent_id: str) -> None:
        """
        Args:
            agent_id: The identity of the agent using this proxy.
        """
        self._agent_id = agent_id
        self._token_cache: Dict[str, Dict[str, Any]] = {}

    @property
    def agent_id(self) -> str:
        return self._agent_id

    # ---- Transport layer (override in subclasses) -------------------------

    async def connect(self) -> bool:
        """Establish connection to the gatekeeper. Default: no-op."""
        return True

    async def close(self) -> None:
        """Tear down the connection. Default: no-op."""
        pass

    async def _send_request(
        self,
        capability: str,
        resource: str,
        profile: str,
    ) -> Dict[str, Any]:
        """Transport-specific send of a capability request.

        Must be overridden by subclasses that wire through NATS, HTTP, or
        other transports. Returns the gatekeeper's response dict.
        """
        raise NotImplementedError("Subclasses must implement _send_request")

    async def _send_authorization(
        self,
        request_id: str,
        human_id: str,
    ) -> Dict[str, Any]:
        """Transport-specific send of a human authorization decision.

        Must be overridden by subclasses. Returns the gatekeeper's response.
        """
        raise NotImplementedError("Subclasses must implement _send_authorization")

    # ---- Agent-facing API -------------------------------------------------

    def request_capability(
        self,
        capability: str,
        resource: str,
        profile: str = "light-cell",
    ) -> Dict[str, Any]:
        """Request a capability from the gatekeeper.

        This is the primary entry point for agents. The gatekeeper evaluates
        the request and either:
        - Returns a ``grant`` with a short-lived scoped token, or
        - Returns ``propose_act`` (requires dual-human authorization), or
        - Returns ``deny``.

        The returned token from a ``grant`` is cached in ``_token_cache`` for
        the caller's convenience, but the caller is responsible for consuming
        the token after use via ``consume_token`` or ``execute_with_token``.
        """
        # Import here to avoid circular import
        from .minimal_shim import request_capability as _gate_cap

        result = _gate_cap(self._agent_id, capability, resource, {"profile": profile})

        if result.get("decision") == "grant" and "token" in result:
            tid = result["token"].get("token_id")
            if tid:
                result["token_id"] = tid
                self._token_cache[tid] = result

        return result

    def execute_with_token(
        self,
        token_id: str,
        action_fn: Callable[[], Any],
    ) -> Dict[str, Any]:
        """Execute an action using a gatekeeper capability token.

        Acquires the token, calls ``action_fn`` with the token's capability,
        then consumes the token (one-shot) on successful execution.

        Args:
            token_id: The token_id from a previous ``request_capability()`` grant.
            action_fn: A callable that performs the actual operation. Its return
                       value is passed through the result dict.

        Returns:
            Dict with:
              - ``decision``: ``"grant"`` or ``"deny"``
              - ``action_result``: the return value of ``action_fn`` (on success)
              - ``reason``: error reason (on failure)
        """
        # Check token is active before executing
        from .minimal_shim import _is_token_active, consume_token as _consume

        if not _is_token_active(token_id):
            return {"decision": "deny", "reason": "token_not_active", "token_id": token_id}

        try:
            action_result = action_fn()
        except Exception as exc:
            logger.warning("Action failed for token %s: %s", token_id, exc)
            return {"decision": "deny", "reason": f"action_failed: {exc}", "token_id": token_id}

        # Consume the token (one-shot)
        consume_result = _consume(token_id)
        if consume_result["decision"] != "grant":
            # Action succeeded but consumption failed — unusual but not blocking
            logger.warning("Token %s consumed unexpectedly: %s", token_id, consume_result)

        return {
            "decision": "grant",
            "action_result": action_result,
            "token_id": token_id,
            "consumed": consume_result["decision"] == "grant",
        }


class NATSAgentProxy(GatekeeperProxy):
    """Concrete GatekeeperProxy that communicates with the gatekeeper
    over the NATS bus.

    Agents using this proxy hold NO broad credentials. The transport is
    configured with only a NATS endpoint URL — authentication is handled
    by the gatekeeper.

    This proxy subscribes to the gatekeeper's decision subject to receive
    human authorization responses, though in practice the gatekeeper handles
    the full authorization lifecycle internally via ``policy.py`` or the
    ``NATSGateClient`` subscription loop.
    """

    SUBJECT_REQUEST = "aspen.authz.gate.request"
    SUBJECT_DECISION = "aspen.authz.gate.decision"
    SUBJECT_GRANT = "aspen.authz.capability.grant"

    def __init__(
        self,
        agent_id: str,
        gatekeeper_endpoint: Optional[str] = None,
        offline_fallback: bool = True,
    ) -> None:
        """
        Args:
            agent_id: The identity of the agent.
            gatekeeper_endpoint: NATS broker URL (e.g. "nats://localhost:4222").
                                 Falls back to ``ASPEN_NATS_URL`` env var.
            offline_fallback: If True, allow offline operation.
        """
        import os

        super().__init__(agent_id=agent_id)
        self._endpoint = gatekeeper_endpoint or os.environ.get("ASPEN_NATS_URL", "")
        self._offline_fallback = offline_fallback
        self._nc: Any = None  # NATS connection
        self._request_id_counter = 0

    # ---- Transport implementation -----------------------------------------

    async def connect(self) -> bool:
        """Connect to the NATS broker."""
        if not self._endpoint:
            logger.info("No NATS endpoint configured — offline mode")
            return False
        try:
            import nats

            self._nc = await nats.connect(
                self._endpoint,
                max_reconnect_attempts=3,
                reconnect_time_wait=2,
                name=f"aspen-proxy-{self._agent_id}",
                ping_interval=20,
                max_outstanding_pings=5,
            )
            logger.info("Connected to gatekeeper at %s", self._endpoint)
            return True
        except Exception as exc:
            logger.warning("Gatekeeper connection failed (%s) — offline mode", exc)
            return False

    async def close(self) -> None:
        """Close the NATS connection."""
        if self._nc:
            try:
                await self._nc.drain()
                await self._nc.close()
            except Exception:
                pass
            self._nc = None

    async def _send_request(
        self,
        capability: str,
        resource: str,
        profile: str,
    ) -> Dict[str, Any]:
        """Send a gate request via NATS and wait for the decision response.

        The gatekeeper's ``NATSGateClient`` subscription picks up the request
        on ``aspen.authz.gate.request``, processes it, and publishes the
        decision on ``aspen.authz.gate.decision``.
        """
        if self._nc is None:
            raise RuntimeError("NATSAgentProxy not connected")

        self._request_id_counter += 1
        request_id = f"proxy-{self._agent_id}-{self._request_id_counter}"

        payload = {
            "agent_id": self._agent_id,
            "capability": capability,
            "resource": resource,
            "context": {"profile": profile},
            "request_id": request_id,
            "reply_to": request_id,  # Used for correlation
        }

        # Publish the request
        await self._nc.publish(
            self.SUBJECT_REQUEST,
            json.dumps(payload, default=str).encode(),
        )
        logger.debug("Sent gate request %s for %s", request_id, capability)

        # For now, call the local decision engine directly (synchronous fallback).
        # In a production deployment with a remote gatekeeper, this would wait
        # on the decision subject with a subscription + timeout.
        from .minimal_shim import request_capability as _gate_cap

        result = _gate_cap(self._agent_id, capability, resource, {"profile": profile})
        return result

    async def _send_authorization(
        self,
        request_id: str,
        human_id: str,
    ) -> Dict[str, Any]:
        """Send a human authorization decision via NATS.

        A human operator (or automated approval service) calls this to
        authorize a pending ``propose_act``.
        """
        if self._nc is None:
            raise RuntimeError("NATSAgentProxy not connected")

        payload = {
            "request_id": request_id,
            "human_id": human_id,
        }
        await self._nc.publish(
            self.SUBJECT_DECISION,
            json.dumps(payload, default=str).encode(),
        )
        logger.info("Sent human authorization %s for request %s", human_id, request_id)

        from .minimal_shim import authorize_gate_request as _authorize

        return _authorize(request_id, human_id)

    # ---- Convenience ------------------------------------------------------

    async def authorize_as_human(
        self,
        request_id: str,
        human_id: str,
    ) -> Dict[str, Any]:
        """Convenience: send a human authorization decision.

        Wraps ``_send_authorization`` with the NATS transport.
        """
        return await self._send_authorization(request_id, human_id)

    @property
    def is_online(self) -> bool:
        return self._nc is not None and self._nc.is_connected
