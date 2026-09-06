# ASP-536: aspen.* subject ACLs + nkey-only NATS credentials

## Problem

`nats/fleet-accounts.conf.tmpl` only guarded `starship.*` / `agnetic.*`. The
`aspen.*` namespace (ADR-0007: sentinel/authz/fleet/safety) was unguarded and
the `STARSHIP_OPS` user had **no permissions block** (open-by-default) — a
compromised ops credential could publish arbitrary `aspen.fleet.mission.*` or
`aspen.safety.*` messages. Credentials were also plaintext passwords embedded
in the materialized conf (H-011), with nkeys only added as a *sibling* entry.

## Solution

1. **Per-role `aspen.*` ACLs** in the template: ops = mesh/sentinel host
   (all four `aspen.*` prefixes), edge = `aspen.fleet.>`, `aspen.edge.>`,
   `aspen.safety.{estop,authorize_clear,clear}`, `aspen.sentinel.>` subscribe;
   range red/blue = scoped fleet/heartbeat + estop subscribe; telemetry unchanged.
   ops's previously-open permissions are now enumerated (still allow
   `starship.>`/`agnetic.>` → no regression).
2. **nkey-only by default:** `gen-nats-accounts.sh` substitutes the whole
   `{user, password}` entry with `{nkey: "U..."}` when `nk` is available;
   `--password-only` restores the legacy fallback. `nats-server -t` rejects
   `{user: "...", nkey: "..."}` ("Nkey users do not take usernames or
   passwords") — the user field must be dropped too.
3. Doc-drift: `fleet-auth.yaml` + `subjects.yaml` mirror the matrix; a
   smoke-test regression guard asserts the four `aspen.*` prefixes survive
   generation.

## Key gotchas

- **Import cycles are rejected:** OPS importing `aspen.safety.estop` from EDGE
  *and* EDGE importing it from OPS → `import forms a cycle`. Pick one direction:
  estop fans **up** edge→ops; sentinel streams flow ops→edge. No two accounts
  may import the same subject from each other.
- **nkey and username are mutually exclusive** in NATS user entries.
- **Per-subject live test:** a config that parses (`nats-server -t`) can still
  silently fail *delivery* when subjects aren't exported/imported across
  accounts. Always verify with a real pub/sub client (`nats-py` + `nkeys`).
- For sandbox runs, patch `jetstream.store_dir` (writable scratch) — the
  default `/var/lib/starship/nats` needs root.

## Verification

- `nats-server -t` valid in nkey-only and password modes.
- Live `nats-py`/nkeys: sentinel pub/sub, estop fanout edge→ops, sentinel
  overview ops→edge, and denial of `aspen.authz.gate.decision` from edge.
- Regression diff: only additive `aspen.*` lines; `starship.*`/`agnetic.*`
  entries unchanged; nightly "gen accounts conf valid" smoke passes.

## Related

- H-013 (Closed), H-011; ADR-0007, ADR-0003; `docs/plans/ASP-536.md`
  (commit `16eee48`)
- Follow-ups: ASP-537 (audit publisher), ASP-540 (gatekeeper) consume the new
  ACLs; the H-013 threat-model row is still "Open: mid-migration" pending the
  in-flight ASP-538/539 edits to that file.