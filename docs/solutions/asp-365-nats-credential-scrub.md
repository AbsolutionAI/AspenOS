# NATS credential scrub — burn lab secrets from source tree

**Ticket:** ASP-365 (H-017)
**Date:** 2026-08-25

## Problem

The Starship OS source tree contained live NATS credentials in
`nats/server.conf` — a token (`agnetic_s3cr3t_t0k3n`), admin password
(`agnetic_admin_2026`), and user password (`agnetic_user_2026`). These were
lab/test values from early development. While functionally equivalent to
placeholder tokens (the production deployment materialises fresh creds via
`setup-nats-auth.sh` and firstboot), having live secrets in git exposed the
project to three risks:

1. **Credential leak via git history** — any clone of the repo contained
   machine-usable credentials, even if the file was later changed.
2. **False sense of security** — a reader might assume these were production
   credentials and reuse them elsewhere.
3. **Hygiene precedent** — once burned values enter the tree, automated
   scanners flag every clone, and team members stop trusting the repo's
   security boundary.

## Solution

### `nats/server.conf` — replace live values with placeholders

Replaced the three burned credential fields with `__STARSHIP_NATS_TOKEN__`,
`__NATS_ADMIN_PASS__`, and `__NATS_USER_PASS__` — the same placeholders used
throughout the fleet config system. These have zero functional value outside
the firstboot materialisation pipeline.

### `scripts/setup-nats-auth.sh` — credential rotation, no print

- Rewrote the script to generate fresh random credentials at setup time
  instead of embedding defaults.
- Added a credential rotation scheme: when `--rotate` is passed, new creds
  are generated and the old ones are archived.
- Removed all `echo` / `printf` of generated secrets to stdout (they are
  written only to the config file on disk).
- Added `set -euo pipefail` for robustness.

### Smoke-test and packaging

- Added regression checks in `smoke-test.sh` that verify no live lab NATS
  secrets exist in `nats/` or `scripts/setup-nats-auth.sh`.
- `build-deb.sh` and `install-daemon.sh` now install `server.conf` as
  `server.conf.deprecated` (stub only) — the active config is always
  generated at firstboot.
- Added `tests/test_nats_accounts_default.py` with 100+ lines of contract
  tests: path assertions, placeholder presence, no-hardcoded-secrets scans.

### Documentation

- `docs/SECURITY.md` — new file documenting credential lifecycle, rotation
  policy, and audit procedures (46 lines).
- Updated `docs/AGENT_GUIDE.md`, `docs/ARCHITECTURE_COMPLETE.md`,
  `docs/FLEET.md`, and top-level `SECURITY.md` to reflect the no-credentials-
  in-repo policy.

## Reflection

The root cause was **credential entropy by neglect** — the lab values were
never meant to be production credentials, but they were also never cleaned
up after the placeholder-based firstboot system was implemented. They became
a "works on my machine" crutch for local development, which is exactly the
pattern that leads to credential sprawl.

Key takeaway: once a credential file moves from "manually configured" to
"auto-generated at firstboot," the template file in git should be scrubbed
of any real values immediately. The firstboot materialisation pipeline was
working correctly, but the stale template was a latent vulnerability.

The contract tests (`tests/test_nats_accounts_default.py`) should prevent
regression: they assert both the presence of placeholders *and* the absence
of any string matching the known burned credential patterns.

## Files changed

- `nats/server.conf` — live credentials → placeholders
- `scripts/setup-nats-auth.sh` — generate fresh creds, never print, `--rotate`
- `scripts/build-deb.sh` — install server.conf as `.deprecated`
- `scripts/install-daemon.sh` — install server.conf as `.deprecated`
- `scripts/smoke-test.sh` — regression checks for burned secrets
- `src/python/lib/scripts/build-deb.sh` — same as above (python mirror)
- `src/python/lib/scripts/install-daemon.sh` — same as above
- `src/python/lib/scripts/setup-nats-auth.sh` — same as above
- `tests/test_nats_accounts_default.py` — 106-line contract test suite
- `docs/SECURITY.md` — new credential lifecycle doc

## Related

- ASP-169 (NATS accounts + nkeys by default — complementary auth change)
- ASP-170 (fleet node enrollment — credential rotation feeds into enrollment)
- ASP-174 (NATS TLS+mTLS default — transport-layer counterpart)
- `docs/solutions/asp-169-nats-accounts-default.md`
- `docs/solutions/asp-170-fleet-node-enrollment.md`
