#!/usr/bin/env python3
"""
NATS client wrapper for the ADR-0009 Gatekeeper.

Wires the minimal shim to NATS subjects:
  * aspen.authz.gate.request     — subscribe (inbound capability requests)
  * aspen.authz.gate.decision    — publish  (decision responses)
  * aspen.authz.capability.grant — publish  (granted tokens)
  * aspen.sentinel.audit.event   — publish  (audit trail)

Offline-capable: when no NATS broker is reachable, events buffer locally
and the shim's in-memory AUDIT_LOG remains the write-path. The NATS path
is best-effort; no agent credential is ever embedded in the codebase.

Usage:
    client = NATSGateClient("nats://localhost:4222")
    await client.connect()
    await client.publish_audit({"type": "capability.grant", ...})
    await client.publish_decision(request_id, "grant", ...)
    await client.publish_grant(agent_id, caps, scope)
    # subscribe() sets up gate.request listener that calls your handler
    await client.close()
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("gatekeeper.nats")


# ---------------------------------------------------------------------------
# Offline local buffer — used when no NATS broker is reachable
# ---------------------------------------------------------------------------
_OFFLINE_BUFFER: list[Dict[str, Any]] = []


def _flush_offline_buffer(client: "NATSGateClient") -> None:
    """Best-effort flush of buffered events once NATS reconnects."""
    if not client._nc or not client._nc.is_connected:
        return
    while _OFFLINE_BUFFER:
        event = _OFFLINE_BUFFER.pop(0)
        try:
            subject = client._resolve_audit_subject(event)
            asyncio.ensure_future(client._nc.publish(subject, json.dumps(event).encode()))
        except Exception:
            _OFFLINE_BUFFER.insert(0, event)
            break


# ---------------------------------------------------------------------------
# NATS Gate Client
# ---------------------------------------------------------------------------

class NATSGateClient:
    """Thin NATS client for the gatekeeper's ADR-0009 subjects.

    Connects to a NATS broker and exposes typed publish helpers.
    If the broker is unavailable the class operates in *offline mode*:
    every publish call writes to an in-memory buffer instead.
    """

    SUBJECT_REQUEST = "aspen.authz.gate.request"
    SUBJECT_DECISION = "aspen.authz.gate.decision"
    SUBJECT_GRANT = "aspen.authz.capability.grant"
    SUBJECT_AUDIT = "aspen.sentinel.audit.event"

    def __init__(
        self,
        nats_url: Optional[str] = None,
        offline_fallback: bool = True,
        request_handler: Optional[Callable] = None,
    ):
        """
        Args:
            nats_url: NATS broker URL (e.g. "nats://localhost:4222").
                      If None/empty, the client starts in offline mode.
            offline_fallback: If True, buffers events locally when broker
                              unreachable (default: True).
            request_handler: Async callable(request_data: dict) -> dict
                             invoked when a message arrives on
                             aspen.authz.gate.request. The return dict is
                             published to aspen.authz.gate.decision.
        """
        self._nats_url = nats_url or os.environ.get("ASPEN_NATS_URL", "")
        self._offline_fallback = offline_fallback
        self._request_handler = request_handler
        self._nc: Any = None  # nats.aio.client.Client or None
        self._js: Any = None  # JetStream context (optional)
        self._sub: Any = None  # subscription handle
        self._connected = False

    # ---- lifecycle -------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to the NATS broker. Returns True if connected, False for offline mode."""
        if not self._nats_url:
            logger.info("No NATS URL configured — running in offline mode")
            self._connected = False
            return False

        try:
            import nats

            # Disable default signal handler — we manage our own lifecycle
            self._nc = await nats.connect(
                self._nats_url,
                max_reconnect_attempts=3,
                reconnect_time_wait=2,
                name="aspen-gatekeeper",
                ping_interval=20,
                max_outstanding_pings=5,
                # Don't install signal handlers; let asyncio manage shutdown
                # NATS 2.15+ uses error_cb/disconnected_cb/reconnected_cb
            )
            self._connected = True
            logger.info("Connected to NATS broker at %s", self._nats_url)

            # Optional JetStream context for durable audit storage
            self._js = self._nc.jetstream()

            # Flush any events queued during offline period
            _flush_offline_buffer(self)

            # Subscribe to gate.request if a handler was provided
            if self._request_handler is not None:
                await self._subscribe_gate_requests()

            return True

        except Exception as exc:
            logger.warning("NATS connection failed (%s) — offline mode", exc)
            self._connected = False
            # Reconnect is handled by the NATS client internally;
            # we just operate in fire-and-forget mode until reconnected.
            return False

    async def close(self) -> None:
        """Drain and close the NATS connection."""
        if self._sub:
            try:
                await self._sub.unsubscribe()
            except Exception:
                pass
            self._sub = None
        if self._nc:
            try:
                await self._nc.drain()
                await self._nc.close()
            except Exception:
                pass
            self._nc = None
        self._connected = False

    @property
    def is_online(self) -> bool:
        return self._connected and self._nc is not None and self._nc.is_connected

    # ---- publish helpers -------------------------------------------------

    async def publish_audit(self, event: Dict[str, Any]) -> None:
        """Publish an audit event to aspen.sentinel.audit.event.

        Falls back to the local buffer if offline.
        """
        # Ensure timestamp
        if "ts" not in event:
            event["ts"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        payload = json.dumps(event, default=str).encode()

        if self.is_online:
            try:
                await self._nc.publish(self.SUBJECT_AUDIT, payload)
                logger.debug("Published audit event: %s", event.get("type", "unknown"))
            except Exception as exc:
                logger.warning("NATS publish failed for audit event: %s", exc)
                if self._offline_fallback:
                    _OFFLINE_BUFFER.append(event)
        else:
            if self._offline_fallback:
                _OFFLINE_BUFFER.append(event)

    async def publish_decision(
        self,
        request_id: str,
        decision: str,
        *,
        humans: Optional[list[str]] = None,
        note: Optional[str] = None,
        **extra,
    ) -> None:
        """Publish a gate decision to aspen.authz.gate.decision."""
        payload: Dict[str, Any] = {
            "request_id": request_id,
            "decision": decision,
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        if humans:
            payload["humans"] = humans
        if note:
            payload["note"] = note
        payload.update(extra)

        data = json.dumps(payload, default=str).encode()

        if self.is_online:
            try:
                await self._nc.publish(self.SUBJECT_DECISION, data)
                logger.info("Published decision %s for request %s", decision, request_id)
            except Exception as exc:
                logger.warning("NATS publish failed for decision: %s", exc)
                if self._offline_fallback:
                    _OFFLINE_BUFFER.append(payload)
        elif self._offline_fallback:
            _OFFLINE_BUFFER.append(payload)

    async def publish_grant(
        self,
        agent_id: str,
        caps: list[str],
        *,
        expires: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> None:
        """Publish a capability grant to aspen.authz.capability.grant."""
        payload: Dict[str, Any] = {
            "agent_id": agent_id,
            "caps": caps,
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        if expires:
            payload["expires"] = expires
        if scope:
            payload["scope"] = scope

        data = json.dumps(payload, default=str).encode()

        if self.is_online:
            try:
                await self._nc.publish(self.SUBJECT_GRANT, data)
                logger.info("Published grant for %s (%d caps)", agent_id, len(caps))
            except Exception as exc:
                logger.warning("NATS publish failed for grant: %s", exc)
                if self._offline_fallback:
                    _OFFLINE_BUFFER.append(payload)
        elif self._offline_fallback:
            _OFFLINE_BUFFER.append(payload)

    # ---- subscription ----------------------------------------------------

    async def _subscribe_gate_requests(self) -> None:
        """Subscribe to aspen.authz.gate.request and invoke the handler."""
        if not self._nc or not self._request_handler:
            return

        import nats

        async def _on_request(msg):
            try:
                data = json.loads(msg.data.decode())
                logger.debug("Received gate request: %s", data.get("capability", "unknown"))
                result = await self._request_handler(data)
                # Publish the handler's result as a decision
                await self.publish_decision(
                    request_id=result.get("request_id", data.get("request_id", "unknown")),
                    decision=result.get("decision", "deny"),
                    **{k: v for k, v in result.items() if k not in ("decision", "request_id")},
                )
            except Exception as exc:
                logger.error("Error handling gate request: %s", exc)

        self._sub = await self._nc.subscribe(self.SUBJECT_REQUEST, cb=_on_request)
        logger.info("Subscribed to %s", self.SUBJECT_REQUEST)

    # ---- helpers ---------------------------------------------------------

    @staticmethod
    def _resolve_audit_subject(event: Dict[str, Any]) -> str:
        """Return the NATS subject for a given audit event type."""
        etype = event.get("type", "")
        if "grant" in etype:
            return "aspen.authz.capability.grant"
        if "deny" in etype or "decision" in etype:
            return "aspen.authz.gate.decision"
        return "aspen.sentinel.audit.event"

    @property
    def offline_buffer_size(self) -> int:
        return len(_OFFLINE_BUFFER)

    async def drain_offline_buffer(self) -> int:
        """Attempt to flush locally buffered events to NATS.

        Returns the count of events that were successfully published.
        """
        if not self.is_online:
            return 0
        count = 0
        while _OFFLINE_BUFFER:
            event = _OFFLINE_BUFFER.pop(0)
            try:
                subject = self._resolve_audit_subject(event)
                await self._nc.publish(subject, json.dumps(event, default=str).encode())
                count += 1
            except Exception:
                _OFFLINE_BUFFER.insert(0, event)
                break
        return count


# ---------------------------------------------------------------------------
# Convenience: run standalone to test connectivity
# ---------------------------------------------------------------------------
if __name__ == "__main__":

    async def _demo():
        logging.basicConfig(level=logging.INFO)

        client = NATSGateClient(
            nats_url=os.environ.get("ASPEN_NATS_URL", "nats://localhost:4222"),
            offline_fallback=True,
        )
        connected = await client.connect()
        print(f"Connected: {connected}")
        print(f"Online: {client.is_online}")

        # Publish a test audit event
        await client.publish_audit({
            "type": "gatekeeper.test",
            "message": "NATSGateClient connectivity check",
        })
        print(f"Offline buffer size: {client.offline_buffer_size}")

        await client.close()
        print("Done.")

    asyncio.run(_demo())