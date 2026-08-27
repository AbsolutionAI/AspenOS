# NATS accounts + nkeys auth by default (ASP-169 / H-001)

**Date:** 2026-08-24
**Tickets:** ASP-169, ASP-174 (TLS), ASP-170 (enrollment)

## Problem

`nats/agent-bus.conf` started NATS with zero authentication. Firstboot fell
back to it for server/edge profiles. Any process on the local network could
publish/subscribe to the agent bus.

## Solution

Six changes closed the auth gap:

1. **`nats/agent-bus.conf` deleted** — no startup path can select it.
2. **Profiles default to `nats_mode: accounts`** in `config/profiles.yaml`
   (edge, server, ops all use accounts + nkeys).
3. **`gen-nats-accounts.sh`** creates OPS, EDGE, RANGE, TELEM accounts with
   nkey-seed credentials on firstboot.
4. **`nats_connect.py` fails closed** — `STARSHIP_NATS_MODE=accounts` requires
   user/pass or nkey seed; bare token/anonymous gets a migration hint + error.
5. **Install-daemon materializes `fleet-accounts.conf`** as the active NATS
   config instead of `agent-bus.conf`.
6. **Systemd unit references `fleet-accounts.conf`** — `agnetic-nats.service`
   ExecStart uses `-c /etc/starship/nats/fleet-accounts.conf`.

## Patterns to reuse

1. **Fail closed as default posture.** The absence of credentials is an error,
   not a hint to start unauthenticated. Every future transport-gap should
   follow the same principle.
2. **One config generation script per auth mode.** `gen-nats-accounts.sh` is
   the canonical accounts creator; `gen-nats-tls.sh` handles TLS mode. No
   ad-hoc conf files.
3. **Profiles.yaml as single source of truth** for which auth mode each
   deployment profile uses. The installer reads the profile, not a hardcoded
   fallback.

## Verification

- `tests/test_nats_accounts_default.py` — 24 tests covering accounts
  generation, connect with credentials, and fail-closed on bare token.
- `bash -n` on all modified shell scripts.
- Manual: firstboot generates accounts, agents connect via nkey, unknown
  tokens are refused.

## Remaining

- `nats/server.conf` hardcoded credentials → H-017 (ASP-365).
- TLS-by-default → H-006 (ASP-174, implemented in same forward-port batch).
