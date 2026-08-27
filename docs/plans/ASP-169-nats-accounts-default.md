# Plan: ASP-169 / H-001 — NATS accounts + nkeys auth by default

Threat model v2.1 finding F-001. Agent-bus NATS currently defaults to zero
authentication (`nats/agent-bus.conf`) and firstboot falls back to it for
server/edge profiles.

## Goal

Accounts mode (multi-tenant accounts + nkeys) is the default everywhere.
No-auth dev config is removed; the bus fails closed instead of silently
starting unauthenticated.

## Acceptance criteria (from issue)

1. `agent-bus.conf` removed (no startup path can select it).
2. Firstboot generates multi-tenant accounts (OPS, EDGE, RANGE, TELEM) with nkeys.
3. Every agent connects with account credentials, not bare token.
4. Documented migration path for single-node dev setups.

## Changes

| # | File | Change |
|---|------|--------|
| 1 | `nats/agent-bus.conf` | Delete |
| 2 | `scripts/starship-firstboot.sh` | Accounts = default for ALL profiles; drop `_enable_agent_bus`; auth'd fleet-token remains explicit opt-in (`STARSHIP_NATS_MODE=fleet`); fail loud if no auth'd config can be materialized |
| 3 | `scripts/start-agents.sh` (+ src mirror) | Start NATS with local accounts conf, generating creds via `gen-nats-accounts.sh` when absent — never agent-bus |
| 4 | `scripts/install-daemon.sh` (+ src mirror) | Default `active.conf` → `fleet-accounts.conf`; materialize on install if missing; remove agent-bus copies/fallbacks |
| 5 | `scripts/build-deb.sh` (+ src mirror) | Stop packaging agent-bus.conf |
| 6 | `config/profiles.yaml` | edge/server `nats_mode: agent` → `accounts` |
| 7 | `systemd/agnetic-nats.service`, `services/watchdog.py` | Comment/command reference accounts conf |
| 8 | `agents/nats_connect.py` | Fail-closed guard: `STARSHIP_NATS_MODE=accounts` requires user/pass or nkey seed — refuse bare token/anonymous with migration hint |
| 9 | Docs: README, SECURITY, FLEET, MULTI_NODE, ARCHITECTURE_COMPLETE, iso/autoinstall README, `nats/fleet-auth.yaml` | Modes tables updated + single-node dev migration section (localhost accounts via `gen-nats-accounts.sh`) |
| 10 | `tests/test_nats_accounts_default.py` | Guard tests for all of the above |

## Out of scope

- `nats/server.conf` hardcoded credentials → H-017 ([ASP-365](/ASP/issues/ASP-365))
- TLS-by-default → H-006 ([ASP-174](/ASP/issues/ASP-174))

## Verification

- `pytest tests/test_nats_accounts_default.py` (new) + existing suites green
- `bash -n` on every modified shell script
- grep proves zero remaining functional references to agent-bus

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — NATS accounts default configuration landed. `pytest tests/test_nats_accounts_default.py` + existing suites green. `bash -n` clean on all modified shell scripts. Zero remaining functional references to `agent-bus`.
