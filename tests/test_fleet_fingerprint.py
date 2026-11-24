"""F-017: Fleet node fingerprint validation (hermetic fixture).

Verifies the fingerprint allowlist logic defined in
docs/security/f-017-fleet-node-fingerprint.md. No NATS, no network.
"""
import hashlib


def validate_fingerprint(
    node_id: str,
    payload_fingerprint: str | None,
    allowlist: dict[str, str],
) -> tuple[bool, str]:
    """Validate a node register/heartbeat fingerprint against the allowlist.

    Returns (accepted, reason). Accepted=False means the payload should be
    rejected by the ops-manager.
    """
    expected = allowlist.get(node_id)

    if payload_fingerprint is None and expected is None:
        return True, "no-allowlist-entry-no-fingerprint"
    if payload_fingerprint is None and expected is not None:
        return False, "enrolled-node-missing-fingerprint"
    if payload_fingerprint is not None and expected is None:
        return True, "unrecognized-node-unenrolled"
    if payload_fingerprint == expected:
        return True, "fingerprint-match"
    return False, "fingerprint-mismatch"


class TestFleetFingerprint:
    """Hermetic tests for F-017 fingerprint validation rules.

    Rules (from the spec):
    1. No fingerprint + no allowlist entry → accept (backward compat)
    2. No fingerprint + allowlist entry → reject
    3. Fingerprint + no allowlist entry → accept (log as unknown)
    4. Fingerprint + matching allowlist entry → accept
    5. Fingerprint + mismatched allowlist entry → reject
    """

    def test_no_fingerprint_no_allowlist(self):
        """Rule 1: pre-fingerprint nodes work with no allowlist."""
        accepted, reason = validate_fingerprint("node-a", None, {})
        assert accepted, f"expected accept, got {reason}"
        assert reason == "no-allowlist-entry-no-fingerprint"

    def test_no_fingerprint_with_allowlist_rejected(self):
        """Rule 2: enrolled node must advertise its fingerprint."""
        allowlist = {"node-a": "abc123"}
        accepted, reason = validate_fingerprint("node-a", None, allowlist)
        assert not accepted, f"expected reject, got {reason}"
        assert reason == "enrolled-node-missing-fingerprint"

    def test_unknown_fingerprint_no_allowlist_accepted(self):
        """Rule 3: unenrolled node with fingerprint is accepted (logged)."""
        accepted, reason = validate_fingerprint("node-a", "def456", {})
        assert accepted, f"expected accept, got {reason}"
        assert reason == "unrecognized-node-unenrolled"

    def test_matching_fingerprint_accepted(self):
        """Rule 4: happy path."""
        allowlist = {"node-a": "abc123"}
        accepted, reason = validate_fingerprint("node-a", "abc123", allowlist)
        assert accepted, f"expected accept, got {reason}"
        assert reason == "fingerprint-match"

    def test_mismatched_fingerprint_rejected(self):
        """Rule 5: spoofing attempt — reject."""
        allowlist = {"node-a": "abc123"}
        accepted, reason = validate_fingerprint("node-a", "fake999", allowlist)
        assert not accepted, f"expected reject, got {reason}"
        assert reason == "fingerprint-mismatch"

    def test_many_nodes_independent(self):
        """Multiple allowlist entries do not interfere."""
        allowlist = {"node-a": "aaa", "node-b": "bbb"}
        assert validate_fingerprint("node-a", "aaa", allowlist)[0]
        assert validate_fingerprint("node-b", "bbb", allowlist)[0]
        assert not validate_fingerprint("node-a", "bbb", allowlist)[0]
        assert not validate_fingerprint("node-b", "aaa", allowlist)[0]

    def test_allowlist_empty_all_unknown_accepted(self):
        """An empty allowlist accepts all (backward compat during rollout)."""
        assert validate_fingerprint("node-a", "xxx", {})[0]
        assert validate_fingerprint("node-a", None, {})[0]
        assert validate_fingerprint("node-b", "yyy", {})[0]

    def test_hash_derivation_is_deterministic(self):
        """SHA-256 of machine-id produces a stable fingerprint."""
        mid = "abc123def456\n"
        fp1 = hashlib.sha256(mid.strip().lower().encode()).hexdigest()
        fp2 = hashlib.sha256(mid.strip().lower().encode()).hexdigest()
        assert fp1 == fp2

    def test_registered_node_missing_fingerprint_fails(self):
        """Partial enrollment: some nodes in allowlist, some not."""
        allowlist = {"enrolled-node": "abc123"}
        assert validate_fingerprint("enrolled-node", None, allowlist)[0] is False
        assert validate_fingerprint("new-node", None, allowlist)[0]