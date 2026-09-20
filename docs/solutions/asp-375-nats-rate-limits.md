# ASP-375: F-011 — NATS rate limiting + tighter connection limits

**Status:** READY_FOR_AIDER_QA
**Mode:** IMPLEMENTATION

## Threat-model link

DoS row of the ASP-298 refresh — *Flood fleet subjects* — was mitigated only by
`max_connections` + `max_payload`. This ticket (F-011) goes beyond the existing
caps: per-connection rate limits, auth-failure hardening, and per-account
blast-radius caps for the fleet bus and accounts mode.

## Key insight: nats-server v2.14 has no `auth_failure_timeout`

Verified against the pinned nats-server v2.14.5 source (`server/opts.go`):
`auth_failure_timeout` / `auth_timeout` are **not** config fields. "Auth failure
rate limiting" is therefore delivered through the native knobs that bound
auth-connection resource use and failed-connection bookkeeping:

- `authorization { timeout }` — the auth handshake window. Lowered 5.0s → **2.0s**
  (the server default) so unauthenticated connections cannot park in a slot.
  Verified live: a connection that sends no `CONNECT` is dropped with
  `-ERR 'Authentication Timeout'` at exactly 2.0s; a wrong token is refused
  with `-ERR 'Authorization Violation'`.
- `max_closed_clients` — retained closed-connection state cap (10000 → **4096**).
- `connect_error_reports` / `reconnect_error_reports` — explicit, documented
  throttling of connect/auth-failure log spam.

## Changes

### Global hardening block (all three NATS configs)

`nats/agent-bus.conf`, `nats/fleet-bus.conf`, `nats/fleet-accounts.conf.tmpl`:

| Option | Old | New | Purpose |
|--------|-----|-----|---------|
| `max_pending` | default 64MB | **16MB** | per-connection buffered-bytes cap (kept >= 8MB `max_payload` invariant) |
| `max_control_line` | default 4KB | **4KB** (explicit) | cap oversized CONNECT/PUB control lines |
| `max_subscriptions` | unlimited | **512** | cap subscription floods per client |
| `max_closed_clients` | 10000 | **4096** | cap retained closed-connection state |
| `max_traced_msg_len` | unlimited | **512** | cap debug/trace log amplification |
| `write_deadline` | 10s | **5s** | cap write stalls |
| `ping_interval` / `ping_max` | 2m / 2 | **30s / 3** | faster slow-consumer detection |
| auth `timeout` (fleet-bus) | 5.0s | **2.0s** | bound auth handshake, drop no-CONNECT clients |

### Per-account limits (`nats/fleet-accounts.conf.tmpl`)

NATS account `limits { max_connections, max_subscriptions }` bound each role's
blast radius below the server-wide `max_connections: 256`:

| Account | max_connections | max_subscriptions |
|---------|-----------------|-------------------|
| `SYS` | 4 | 16 |
| `STARSHIP_OPS` | 64 | 512 |
| `STARSHIP_EDGE` | 128 | 512 |
| `STARSHIP_RANGE` | 32 | 256 |
| `STARSHIP_TELEM` | 32 | 16 |

`gen-nats-accounts.sh` passes the blocks through untouched (sed only replaces
credentials/ports placeholders).

## Verification

```bash
# config parse (nats-server -t on every config + materialized accounts conf)
nats-server -c nats/agent-bus.conf -t
nats-server -c nats/fleet-bus.conf -t
bash scripts/gen-nats-accounts.sh --out "$OUT" --port 14222 && nats-server -c "$OUT/fleet-accounts.conf" -t

# unit tests (5 passed)
python3 -m pytest tests/test_nats_rate_limits.py -v
```

Live runtime checks performed against a local nats-server v2.14.5:

- 34 connections to the telem account (cap 32) → **2 refused**.
- 20 subscriptions on telem (cap 16) → subs 17+ refused
  (`-ERR 'maximum subscriptions exceeded'`).
- fleet-bus: good token → PONG; bad token → `-ERR 'Authorization Violation'`;
  no CONNECT → `-ERR 'Authentication Timeout'` dropped after 2.0s.

## Files changed

| File | Change |
|------|--------|
| `nats/agent-bus.conf` | hardening block |
| `nats/fleet-bus.conf` | hardening block + auth timeout 5.0 → 2.0 |
| `nats/fleet-accounts.conf.tmpl` | hardening block + per-account `limits` |
| `tests/test_nats_rate_limits.py` | New: key-presence, invariant, `-t` parse, materialized-conf tests |
| `scripts/check-nightly.sh` | +Section 19 gates |
| `tests/test_ci_assertions.py` | Section 19 presence assertion |
| `docs/plans/ASP-375.md` | Plan document |
| `docs/ops/NIGHTLY_PACKAGING_DEPLOY_CHECK.md` | Section 19 row + baseline |

Related: [ASP-373](/ASP/issues/ASP-373) (F-009 mode 600), [ASP-536](/ASP/issues/ASP-536)
(H-011 plaintext-creds, the other H-011).