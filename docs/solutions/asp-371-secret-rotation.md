# ASP-371: Automated secret rotation (IEC 62443 SR 4.2)

**Ticket:** ASP-371  
**Threat model entries:** H-017 (NATS credential rotation — no automatic rotation), F-007 (medium, carried from v2.1)  
**Standard:** IEC 62443 SR 4.2 — "Any provision of information by a previous user of the asset is prevented"  
**Parent:** ASP-298 (Biweekly Security Threat-Model refresh)

## Problem

All NATS credentials in Starship OS are generated once by `scripts/gen-nats-accounts.sh` at firstboot or when `setup-nats-auth.sh` runs, then never rotated. This means:

1. **No credential expiry enforcement** — a leaked password or nkey seed is valid indefinitely.
2. **No rotation procedure** — there is no script or documented process to issue fresh credentials and propagate them to running agents.
3. **Plaintext on disk** (H-011) — `fleet-accounts.conf` contains passwords in plaintext; rotation would also allow transitioning toward nkey-only auth.
4. **SecretsManager master key static** — `AGENTIC_MASTER_PASSWORD` env var persists across sessions with no re-key mechanism.

IEC 62443 SR 4.2 requires that provision of information from a previous user is prevented. Without rotation, a former agent or compromised credential retains access until manual regeneration.

## Current credential landscape

| Secret type | Source | Lifetime | Rotation mechanism | Stored at |
|-------------|--------|----------|--------------------|-----------|
| NATS account passwords | `gen-nats-accounts.sh` (random hex) | Infinite | None | `fleet-accounts.conf` (plaintext), `creds/*.env` |
| NATS nkey seeds | `gen-nats-accounts.sh` (nk -gen user) | Infinite | None (regenerate) | `creds/*.nk` (mode 600) |
| Agent tokens (Hermes) | `security.py generate-tokens` | Infinite | None | `SecretsManager` encrypted store |
| SecretsManager master key | `AGENTIC_MASTER_PASSWORD` env var | Infinite | None (manual re-encrypt) | Process env / keyring |
| StarAgent nkey | Fleet daemon bootstrap | Per-deploy | Redeploy agent | Agent config |

## Solution

### Design overview

Three rotation scripts, one coordinator, all safe by default (dry-run mode):

```
scripts/
  rotate-nats-creds.sh        — Rotate NATS account passwords + nkeys
  rotate-nkeys.sh             — Rotate nkey pairs only (lighter operation)
  rotate-secrets-manager.sh   — Re-encrypt SecretsManager store with new master key
  rotate-all.sh               — Coordinator: orchestrate with grace periods
```

All scripts accept `--dry-run` (default) and `--force` flags. `--dry-run` prints what would change without touching any file. The coordinator never defaults to live rotation — operator must explicitly pass `--force`.

### Rotation scheme: NATS credentials

```
1. Generate new passwords + nkey pairs (same as gen-nats-accounts.sh)
2. Write fleet-accounts.conf.new with new creds + old nkeys as secondary users
3. SIGHUP nats-server to reload config (graceful — existing connections survive)
4. Wait grace period (default 60s) for agents to reconnect with new creds
5. Remove old credentials from config and second SIGHUP
6. Update client env files with new creds
7. Log rotation event to syslog + audit file
```

The two-phase approach (dual config during grace) avoids connectivity blips: agents using the old password still authenticate during the grace window because the NATS config includes both old and new user entries.

### Rotation scheme: nkeys

```
1. Generate new nkey pairs for each role
2. Add new public keys to NATS account user entries
3. SIGHUP nats-server
4. Distribute new nkey seeds to agents (creds/*.nk)
5. Grace period, then remove old nkey public keys
6. Second SIGHUP
```

### Rotation scheme: SecretsManager master key

```
1. Decrypt all secrets with old master password
2. Prompt for new master password (or generate)
3. Re-encrypt all secrets with new key
4. Write updated secrets to disk (atomic directory swap)
5. Log rotation event
6. Operator must update AGENTIC_MASTER_PASSWORD (or keyring) separately
```

### Frequency recommendation

| Secret type | Recommended rotation | Trigger |
|-------------|---------------------|---------|
| NATS passwords | 90 days | Cron / monthly ops sweep |
| NATS nkeys | 180 days | Quarterly maintenance |
| SecretsManager master key | Per-incident or 365 days | Compromise event or annual |
| Agent tokens | Per-deployment | Redeploy agent |

