# Plan: ASP-170 / H-002 — Fleet node enrollment with signed identity tokens

Threat model v2.1 finding F-002: no per-node identity or enrollment mechanism.
`fleet-node.yaml` is a local file with no attestation; `gen-nats-tls.sh --node`
issues certs but has no protocol — key and cert are minted in the same place,
no token gates issuance, and compromised nodes cannot be revoked.

Builds directly on H-001 (accounts+nkeys, [ASP-169](/ASP/issues/ASP-169)) and
H-006 (mTLS by default, fleet CA, [ASP-174](/ASP/issues/ASP-174)).

## Goal

A rogue node cannot obtain a fleet identity without a signed enrollment token
issued by the ops manager; nodes prove that identity on every NATS connect;
compromised node identities can be revoked and every enforcement point fails
closed.

## Acceptance criteria (from issue)

1. Enrollment protocol: new node generates the keypair locally, ops manager
   signs the node identity cert (private key never leaves the node).
2. Node identity verified on every NATS connect (mTLS `verify:true` + client
   refuses to connect when its own identity is revoked).
3. Revocation list for compromised nodes, enforced at signing, at the fleet
   daemon (peer events), and in `nats_connect`.
4. Rogue node cannot join without a signed enrollment token (token is
   RSA-signed by the fleet CA key, bound to one node name + expiry).

## Design

Enrollment tokens are signed by the **fleet CA private key** (RSA-SHA256 via
`openssl dgst`), so no second secret is introduced: only CA-key holders can
mint tokens, and any party with `ca.pem` can verify them.

Token format (single line): `ENROLL-v1:<node>:<expiry_epoch>.<base64(sig)>`
where sig = RSA-SHA256 over `ENROLL-v1:<node>:<expiry_epoch>\n`.

Flow:

```
ops manager                          enrolling node
-----------                          --------------
fleet-enroll.sh issue-token --node cell-7
        │  (out of band)
        └──────────────────────────► fleet-enroll.sh request --node cell-7 --token ...
                                     key.pem + csr.pem stay local
        ◄── ship csr.pem + token ────
fleet-enroll.sh sign --request DIR
  verify: token sig, expiry, CN match, not revoked
        └──────────────────────────► install node-cell-7-cert.pem + .env
```

## Changes

| # | File | Change |
|---|------|--------|
| 1 | `scripts/fleet-enroll.sh` (new) | `issue-token`, `request`, `sign`, `revoke [--list]`; revocation list `<tls-out>/revocations.list`; every command fails closed without fleet CA material |
| 2 | `agents/nats_connect.py` | `local_identity_cn()`, `revocations_path()`, `is_revoked()`, `check_local_identity()` (RuntimeError on revoked self); called from `connect()` |
| 3 | `services/fleet.py` | `identity_revoked()` helper; register/heartbeat handlers drop revoked peers; local node payload carries mTLS `identity` CN |
| 4 | `tests/test_fleet_enrollment.py` (new) | End-to-end happy path; tampered/expired/wrong-node tokens rejected; revoked refused at sign/connect/peer layers; fail-closed without CA |
| 5 | Docs: `SECURITY.md`, `docs/SECURITY.md`, `docs/FLEET.md`, `README.md` | H-002 rows + enrollment runbook section |

`gen-nats-tls.sh --node` stays as ops-manager-local convenience (requires CA
key possession, same trust as issuing tokens); remote nodes use the protocol.

## Out of scope

- NATS leaf-node / operator + JetStream domain trust chains (architectural)
- Automated cert renewal/rotation → H-007 secret rotation ([ASP-371](/ASP/issues/ASP-371))
- CRL distribution over the bus itself

## Verification

- `pytest tests/test_fleet_enrollment.py tests/test_nats_tls_default.py tests/test_nats_accounts_default.py`
- `bash -n scripts/fleet-enroll.sh`
- Manual end-to-end: issue-token → request → sign → `openssl verify` chain

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — Fleet node enrollment landed. NATS leaf-node trust chain, `scripts/fleet-enroll.sh` with TLS. `pytest tests/test_fleet_enrollment.py` + related suites green. `bash -n` clean.
