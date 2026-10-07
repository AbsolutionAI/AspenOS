# H-024 — WAN Deployment with Mutual TLS

**Owner:** Aspen OS Development · **Control:** H-024 (IEC 62443-4-2 cell assessment)
**Implements:** threat model v2.2 §8 item 16 (TLS by default) · **Issue:** ASP-684

A cell that speaks NATS across a WAN link is carrying the fleet bus — agent heartbeats,
audit events, plant control messages — over an untrusted network. This document is the
deployment reference for that case.

## Why mutual, not just server TLS

Server-authenticated TLS proves the server holds a key for `cell-N.local`. It does not
prove the *client* is one of your cells. With a shared fleet token, anyone who has
exfiltrated `/etc/starship/nats-token` can complete a handshake against a
server-auth-only listener and read the bus.

Mutual TLS closes that: `verify: true` makes the server demand a CA-signed client
certificate before the connection is accepted. A stolen token alone is then not enough —
the attacker also needs a key issued by your fleet CA.

## What firstboot does now

TLS mode is resolved before the NATS bus is brought up:

| Condition | Result |
|---|---|
| `STARSHIP_NATS_TLS` explicitly `0`/`false`/`off`/`no` | **off** (opt-out always wins) |
| `STARSHIP_NATS_TLS` explicitly `1`/`true`/`on`/`yes` | **on** |
| profile `ops` or `edge` | **on** (H-024 default) |
| any other profile (`server`, dev) | **off** (loopback agent-bus) |

TLS is applied *after* bus selection, resolving `/etc/starship/nats/active.conf`. The same
path therefore covers all three bus modes — `fleet-accounts`, `fleet-bus`, and `agent-bus`.
Before this change the TLS block existed only inside `_enable_accounts_bus`, so setting
`STARSHIP_NATS_TLS=1` on an `edge` cell was silently ignored.

**Fail-closed.** If TLS is required and the material cannot be established, firstboot exits
non-zero rather than continuing with plaintext. A silently-unencrypted bus is worse than a
failed boot: it manufactures the belief that the link is protected when it is not.

## Enabling it

Default (server-auth only) — no action needed on `ops`/`edge`:

```bash
# in /etc/starship/firstboot.env
STARSHIP_PROFILE=ops
```

Mutual TLS (required for WAN):

```bash
# in /etc/starship/firstboot.env
STARSHIP_PROFILE=ops
STARSHIP_NATS_TLS=1
STARSHIP_NATS_TLS_MUTUAL=1
STARSHIP_NATS_TLS_HOST=cell-alpha.plant.example.com
```

`STARSHIP_NATS_TLS_HOST` becomes the certificate CN and the first SAN. It must match the
name clients dial, or the handshake fails hostname verification — use the FQDN the fleet
actually reaches, not `localhost`.

Re-running the generator with `--mutual` on a cell that already has server-auth material
**re-issues the config snippet without rotating certificates**. Existing certs are
preserved. Rotating them is a deliberate, separate action (see below).

Result:

```
/etc/starship/nats/tls/
├── ca.pem             # trust anchor — distribute to clients
├── ca-key.pem         # 600 — offline; never ships to clients
├── server-cert.pem    # server identity
├── server-key.pem     # 600
├── client-cert.pem    # client identity for mTLS
├── client-key.pem     # 600
├── tls.conf.snippet   # tls { ... verify: true ... }  appended to active.conf
└── client.env         # 600 — CA/cert/key paths + NATS_URL=tls://
```

## Commissioning

A cell that cannot produce TLS material (no `openssl`, missing generator script) fails
firstboot. During a commissioning window only, this is recoverable:

```bash
STARSHIP_NATS_TLS_BEST_EFFORT=1 /opt/starship/bin/starship-firstboot.sh
```

This logs `WARN: NATS TLS required but unavailable — continuing UNENCRYPTED`. It is a
**commissioning override, not a deployment mode.** Do not commission a cell on a WAN link
with it set — that is an open H-024 violation, and the production cell commission checklist
item 3 should be marked failed.

The permanent opt-out is `STARSHIP_NATS_TLS=0` in `firstboot.env`.

## Verifying a deployed cell

```bash
# snippet is in the active conf, and mTLS is really on
grep -A6 '^tls {' "$(readlink -f /etc/starship/nats/active.conf)"

# client env points at TLS
grep -E '^(NATS_URL|STARSHIP_NATS_TLS|STARSHIP_NATS_CA)=' /etc/starship/nats.env

# listener is not accepting a bare-TCP handshake on the WAN interface
sudo nats-server -t -c "$(readlink -f /etc/starship/nats/active.conf)"
```

`nats-server -t` parses the config and exits non-zero on a malformed TLS block — that is the
cheapest proof that a bad snippet has not taken the cell down.

## Rotation

This change does **not** introduce an expiry cadence. Key rotation is owned by H-017
(threat model §8 item 11) and covers NATS credentials generally. Until H-017 lands, the
generated material is valid for 825 days and re-running the generator is idempotent — it
will not silently rotate a live cell.

To rotate deliberately:

```bash
STARSHIP_NATS_TLS_FORCE=1 bash scripts/gen-nats-tls.sh --out /etc/starship/nats/tls \
  --host cell-alpha.plant.example.com --mutual
# distribute the new ca.pem + client-cert to every peer FIRST, then restart NATS
```

Order matters. Rolling the server CA before clients hold the new cert takes the fleet bus
down.

## Related

- `scripts/check-nats-tls-default.sh` — CI/nightly gate (H-024)
- `scripts/gen-nats-tls.sh` — material generation
- `scripts/starship-firstboot.sh` — `_resolve_tls_mode` / `_enable_nats_tls`
- `docs/plans/ASP-684.md` · `docs/solutions/asp-684-nats-tls-by-default.md`
- `docs/SECURITY_THREAT_MODEL_v2.2.md` §8 item 16