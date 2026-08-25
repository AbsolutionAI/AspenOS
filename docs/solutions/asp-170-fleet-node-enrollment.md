# Fleet node enrollment with signed identity tokens (ASP-170 / H-002)

**Date:** 2026-08-24
**Tickets:** ASP-170, ASP-169 (accounts), ASP-174 (mTLS)

## Problem

`fleet-node.yaml` was a local file with no attestation. `gen-nats-tls.sh --node`
issued certs but had no protocol — key and cert were minted in the same place,
no token gated issuance, and compromised nodes could not be revoked.

## Solution

A three-part enrollment protocol built on the fleet CA key:

1. **Enrollment tokens** (`ENROLL-v1:<node>:<expiry>.<base64sig>`) signed by the
   fleet CA RSA key. Only CA-key holders can mint tokens; any party with
   `ca.pem` can verify.
2. **`scripts/fleet-enroll.sh`** implements `issue-token`, `request`, `sign`,
   and `revoke [--list]` subcommands. Private key never leaves the enrolling
   node; CSR is shipped to the ops manager for signing.
3. **Runtime revocation enforcement** at three layers:
   - `fleet-enroll.sh sign` refuses to sign a revoked node.
   - `nats_connect.py::check_local_identity()` refuses to connect if the
     local node appears on the revocation list.
   - `services/fleet.py` drops heartbeats from revoked peers.

## Patterns to reuse

1. **No new second secret.** Enrollment tokens reuse the fleet CA key (RSA-SHA256
   via `openssl dgst`). Verifier only needs `ca.pem`.
2. **Private key never leaves the node.** The keypair is generated locally; only
   the CSR crosses the wire for signing. This is the standard PKI enrollment
   pattern.
3. **Three-layer revocation** (signing gate, self-check, peer-drop) means a
   compromised node is contained even without centralized CRL distribution.
4. **Shell script over Python** for the enrollment tool — it's a bootstrap
   operation that must work before Python dependencies are available.

## Verification

- `tests/test_fleet_enrollment.py` — end-to-end happy path, tampered/expired/
  wrong-node tokens rejected, revoked refuse at sign/connect/peer layers,
  fail-closed without CA material.
- `bash -n scripts/fleet-enroll.sh`.
- Manual end-to-end: issue-token → request → sign → `openssl verify` chain.

## Remaining

- NATS leaf-node / operator trust chains (architectural, deferred).
- Automated cert renewal/rotation → H-007 (ASP-371).
- CRL distribution over the bus itself.
