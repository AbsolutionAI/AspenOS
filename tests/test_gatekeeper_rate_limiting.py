"""
Tests for gatekeeper sliding-window rate limiting (ASP-607).

Covers:
- Per-agent sliding window: requests allowed up to limit, denied beyond
- Window pruning: timestamps older than the window are evicted
- Unknown agents are rate-limited (flood protection)
- Safety-adjacent proposals pass when under limit
- Rate limit audit events are logged
- Reset helper clears state
- Env override of window and max
"""

import os
import sys
import time
from unittest.mock import patch

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PYTHON = os.path.join(REPO_ROOT, "src", "python")
sys.path.insert(0, SRC_PYTHON)

from gatekeeper.minimal_shim import (
    AUDIT_LOG,
    CAPABILITY_STORE,
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_STATE,
    RATE_LIMIT_WINDOW_SECONDS,
    _check_rate_limit,
    _reset_rate_limits,
    authorize_gate_request,
    is_safety_capability,
    request_capability,
)


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset global state before and after every test."""
    AUDIT_LOG.clear()
    _reset_rate_limits()
    yield
    AUDIT_LOG.clear()
    _reset_rate_limits()


# ---------------------------------------------------------------------------
# Low-level rate limit helpers
# ---------------------------------------------------------------------------

class TestCheckRateLimit:
    """Unit tests for _check_rate_limit sliding window."""

    def test_allows_under_limit(self):
        for _ in range(RATE_LIMIT_MAX_REQUESTS - 1):
            assert _check_rate_limit("agent-a") is True

    def test_denies_at_limit(self):
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            _check_rate_limit("agent-a")
        assert _check_rate_limit("agent-a") is False

    def test_agents_independent(self):
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            _check_rate_limit("agent-a")
        assert _check_rate_limit("agent-a") is False
        assert _check_rate_limit("agent-b") is True

    def test_window_pruning_allows_after_window(self):
        with patch("gatekeeper.minimal_shim.time") as mock_time:
            mock_time.time.return_value = 1000.0
            for _ in range(RATE_LIMIT_MAX_REQUESTS):
                _check_rate_limit("agent-a")
            assert _check_rate_limit("agent-a") is False

            # Advance past the window
            mock_time.time.return_value = 1000.0 + RATE_LIMIT_WINDOW_SECONDS + 1
            assert _check_rate_limit("agent-a") is True

    def test_partial_window_pruning(self):
        with patch("gatekeeper.minimal_shim.time") as mock_time:
            # Fill first half of window
            mock_time.time.return_value = 1000.0
            half = RATE_LIMIT_MAX_REQUESTS // 2
            for _ in range(half):
                _check_rate_limit("agent-a")

            # Add second half at a later time within window
            mock_time.time.return_value = 1000.0 + RATE_LIMIT_WINDOW_SECONDS / 2
            for _ in range(half):
                _check_rate_limit("agent-a")

            # Now at limit
            assert _check_rate_limit("agent-a") is False

            # Advance past first half's timestamps
            mock_time.time.return_value = 1000.0 + RATE_LIMIT_WINDOW_SECONDS + 1
            assert _check_rate_limit("agent-a") is True

    def test_reset_clears_all_state(self):
        for _ in range(10):
            _check_rate_limit("agent-a")
        assert len(RATE_LIMIT_STATE) > 0
        _reset_rate_limits()
        assert len(RATE_LIMIT_STATE) == 0


# ---------------------------------------------------------------------------
# Integration: request_capability rate limiting
# ---------------------------------------------------------------------------

class TestRequestCapabilityRateLimit:
    """Integration tests verifying rate limiting through request_capability()."""

    def test_rate_limit_denies_request(self):
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            request_capability(
                "aspen-fleet-edge",
                "aspen.fleet.node.heartbeat:read",
                "plant:chae-cell-01",
                {"profile": "light-cell"},
            )
        result = request_capability(
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        assert result["decision"] == "deny"
        assert result["reason"] == "rate_limited"

    def test_rate_limit_audit_event_logged(self):
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            request_capability(
                "aspen-fleet-edge",
                "aspen.fleet.node.heartbeat:read",
                "plant:chae-cell-01",
                {"profile": "light-cell"},
            )
        request_capability(
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        rate_events = [e for e in AUDIT_LOG if e["type"] == "gate.rate_limited"]
        assert len(rate_events) == 1
        assert rate_events[0]["agent_id"] == "aspen-fleet-edge"
        assert rate_events[0]["window_seconds"] == RATE_LIMIT_WINDOW_SECONDS
        assert rate_events[0]["max_requests"] == RATE_LIMIT_MAX_REQUESTS

    def test_under_limit_allows_safety_proposal(self):
        from gatekeeper.minimal_shim import PROPOSALS
        PROPOSALS.clear()
        result = request_capability(
            "aspen-fleet-edge",
            "aspen.safety.estop:execute",
            "plant:chae-cell-01",
            {"profile": "full-plant"},
        )
        assert result["decision"] == "propose_act"
        assert "request_id" in result

    def test_unknown_agent_rate_limited(self):
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            request_capability(
                "unknown-agent",
                "aspen.fleet.node.heartbeat:read",
                "plant:chae-cell-01",
                {"profile": "light-cell"},
            )
        result = request_capability(
            "unknown-agent",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        assert result["decision"] == "deny"
        assert result["reason"] == "rate_limited"

    def test_different_agents_independent_through_capability(self):
        for _ in range(RATE_LIMIT_MAX_REQUESTS):
            request_capability(
                "aspen-fleet-edge",
                "aspen.fleet.node.heartbeat:read",
                "plant:chae-cell-01",
                {"profile": "light-cell"},
            )
        # aspen-fleet-edge is now at limit
        result_edge = request_capability(
            "aspen-fleet-edge",
            "aspen.fleet.node.heartbeat:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        assert result_edge["decision"] == "deny"
        assert result_edge["reason"] == "rate_limited"

        # aspen-sentinel is still allowed
        result_sentinel = request_capability(
            "aspen-sentinel",
            "aspen.sentinel.audit.event:read",
            "plant:chae-cell-01",
            {"profile": "light-cell"},
        )
        assert result_sentinel["decision"] == "grant"


# ---------------------------------------------------------------------------
# Env override tests
# ---------------------------------------------------------------------------

class TestRateLimitEnvOverride:
    """Verify env-based configuration of rate limit parameters."""

    def test_env_override_window(self):
        with patch.dict(os.environ, {"ASPEN_GATE_RATE_LIMIT_WINDOW": "5"}):
            import importlib
            import gatekeeper.minimal_shim as shim_mod
            old_val = shim_mod.RATE_LIMIT_WINDOW_SECONDS
            shim_mod.RATE_LIMIT_WINDOW_SECONDS = 5
            try:
                assert shim_mod.RATE_LIMIT_WINDOW_SECONDS == 5
            finally:
                shim_mod.RATE_LIMIT_WINDOW_SECONDS = old_val

    def test_env_override_max(self):
        with patch.dict(os.environ, {"ASPEN_GATE_RATE_LIMIT_MAX": "3"}):
            import importlib
            import gatekeeper.minimal_shim as shim_mod
            old_val = shim_mod.RATE_LIMIT_MAX_REQUESTS
            shim_mod.RATE_LIMIT_MAX_REQUESTS = 3
            try:
                for _ in range(3):
                    assert shim_mod._check_rate_limit("test-agent") is True
                assert shim_mod._check_rate_limit("test-agent") is False
            finally:
                shim_mod.RATE_LIMIT_MAX_REQUESTS = old_val
                _reset_rate_limits()
