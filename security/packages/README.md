# StarShip OS — Package Signing (F-014 / ASP-378)

Signed artifacts + update-integrity checks for the StarShip OS `.deb` update
chain. Documented split: **verify** path (shipped + gated now, CI) vs **signing
ceremony** (human, later, production keys). No production key exists yet.

## Verify path (this ticket — CI gate, active)

| Tool | Purpose |
|------|---------|
| `scripts/verify-deb-signature.sh` | `gpgv` detached-signature check against a pinned keyring. Fails on unsigned / tampered / unknown-key. |
| `scripts/sign-deb.sh` | Signing executor: produces `<package>.deb.asc`. Used by tests today, by the ceremony later. |
| `security/packages/starship-release.gpg` | Trust anchor (binary keyring) the verifier defaults to. **Placeholder dev key** — see ceremony. |
| `.github/workflows/ci.yml` `verify-package-signature` | CI job: a PR presenting an unsigned/tampered fixture fails the build. |
| `scripts/check-nightly.sh` Section 21 | Nightly gate asserting the tooling + tests exist and pass. |
| `tests/test_package_signatures.py` | Hermetic fixture suite (throwaway keys in a temp GNUPGHOME — no private key committed). |

### Usage

```bash
# Verify (default keyring = security/packages/starship-release.gpg)
scripts/verify-deb-signature.sh dist/starship-os_2.2.0_amd64.deb

# Verify against a specific keyring
scripts/verify-deb-signature.sh --keyring /path/to/keys.pgp dist/.../.deb

# Enforce verification before install (update chain)
sudo scripts/update.sh --file dist/....deb --verify-signature
```

Exit codes: `0` valid, `1` key not trusted, `2` bad signature / tampered,
`3` environment or missing signature (no `gpgv`, no `.asc`, no keyring).

## Signing ceremony (human, later — NOT executed in this ticket)

When production release signing is stood up, the operator, using a hardware-key
protected identity **off this host**:

```bash
# 1. Export the production public key into the committed trust anchor
#    (replaces the placeholder below):
gpg --export --export-options export-minimal \
    --output security/packages/starship-release.gpg "KEYID"

# 2. Verify its fingerprint loudly and record it (out-of-band):
gpg --list-keys --fingerprint "KEYID"

# 3. Sign each release artifact next to the .deb it will ship with:
scripts/sign-deb.sh --local-user "KEYID" dist/starship-os_X_Y_Z_amd64.deb

# 4. Flip the update chain to enforce:
#    - make scripts/update.sh --verify-signature the required/only path
#      (remove the non-verifying fallback) at release time.
```

Rules for the ceremony:

- The production signing identity **must have an expiring subkey**, an out-of-band
  fingerprint record, and a documented revocation path.
- Never import the production private key onto a CI/agent host.
- `security/packages/starship-release.gpg` is the single trust anchor; treat a
  merge to it as a security-sensitive change (review + dual-human gate).
- Do not commit private key material under any name (tests use throwaway keys
  generated at run time in a temp `GNUPGHOME`).

## Current placeholder trust anchor

`starship-release.gpg` was generated as a **throwaway dev key** to make the
verify path real before the ceremony. Fingerprint:

```
2917 427F AE9E 734C 0EB9  BB9A 269C 56CD 6F61 30CB
```

It is NOT a production key. Destroy warm copies; replace it with the ceremony
output before enforcing signatures in release channels.

## Threat model linkage

`docs/SECURITY_THREAT_MODEL_v2.2.md` CR 3.4 (Software update integrity): TLS
alone does not authenticate artifact origin; the detached signature + pinned
keyring adds a code-signing origin claim and a tamper check at
download/install time (IEC 62443 CR 3.4). Deeper writeup:
`docs/solutions/asp-378-signed-packages.md`.