#!/usr/bin/env python3
"""
SafetySubjectEnforcer — immutable proxy for safety-adjacent NATS subjects
===========================================================================

ADR-0009 Phase 2: enforces that safety-adjacent NATS subjects can only be
published through the gatekeeper authorization flow. Direct publishes to
safety subjects without a valid gatekeeper capability token are denied.

The enforcer sits as a NATS interceptor (or agent-side mixin) that validates
every publish against the gatekeeper's TOKEN_REGISTRY. Only token-authorized
messages pass through.

Usage:
    from gatekeeper.safety_enforcer import SafetySubjectEnforcer

    enforcer = SafetySubjectEnforcer()
    enforcer.add_safety_subject("aspen.safety.estop")

    # Before publishing, check:
    if enforcer.check_publish("aspen.safety.estop", token_id):
        # Publish is allowed
    else:
        # Publish is blocked — must go through gatekeeper
        result = request_capability(...)
        # Use token from result

Design:
- The enforcer does NOT intercept NATS directly (that would require a NATS
  middleware plugin). Instead, it provides a **check function** that agents
  and the gatekeeper call before publishing to safety subjects.
- The gatekeeper itself is the only component that can authorize a publish
  to a safety subject, via its token issuance.
- Immutable: once the list of safety subjects and the enforcer's rules are
  configured, they cannot be changed at runtime without reinitialization.
"""

import logging
from typing import Dict, List, Optional

from .minimal_shim import (
    SAFETY_SUBJECTS,
    TOKEN_REGISTRY,
    _is_token_active,
    _subject_match,
)

logger = logging.getLogger("gatekeeper.enforcer")


class SafetySubjectEnforcer:
    """Immutable proxy enforcement for safety-adjacent NATS subjects.

    Validates that publishes to safety subjects carry a valid gatekeeper
    capability token. The enforcer NEVER allows a direct publish to a safety
    subject without token authorization.

    Subjects are compiled from the gatekeeper's ``SAFETY_SUBJECTS`` list
    (``aspen.safety.*``, ``aspen.edge.*.command``, ``aspen.fleet.mission.start``)
    plus any additional patterns passed at construction time.
    """

    def __init__(
        self,
        additional_subjects: Optional[List[str]] = None,
    ) -> None:
        """Initialize the enforcer with the gatekeeper's safety subjects.

        Args:
            additional_subjects: Optional list of extra subject patterns to
                enforce (e.g., ``["aspen.fleet.mission.stop"]``).
        """
        self._patterns = list(SAFETY_SUBJECTS)
        if additional_subjects:
            self._patterns.extend(additional_subjects)
        # Immutable: freeze the pattern list
        self._frozen_patterns = tuple(self._patterns)
        logger.info(
            "SafetySubjectEnforcer initialized with %d patterns",
            len(self._frozen_patterns),
        )

    @property
    def patterns(self) -> tuple:
        """Return the immutable tuple of safety subject patterns."""
        return self._frozen_patterns

    def is_safety_subject(self, subject: str) -> bool:
        """True when the subject matches a safety pattern.

        Uses the gatekeeper's ``_subject_match`` with NATS-style wildcards
        (``*`` for single token, ``>`` for tail).
        """
        return any(
            _subject_match(pattern, subject) for pattern in self._frozen_patterns
        )

    def check_publish(
        self,
        subject: str,
        token_id: Optional[str] = None,
        check_token_fn=None,
    ) -> Dict:
        """Check whether a publish to the given subject is allowed.

        Rules (enforced in order, fail-closed):
        1. If the subject is NOT a safety subject → allow (unrestricted).
        2. If the subject IS a safety subject and no token_id is provided → DENY.
        3. If the token exists and is active → allow.
        4. If the token is expired, consumed, or unknown → DENY.

        Args:
            subject: The NATS subject being published to.
            token_id: Optional capability token ID from the gatekeeper.
            check_token_fn: Optional override for token validation callable.
                            Defaults to ``_is_token_active``.

        Returns:
            Dict with:
              - ``allowed``: True/False
              - ``reason``: explanation string
              - ``subject``: the subject checked
        """
        if not self.is_safety_subject(subject):
            return {"allowed": True, "reason": "not_safety_subject", "subject": subject}

        if not token_id:
            logger.warning(
                "BLOCKED: safety subject %s published without token",
                subject,
            )
            return {
                "allowed": False,
                "reason": "safety_subject_requires_token",
                "subject": subject,
            }

        # Validate the token
        checker = check_token_fn or _is_token_active
        if checker(token_id):
            token = TOKEN_REGISTRY.get(token_id, {})
            logger.info(
                "ALLOWED: safety subject %s with token %s (capability: %s)",
                subject,
                token_id,
                token.get("capability", "unknown"),
            )
            return {
                "allowed": True,
                "reason": "token_valid",
                "subject": subject,
                "token_id": token_id,
                "capability": token.get("capability", ""),
            }

        # Token is inactive (expired, consumed, or unknown)
        token = TOKEN_REGISTRY.get(token_id, {})
        status = token.get("status", "unknown") if token else "unknown"
        logger.warning(
            "BLOCKED: safety subject %s with %s token %s",
            subject,
            status,
            token_id,
        )
        return {
            "allowed": False,
            "reason": f"token_{status}",
            "subject": subject,
            "token_id": token_id,
        }

    def check_publish_with_token_check(
        self,
        subject: str,
        token_id: str,
    ) -> bool:
        """Convenience boolean wrapper around ``check_publish``.

        Returns True when the publish is allowed (subject is not safety, or
        token is valid for a safety subject).
        """
        return self.check_publish(subject, token_id=token_id)["allowed"]