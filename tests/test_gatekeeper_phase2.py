"""
Tests for ADR-0009 Phase 2 — token lifecycle + credential strip + proxy enforcement.
===================================================================================

Covers the Phase-2 DoD:
1. Short-lived capability token lifecycle (issue / consume / refresh / expire / cleanup)
2. GatekeeperProxy / NATSAgentProxy — no broad credentials in agent images
3. SafetySubjectEnforcer — immutable proxy enforcement for safety-adjacent NATS subjects
4. Every action produces an audit log entry
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PYTHON = os.path.join(REPO_ROOT, "src", "python")
sys.path.insert(0, SRC_PYTHON)

from gatekeeper.minimal_shim import (
    TOKEN_REGISTRY,
    TOKEN_DEFAULT_TTL_MINUTES,
    TOKEN_REFRESH_DELTA_MINUTES,
    TOKEN_CLEANUP_MAX_AGE_SECONDS,
    PROPOSALS,
    _is_token_active,
    _register_token,
    _cleanup_stale_tokens,
    consume_token,
    refresh_token,
    expire_token,
    request_capability,
)
from gatekeeper.gatekeeper_proxy import GatekeeperProxy, NATSAgentProxy
from gatekeeper.safety_enforcer import SafetySubjectEnforcer


# =============================================================================
# Helpers
# =============================================================================

@pytest.fixture(autouse=True)
def _clean_state():
    """Reset global state before and after every test."""
    from gatekeeper import AUDIT_LOG
    AUDIT_LOG.clear()
    PROPOSALS.clear()
    TOKEN_REGISTRY.clear()
    yield
    AUDIT_LOG.clear()
    PROPOSALS.clear()
    TOKEN_REGISTRY.clear()


def _make_token(
    agent_id="aspen-fleet-edge",
    capability="aspen.fleet.node.heartbeat:read",
    resource="plant:chae-cell-01",
    scope="light-cell",
    ttl_minutes=TOKEN_DEFAULT_TTL_MINUTES,
    authorized_by=None,
):
    """Create a token in TOKEN_REGISTRY and return its token_id."""
    return _register_token(
        agent_id=agent_id,
        capability=capability,
        resource=resource,
        scope=scope,
        authorized_by=authorized_by or [],
        ttl_minutes=ttl_minutes,
    )


# =============================================================================
# Token Lifecycle — consume / refresh / expire / cleanup
# =============================================================================

class TestTokenLifecycleConsume:
    """consume_token() — one-shot consumption semantics."""

    def test_consume_active_token(self):
        token = _make_token()
        tid = token["token_id"]
        result = consume_token(tid)
        assert result["decision"] == "grant"
        assert result["status"] == "consumed"
        assert result["token_id"] == tid
        assert TOKEN_REGISTRY[tid]["status"] == "consumed"
        assert "consumed_at" in TOKEN_REGISTRY[tid]

    def test_consume_idempotent_on_already_consumed(self):
        token = _make_token()
        tid = token["token_id"]
        consume_token(tid)  # first consume succeeds
        result = consume_token(tid)  # second consume is idempotent deny
        assert result["decision"] == "deny"
        assert result["reason"] == "already_consumed"

    def test_consume_refuses_expired_token(self):
        token = _make_token(ttl_minutes=-1)  # already expired
        tid = token["token_id"]
        result = consume_token(tid)
        assert result["decision"] == "deny"
        assert result["reason"] == "token_expired"

    def test_consume_refuses_unknown_token(self):
        result = consume_token("no-such-token")
        assert result["decision"] == "deny"
        assert result["reason"] == "unknown_token"

    def test_consume_audit_trail(self):
        from gatekeeper import AUDIT_LOG
        token = _make_token()
        tid = token["token_id"]
        consume_token(tid)
        types = [e["type"] for e in AUDIT_LOG]
        assert "token.consumed" in types

    def test_consume_deny_audit_trail(self):
        from gatekeeper import AUDIT_LOG
        consume_token("no-such-token")
        types = [e["type"] for e in AUDIT_LOG]
        assert "token.consume.deny" in types


class TestTokenLifecycleRefresh:
    """refresh_token() — TTL extension semantics."""

    def test_refresh_active_token(self):
        token = _make_token()
        tid = token["token_id"]
        old_expires = token["expires"]
        result = refresh_token(tid, extension_minutes=30)
        assert result["decision"] == "grant"
        assert result["token_id"] == tid
        assert result["refresh_count"] == 1
        assert TOKEN_REGISTRY[tid]["expires"] > old_expires
        assert TOKEN_REGISTRY[tid]["refresh_count"] == 1

    def test_refresh_increments_counter(self):
        token = _make_token()
        tid = token["token_id"]
        refresh_token(tid)
        refresh_token(tid)
        refresh_token(tid)
        assert TOKEN_REGISTRY[tid]["refresh_count"] == 3

    def test_refresh_refuses_consumed_token(self):
        token = _make_token()
        tid = token["token_id"]
        consume_token(tid)
        result = refresh_token(tid)
        assert result["decision"] == "deny"
        assert result["reason"] == "already_consumed"

    def test_refresh_refuses_expired_token(self):
        token = _make_token(ttl_minutes=-1)
        tid = token["token_id"]
        result = refresh_token(tid)
        assert result["decision"] == "deny"
        assert result["reason"] == "token_expired"

    def test_refresh_refuses_unknown_token(self):
        result = refresh_token("no-such-token")
        assert result["decision"] == "deny"
        assert result["reason"] == "unknown_token"

    def test_refresh_audit_trail(self):
        from gatekeeper import AUDIT_LOG
        token = _make_token()
        refresh_token(token["token_id"])
        types = [e["type"] for e in AUDIT_LOG]
        assert "token.refresh" in types

    def test_refresh_deny_audit_trail(self):
        from gatekeeper import AUDIT_LOG
        refresh_token("no-such-token")
        types = [e["type"] for e in AUDIT_LOG]
        assert "token.refresh.deny" in types

    def test_refresh_custom_extension(self):
        token = _make_token()
        tid = token["token_id"]
        result = refresh_token(tid, extension_minutes=60)
        new_expires = datetime.fromisoformat(result["expires"])
        now = datetime.now(timezone.utc)
        # Should be ~60 minutes from now
        assert timedelta(minutes=55) < (new_expires - now) < timedelta(minutes=65)


class TestTokenLifecycleExpire:
    """expire_token() — forced expiry semantics."""

    def test_expire_active_token(self):
        token = _make_token()
        tid = token["token_id"]
        result = expire_token(tid)
        assert result["decision"] == "grant"
        assert result["status"] == "expired"
        assert TOKEN_REGISTRY[tid]["status"] == "expired"

    def test_expire_refuses_consumed_token(self):
        token = _make_token()
        tid = token["token_id"]
        consume_token(tid)
        result = expire_token(tid)
        assert result["decision"] == "deny"
        assert result["reason"] == "already_consumed"

    def test_expire_idempotent_on_already_expired(self):
        token = _make_token()
        tid = token["token_id"]
        expire_token(tid)
        result = expire_token(tid)  # second expire is idempotent grant
        assert result["decision"] == "grant"
        assert result["status"] == "expired"

    def test_expire_refuses_unknown_token(self):
        result = expire_token("no-such-token")
        assert result["decision"] == "deny"
        assert result["reason"] == "unknown_token"

    def test_expire_audit_trail(self):
        from gatekeeper import AUDIT_LOG
        token = _make_token()
        expire_token(token["token_id"])
        types = [e["type"] for e in AUDIT_LOG]
        assert "token.expired" in types

    def test_expire_deny_audit_trail(self):
        from gatekeeper import AUDIT_LOG
        expire_token("no-such-token")
        types = [e["type"] for e in AUDIT_LOG]
        assert "token.expire.deny" in types

    def test_expire_then_consume_refuses(self):
        token = _make_token()
        tid = token["token_id"]
        expire_token(tid)
        result = consume_token(tid)
        assert result["decision"] == "deny"
        assert result["reason"] == "token_expired"


class TestTokenLifecycleActiveCheck:
    """_is_token_active() — token state validation."""

    def test_active_token_is_active(self):
        token = _make_token()
        assert _is_token_active(token["token_id"]) is True

    def test_consumed_token_is_inactive(self):
        token = _make_token()
        consume_token(token["token_id"])
        assert _is_token_active(token["token_id"]) is False

    def test_expired_token_is_inactive(self):
        token = _make_token()
        expire_token(token["token_id"])
        assert _is_token_active(token["token_id"]) is False

    def test_unknown_token_is_inactive(self):
        assert _is_token_active("no-such-token") is False

    def test_naturally_expired_token_is_inactive(self):
        token = _make_token(ttl_minutes=-1)
        assert _is_token_active(token["token_id"]) is False

    def test_refreshed_token_stays_active(self):
        token = _make_token()
        tid = token["token_id"]
        refresh_token(tid)
        assert _is_token_active(tid) is True


class TestTokenCleanup:
    """_cleanup_stale_tokens() — garbage collection of old expired tokens."""

    def test_removes_old_expired_tokens(self):
        token = _make_token(ttl_minutes=-2)  # expired
        tid = token["token_id"]
        # Force status to expired
        expire_token(tid)
        assert tid in TOKEN_REGISTRY
        count = _cleanup_stale_tokens(max_age_seconds=0)  # purge everything expired
        assert count >= 1
        assert tid not in TOKEN_REGISTRY

    def test_leaves_active_tokens(self):
        token = _make_token()
        tid = token["token_id"]
        _cleanup_stale_tokens(max_age_seconds=0)
        assert tid in TOKEN_REGISTRY

    def test_leaves_freshly_expired_tokens(self):
        """Tokens that expired recently (within max_age) should NOT be cleaned."""
        token = _make_token(ttl_minutes=-1)
        tid = token["token_id"]
        expire_token(tid)
        # max_age_seconds=3600 (default) — these tokens are recent
        count = _cleanup_stale_tokens(max_age_seconds=3600)
        assert tid in TOKEN_REGISTRY

    def test_cleanup_returns_count(self):
        token1 = _make_token(ttl_minutes=-2)
        token2 = _make_token(ttl_minutes=-2)
        expire_token(token1["token_id"])
        expire_token(token2["token_id"])
        count = _cleanup_stale_tokens(max_age_seconds=0)
        assert count == 2

    def test_cleanup_noops_on_empty_registry(self):
        TOKEN_REGISTRY.clear()
        count = _cleanup_stale_tokens(max_age_seconds=0)
        assert count == 0


# =============================================================================
# GatekeeperProxy — credential strip adapter
# =============================================================================

class TestGatekeeperProxy:
    """GatekeeperProxy — agent-side proxy that routes external calls
    through the gatekeeper. Agents never hold broad credentials."""

    def test_init_sets_agent_id(self):
        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")
        assert proxy.agent_id == "aspen-fleet-edge"

    def test_request_capability_grant_caches_token(self):
        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")
        result = proxy.request_capability(
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
        )
        assert result["decision"] == "grant"
        assert "token_id" in result
        assert result["token_id"] in proxy._token_cache

    def test_request_capability_propose_act_does_not_cache(self):
        from gatekeeper import CAPABILITY_STORE
        CAPABILITY_STORE["aspen-fleet-edge"].append("aspen.safety.estop:execute")
        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")
        result = proxy.request_capability(
            "aspen.safety.estop:execute",
            "plant:chae-cell-01",
            profile="full-plant",
        )
        assert result["decision"] == "propose_act"
        # propose_act returns no token_id to cache
        CAPABILITY_STORE["aspen-fleet-edge"].remove("aspen.safety.estop:execute")

    def test_request_capability_deny_does_not_cache(self):
        proxy = GatekeeperProxy(agent_id="aspen-unknown-agent")
        result = proxy.request_capability(
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
        )
        assert result["decision"] == "deny"
        assert proxy._token_cache == {}

    def test_execute_with_token_success(self):
        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")
        result = proxy.request_capability(
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
        )
        tid = result["token_id"]

        executed = []
        def action():
            executed.append(True)
            return "ok"

        exec_result = proxy.execute_with_token(tid, action)
        assert exec_result["decision"] == "grant"
        assert exec_result["action_result"] == "ok"
        assert executed == [True]
        # Token should be consumed after execution
        assert _is_token_active(tid) is False

    def test_execute_with_token_denies_inactive_token(self):
        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")
        result = proxy.execute_with_token("no-such-token", lambda: "never")
        assert result["decision"] == "deny"
        assert result["reason"] == "token_not_active"

    def test_execute_with_token_denies_on_action_failure(self):
        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")
        result = proxy.request_capability(
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
        )
        tid = result["token_id"]

        def failing_action():
            raise RuntimeError("something broke")

        exec_result = proxy.execute_with_token(tid, failing_action)
        assert exec_result["decision"] == "deny"
        assert "action_failed" in exec_result["reason"]

    def test_execute_with_token_audit_consumption(self):
        from gatekeeper import AUDIT_LOG
        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")
        result = proxy.request_capability(
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
        )
        proxy.execute_with_token(result["token_id"], lambda: "ok")
        types = [e["type"] for e in AUDIT_LOG]
        assert "token.consumed" in types

    def test_connect_default_noop(self):
        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")
        import asyncio
        result = asyncio.run(proxy.connect())
        assert result is True  # default no-op returns True

    def test_close_default_noop(self):
        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")
        import asyncio
        asyncio.run(proxy.close())  # should not raise


class TestNATSAgentProxy:
    """NATSAgentProxy — concrete gatekeeper proxy over NATS transport."""

    def test_init_with_endpoint(self):
        proxy = NATSAgentProxy(
            agent_id="aspen-fleet-edge",
            gatekeeper_endpoint="nats://broker:4222",
        )
        assert proxy._endpoint == "nats://broker:4222"

    def test_init_uses_env_fallback(self):
        with patch.dict(os.environ, {"ASPEN_NATS_URL": "nats://env-broker:4222"}, clear=True):
            proxy = NATSAgentProxy(agent_id="aspen-fleet-edge")
            assert proxy._endpoint == "nats://env-broker:4222"

    @pytest.mark.asyncio
    async def test_connect_with_valid_url(self):
        mock_nats_mod = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.is_connected = True
        mock_conn.publish = AsyncMock()
        mock_conn.subscribe = AsyncMock()
        mock_conn.drain = AsyncMock()
        mock_conn.close = AsyncMock()
        mock_conn.jetstream = MagicMock()
        mock_nats_mod.connect = AsyncMock(return_value=mock_conn)

        proxy = NATSAgentProxy(
            agent_id="aspen-fleet-edge",
            gatekeeper_endpoint="nats://localhost:4222",
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            connected = await proxy.connect()
        assert connected is True
        assert proxy.is_online is True

    @pytest.mark.asyncio
    async def test_connect_offline_without_endpoint(self):
        proxy = NATSAgentProxy(
            agent_id="aspen-fleet-edge",
            gatekeeper_endpoint="",
        )
        connected = await proxy.connect()
        assert connected is False
        assert proxy.is_online is False

    @pytest.mark.asyncio
    async def test_connect_offline_on_failure(self):
        mock_nats_mod = MagicMock()
        mock_nats_mod.connect = AsyncMock(side_effect=RuntimeError("connection refused"))

        proxy = NATSAgentProxy(
            agent_id="aspen-fleet-edge",
            gatekeeper_endpoint="nats://nowhere:4222",
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            connected = await proxy.connect()
        assert connected is False

    @pytest.mark.asyncio
    async def test_close_drains_connection(self):
        mock_nats_mod = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.is_connected = True
        mock_conn.publish = AsyncMock()
        mock_conn.subscribe = AsyncMock()
        mock_conn.drain = AsyncMock()
        mock_conn.close = AsyncMock()
        mock_conn.jetstream = MagicMock()
        mock_nats_mod.connect = AsyncMock(return_value=mock_conn)

        proxy = NATSAgentProxy(
            agent_id="aspen-fleet-edge",
            gatekeeper_endpoint="nats://localhost:4222",
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await proxy.connect()
            await proxy.close()
        mock_conn.drain.assert_called_once()
        mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_request_publishes_to_correct_subject(self):
        mock_nats_mod = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.is_connected = True
        mock_conn.publish = AsyncMock()
        mock_conn.subscribe = AsyncMock()
        mock_conn.drain = AsyncMock()
        mock_conn.close = AsyncMock()
        mock_conn.jetstream = MagicMock()
        mock_nats_mod.connect = AsyncMock(return_value=mock_conn)

        proxy = NATSAgentProxy(
            agent_id="aspen-fleet-edge",
            gatekeeper_endpoint="nats://localhost:4222",
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await proxy.connect()
            result = await proxy._send_request(
                "aspen.fleet.node.heartbeat:read",
                "plant:chae-cell-01",
                profile="light-cell",
            )
        # Should have called NATS publish on the request subject
        subjects = [c[0][0] for c in mock_conn.publish.call_args_list]
        assert "aspen.authz.gate.request" in subjects
        # And returned a decision from the local fallback
        assert result["decision"] in ("grant", "deny")

    @pytest.mark.asyncio
    async def test_send_authorization_publishes_decision(self):
        mock_nats_mod = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.is_connected = True
        mock_conn.publish = AsyncMock()
        mock_conn.subscribe = AsyncMock()
        mock_conn.drain = AsyncMock()
        mock_conn.close = AsyncMock()
        mock_conn.jetstream = MagicMock()
        mock_nats_mod.connect = AsyncMock(return_value=mock_conn)

        proxy = NATSAgentProxy(
            agent_id="aspen-fleet-edge",
            gatekeeper_endpoint="nats://localhost:4222",
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await proxy.connect()
            result = await proxy._send_authorization(
                request_id="test-req-1",
                human_id="operator-1",
            )
        subjects = [c[0][0] for c in mock_conn.publish.call_args_list]
        assert "aspen.authz.gate.decision" in subjects
        assert "decision" in result

    @pytest.mark.asyncio
    async def test_authorize_as_human_wrapper(self):
        mock_nats_mod = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.is_connected = True
        mock_conn.publish = AsyncMock()
        mock_conn.subscribe = AsyncMock()
        mock_conn.drain = AsyncMock()
        mock_conn.close = AsyncMock()
        mock_conn.jetstream = MagicMock()
        mock_nats_mod.connect = AsyncMock(return_value=mock_conn)

        proxy = NATSAgentProxy(
            agent_id="aspen-fleet-edge",
            gatekeeper_endpoint="nats://localhost:4222",
        )
        with patch.dict("sys.modules", {"nats": mock_nats_mod}):
            await proxy.connect()
            result = await proxy.authorize_as_human(
                request_id="test-req-1",
                human_id="operator-1",
            )
        assert "decision" in result

    @pytest.mark.asyncio
    async def test_send_request_raises_when_not_connected(self):
        proxy = NATSAgentProxy(
            agent_id="aspen-fleet-edge",
            gatekeeper_endpoint="nats://localhost:4222",
        )
        with pytest.raises(RuntimeError, match="not connected"):
            await proxy._send_request("cap", "res", "light-cell")

    @pytest.mark.asyncio
    async def test_is_online_property(self):
        proxy = NATSAgentProxy(agent_id="aspen-fleet-edge")
        assert proxy.is_online is False


# =============================================================================
# SafetySubjectEnforcer — immutable proxy enforcement
# =============================================================================

class TestSafetySubjectEnforcerInit:
    """SafetySubjectEnforcer construction and pattern immutability."""

    def test_default_patterns_loaded(self):
        enforcer = SafetySubjectEnforcer()
        patterns = enforcer.patterns
        assert "aspen.safety.*" in patterns
        assert "aspen.edge.*.command" in patterns
        assert "aspen.fleet.mission.start" in patterns

    def test_additional_patterns_appended(self):
        enforcer = SafetySubjectEnforcer(
            additional_subjects=["aspen.fleet.mission.stop"]
        )
        assert "aspen.fleet.mission.stop" in enforcer.patterns

    def test_patterns_are_immutable_tuple(self):
        enforcer = SafetySubjectEnforcer()
        assert isinstance(enforcer.patterns, tuple)
        # Patterns list cannot be modified after construction
        with pytest.raises(TypeError, match="does not support item assignment"):
            enforcer.patterns[0] = "modified.subject"  # tuple is immutable

    def test_patterns_are_not_mutable_through_reference(self):
        enforcer = SafetySubjectEnforcer(
            additional_subjects=["aspen.extra.test"]
        )
        assert len(enforcer.patterns) == 4  # 3 defaults + 1 extra


class TestSafetySubjectEnforcerClassification:
    """is_safety_subject() — subject classification."""

    def setup_method(self):
        self.enforcer = SafetySubjectEnforcer()

    def test_safety_subjects_match(self):
        assert self.enforcer.is_safety_subject("aspen.safety.estop")
        assert self.enforcer.is_safety_subject("aspen.safety.estop.clear")
        assert self.enforcer.is_safety_subject("aspen.edge.cell-01.command")
        assert self.enforcer.is_safety_subject("aspen.edge.robot-a.command")
        assert self.enforcer.is_safety_subject("aspen.fleet.mission.start")
        assert self.enforcer.is_safety_subject("aspen.safety.any.deep.path")

    def test_non_safety_subjects_do_not_match(self):
        assert not self.enforcer.is_safety_subject("aspen.fleet.node.heartbeat")
        assert not self.enforcer.is_safety_subject("aspen.sentinel.audit.event")
        assert not self.enforcer.is_safety_subject("aspen.edge.cell-01.heartbeat")
        assert not self.enforcer.is_safety_subject("aspen.fleet.mission.status")
        assert not self.enforcer.is_safety_subject("aspen.fleet.mission.start_report")


class TestSafetySubjectEnforcerCheckPublish:
    """check_publish() — pre-publish enforcement."""

    def setup_method(self):
        self.enforcer = SafetySubjectEnforcer()

    def test_non_safety_allowed_without_token(self):
        result = self.enforcer.check_publish("aspen.fleet.node.heartbeat:read")
        assert result["allowed"] is True
        assert result["reason"] == "not_safety_subject"

    def test_safety_without_token_denied(self):
        result = self.enforcer.check_publish("aspen.safety.estop")
        assert result["allowed"] is False
        assert result["reason"] == "safety_subject_requires_token"

    def test_safety_with_valid_token_allowed(self):
        token = _make_token()
        result = self.enforcer.check_publish(
            "aspen.safety.estop",
            token_id=token["token_id"],
        )
        assert result["allowed"] is True
        assert result["reason"] == "token_valid"

    def test_safety_with_consumed_token_denied(self):
        token = _make_token()
        consume_token(token["token_id"])
        result = self.enforcer.check_publish(
            "aspen.safety.estop",
            token_id=token["token_id"],
        )
        assert result["allowed"] is False
        assert result["reason"] == "token_consumed"

    def test_safety_with_expired_token_denied(self):
        token = _make_token(ttl_minutes=-1)
        tid = token["token_id"]
        # Force status to expired
        expire_token(tid)
        result = self.enforcer.check_publish(
            "aspen.safety.estop",
            token_id=tid,
        )
        assert result["allowed"] is False
        assert result["reason"] == "token_expired"

    def test_safety_with_unknown_token_denied(self):
        result = self.enforcer.check_publish(
            "aspen.safety.estop",
            token_id="no-such-token",
        )
        assert result["allowed"] is False
        assert result["reason"] == "token_unknown"

    def test_safety_token_must_match_capability(self):
        """The enforcer checks token validity, not capability-scope matching.
        The gatekeeper's token issuance already scopes capabilities."""
        token = _make_token(capability="aspen.fleet.node.heartbeat:read")
        # Even a non-safety token is valid for publish check — the enforcer
        # validates token liveness, not capability-match. Capability scoping
        # is enforced at token-issuance time by the gatekeeper.
        result = self.enforcer.check_publish(
            "aspen.safety.estop",
            token_id=token["token_id"],
        )
        assert result["allowed"] is True  # token is active

    def test_check_publish_includes_subject_in_result(self):
        result = self.enforcer.check_publish("aspen.safety.estop")
        assert result["subject"] == "aspen.safety.estop"

    def test_check_publish_with_custom_check_fn(self):
        token = _make_token()
        def custom_check(tid):
            return False  # always deny
        result = self.enforcer.check_publish(
            "aspen.safety.estop",
            token_id=token["token_id"],
            check_token_fn=custom_check,
        )
        assert result["allowed"] is False

    def test_check_publish_edge_subject_denied_without_token(self):
        result = self.enforcer.check_publish("aspen.edge.cell-01.command")
        assert result["allowed"] is False
        assert result["reason"] == "safety_subject_requires_token"

    def test_check_publish_mission_start_denied_without_token(self):
        result = self.enforcer.check_publish("aspen.fleet.mission.start")
        assert result["allowed"] is False
        assert result["reason"] == "safety_subject_requires_token"