### IEC 62443 SR 4.2 compliance

| Requirement | Implementation |
|-------------|---------------|
| Prevent provision of previous user info | Rotation replaces all credentials; old passwords/nkeys removed after grace window |
| Automated rotation | `scripts/rotate-*.sh` scripts automate the full cycle |
| Audit trail of rotations | All scripts log to syslog + `/var/log/starship/rotation-audit.log` |
| Graceful transition | Two-phase config reload prevents connectivity loss during rotation |
| Dry-run safe | All scripts default to `--dry-run`; no state changes without `--force` |

### Key design decisions

1. **Two-phase reload over in-place edit** — NATS supports multiple user entries per account. By adding new creds alongside old, then removing old after a grace window, rotation is hitless. A single in-place edit would disconnect every agent simultaneously.

2. **Same generator as gen-nats-accounts.sh** — The rotation scripts reuse the same credential generation logic (`rand_pass`, `gen_nkey_pair`) so generated credentials are indistinguishable from firstboot. No new entropy sources needed.

3. **Audit log, not alert** — Rotation events are logged to a file (not NATS — chicken-and-egg if creds just rotated). A downstream log scraper can alert on unexpected rotation events (e.g. midnight rotation without a change window).

4. **Dry-run default** — The coordinator always requires explicit `--force`. This follows the firstboot pattern where `gen-nats-accounts.sh` is interactive/human-driven. Cron-based rotation would add `--force` but only after validating the dry-run output.

5. **SecretsManager rotation is semi-automated** — The master key lives outside the secret store (env var or keyring), so rotation scripts cannot update it without operator input. The script handles the encrypt/decrypt portion; operator updates the keyring.

### Files touched

- `scripts/rotate-nats-creds.sh` — new, NATS password + config rotation
- `scripts/rotate-nkeys.sh` — new, nkey pair rotation
- `scripts/rotate-secrets-manager.sh` — new, SecretsManager re-key
- `scripts/rotate-all.sh` — new, orchestration coordinator

### Out of scope (for follow-up)

- **Automated scheduling via systemd timer** — would be added in a follow-up after rotation scripts are validated manually
- **TLS cert rotation** — covered by existing `scripts/gen-nats-tls.sh`; cert expiry is a separate concern
- **Live NATS nkey rotation on bt-asp-srv** — explicitly excluded from this change (captain direction)
- **StarAgent credential provisioning** — StarAgent receives credentials at deploy time via the dashboard; its rotation is tied to agent redeployment

## QA / Validation

Manual dry-run test plan:

```bash
# Test: dry-run NATS credential rotation
bash scripts/rotate-nats-creds.sh --dry-run
# Expected: prints new passwords + config diff, no files written

# Test: dry-run nkey rotation
bash scripts/rotate-nkeys.sh --dry-run
# Expected: prints new nkey pairs, no files written

# Test: dry-run coordinator
bash scripts/rotate-all.sh --dry-run
# Expected: prints full plan for all three subsystems

# Test: force NATS rotation against a config backup (no live server)
cp nats/creds/fleet-accounts.conf{,.bak}
bash scripts/rotate-nats-creds.sh --force --out /tmp/rotation-test
diff nats/creds/fleet-accounts.conf.bak nats/creds/fleet-accounts.conf
# Expected: passwords differ, structure identical
```

Integration into existing smoke suite (`scripts/smoke-test.sh`) is deferred to a follow-up issue — the scripts depend on `nk` binary and NATS server being available, which the CI container may not have.

## Lessons

1. **Credential rotation is a trust boundary** — the scripts that generate new credentials must themselves be trusted. They should be in the protected `/opt/starship` tree with the same AppArmor/systemd hardening as the agents they serve.
2. **Two-phase rotation is standard practice** — NATS supports multiple user entries per account natively, making hitless rotation straightforward. Other systems (Vault, Kubernetes) use the same add-then-remove pattern.
3. **Dry-run prevents operator error** — a default dry-run mode is cheap insurance against accidental mass-disconnect. Every rotation script should print the before/after diff and exit 0 without `--force`.
4. **SecretsManager master key is the hardest rotation** — because the key lives outside the encrypted store, the operator must manually update it. A follow-up could store the master key in a hardware-backed keystore (systemd-creds, TPM) to allow fully automated rotation.