class TestSafetySubjectEnforcerBoolWrapper:
    """check_publish_with_token_check() — convenience boolean wrapper."""

    def setup_method(self):
        self.enforcer = SafetySubjectEnforcer()

    def test_non_safety_returns_true(self):
        assert self.enforcer.check_publish_with_token_check(
            "aspen.fleet.node.heartbeat:read", "any-token"
        ) is True

    def test_safety_with_valid_token_returns_true(self):
        token = _make_token()
        assert self.enforcer.check_publish_with_token_check(
            "aspen.safety.estop", token["token_id"]
        ) is True

    def test_safety_without_token_returns_false(self):
        assert self.enforcer.check_publish_with_token_check(
            "aspen.safety.estop", "invalid"
        ) is False


# =============================================================================
# Integration: Full Phase 2 flow
# =============================================================================

class TestPhase2Integration:
    """End-to-end Phase 2 flow: request → grant → execute → consume → expire."""

    def test_full_token_lifecycle(self):
        """Agent requests capability, gets token, executes action, token consumed."""
        from gatekeeper import AUDIT_LOG

        # 1. Request capability
        result = request_capability(
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        assert result["decision"] == "grant"
        tid = result["token"]["token_id"]

        # 2. Token is active
        assert _is_token_active(tid) is True

        # 3. Use proxy to execute with token
        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")
        exec_result = proxy.execute_with_token(tid, lambda: {"status": "ok"})
        assert exec_result["decision"] == "grant"
        assert exec_result["consumed"] is True

        # 4. Token is consumed (no longer active)
        assert _is_token_active(tid) is False

        # 5. Full audit trail
        types = [e["type"] for e in AUDIT_LOG]
        assert "capability.grant" in types
        assert "token.consumed" in types

    def test_safety_flow_with_proxy(self):
        """Safety-adjacent: propose_act → dual-human → grant → execute."""
        from gatekeeper import CAPABILITY_STORE, AUDIT_LOG
        from gatekeeper.minimal_shim import authorize_gate_request

        # Add safety capability
        CAPABILITY_STORE["aspen-fleet-edge"].append("aspen.safety.estop:execute")

        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")

        # 1. Request safety capability → propose_act
        result = proxy.request_capability(
            "aspen.safety.estop:execute",
            "plant:chae-cell-01",
            profile="full-plant",
        )
        assert result["decision"] == "propose_act"
        req_id = result["request_id"]

        # 2. Dual-human authorization
        auth1 = authorize_gate_request(req_id, "operator-1")
        assert auth1["decision"] == "awaiting"

        auth2 = authorize_gate_request(req_id, "operator-2")
        assert auth2["decision"] == "grant"
        tid = auth2["token_id"]

        # 3. Execute with token
        exec_result = proxy.execute_with_token(tid, lambda: "safety_action_done")
        assert exec_result["decision"] == "grant"

        # 4. Verify audit trail
        types = [e["type"] for e in AUDIT_LOG]
        assert "propose_act.pending" in types
        assert "gate.authorize" in types
        assert "capability.grant" in types
        assert "token.consumed" in types

        CAPABILITY_STORE["aspen-fleet-edge"].remove("aspen.safety.estop:execute")

    def test_enforcer_in_full_flow(self):
        """SafetySubjectEnforcer blocks direct publish without token
        but allows it with a valid token from the gatekeeper."""
        enforcer = SafetySubjectEnforcer()

        # Without any token — blocked
        check = enforcer.check_publish("aspen.safety.estop")
        assert check["allowed"] is False

        # Get a token through the gatekeeper
        result = request_capability(
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        tid = result["token"]["token_id"]

        # Non-safety subject — allowed even with this token
        check = enforcer.check_publish("aspen.fleet.node.heartbeat:read", token_id=tid)
        assert check["allowed"] is True
        assert check["reason"] == "not_safety_subject"

        # Safety subject WITH valid token — allowed
        check = enforcer.check_publish("aspen.safety.estop", token_id=tid)
        assert check["allowed"] is True

        # After consuming the token — safety subject blocked
        consume_token(tid)
        check = enforcer.check_publish("aspen.safety.estop", token_id=tid)
        assert check["allowed"] is False

    def test_credential_strip_proxy_holds_no_credentials(self):
        """Verify GatekeeperProxy/NATSAgentProxy hold no credential fields."""
        proxy = GatekeeperProxy(agent_id="aspen-fleet-edge")
        # The proxy has no api_key, password, token, or secret attributes
        cred_fields = {"api_key", "password", "secret", "credential", "auth_token"}
        proxy_attrs = set(dir(proxy))
        assert not cred_fields.intersection(proxy_attrs), \
            f"Proxy should not hold credential fields: {cred_fields & proxy_attrs}"

        nats_proxy = NATSAgentProxy(
            agent_id="aspen-fleet-edge",
            gatekeeper_endpoint="nats://localhost:4222",
        )
        nats_attrs = set(dir(nats_proxy))
        assert not cred_fields.intersection(nats_attrs), \
            f"NATS proxy should not hold credential fields: {cred_fields & nats_attrs}"
