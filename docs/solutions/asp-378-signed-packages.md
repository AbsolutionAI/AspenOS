# ASP-378: F-014 — Signed packages and update integrity checks

**Status:** READY_FOR_AIDER_QA
**Mode:** IMPLEMENTATION

## Summary

The `.deb` update chain had no cryptographic integrity check: `scripts/update.sh`
installed whatever bytes it downloaded over TLS, and CI had no job that rejected
an unsigned or tampered artifact. This change splits the problem into a **verify
path** that ships and gates now, and a **signing ceremony** that is documented
and held by a human later — no production key is created here, matching the F-014
(LOW) scope.

## Key insight: verify path without a ceremony, ceremony without a verify path

A code-signing scheme has two halves that need not land in the same ticket:

- **Verify (now):** `gpgv` + a pinned binary keyring (`security/packages/
  starship-release.gpg`) checks a detached `.<file>.asc` sidecar before a package
  is allowed to install or pass CI. Fail on unsigned (no `.asc`), fail on
  tampered bytes (`BADSIG`), fail on unknown key (`NO_PUBKEY`) — defaults are
  fail-closed.
- **Ceremony (later, human):** holding real keys. Per-artifact detached GPG
  signature is the mechanism; the operator exports the production public key into
  the committed keyring, signs each release artifact, and flips `update.sh
  --verify-signature` from opt-in to the only path.

The committed keyring deliberately carries a **placeholder dev key** so the whole
verify path is real and testable today; its fingerprint is printed in the README,
and it must be replaced by the ceremony's output before signatures are enforced
in a release channel. Production is never forced to trust the placeholder.

## Why detached GPG over `debsig-verify` / `dpkg-sig`

| Option | Trade-off |
|--------|-----------|
| `debsig-verify` | Policy XML per keyring; verifies inside dpkg but needs policy groups and is fiddly to fixture offline |
| `dpkg-sig` | Rewrites the `.deb` to inject a `_gpgorigin` member — the artifact CI produced is not what ships |
| **`gpgv` detached `.asc`** | Sidecar travels next to the artifact byte-for-byte; no policy XML; `gpgv` uses a fixed keyring with no web-of-trust and no keyring mutation; present on every Ubuntu runner and this host |

## Changes

### New: `scripts/verify-deb-signature.sh`

The gate. `gpgv --status-fd` against a pinned keyring; exit codes `0` good,
`1` untrusted key, `2` bad/tampered, `3` env/missing (no `gpgv`, no `.asc`, no
keyring). Default signature sidecar is `<file>.asc`; default keyring is the
committed `security/packages/starship-release.gpg`.

### New: `scripts/sign-deb.sh`

Ceremony executor. `gpg --detach-sign --armor --local-user KEYID FILE` →
`FILE.asc`. Used by the fixture tests (throwaway keys) today and by the release
human later.

### New: `security/packages/`

- `starship-release.gpg` — committed trust anchor (placeholder dev key;
  fingerprint `2917 427F AE9E 734C 0EB9 BB9A 269C 56CD 6F61 30CB`).
- `README.md` — the verify/ceremony contract, rotation rules, key custody
  (production key never on CI/agent hosts, expiring subkey, revocation path,
  no private material committed).

### `scripts/update.sh`

Opt-in `--verify-signature [KEYRING]` runs the verifier before `dpkg -i` and
refuses unsigned/tampered/unknown-key packages. **Off by default** so today's
unsigned builds keep updating; the README documents flipping it on at ceremony
completion.

### `tests/test_package_signatures.py`

Hermetic fixture suite (throwaway ed25519 keys in a temp `GNUPGHOME`, minimal
real `.deb` via `dpkg-deb`, plain-byte fallback): unsigned rejected, valid
accepted, byte-tamper rejected, wrong-key rejected, missing-signature = exit 3,
trust anchor is a real keyring, update.sh/CI/nightly wiring.

### `.github/workflows/ci.yml`

New `verify-package-signature` job: installs `gnupg2` + `pytest`, runs the suite.
A PR that presents an unsigned or tampered fixture **fails the build**.

### `scripts/check-nightly.sh`

Section 21 gates: verify/sign scripts exist, trust anchor non-empty, ceremony-vs-
verify documented, update.sh wired, CI job present, fixture tests pass.

## Files changed

| File | Change |
|------|--------|
| `scripts/verify-deb-signature.sh` | New: gpgv verify gate (exit 0/1/2/3) |
| `scripts/sign-deb.sh` | New: detached-sign ceremony executor |
| `security/packages/starship-release.gpg` | New: placeholder dev trust anchor |
| `security/packages/README.md` | New: verify vs ceremony contract |
| `scripts/update.sh` | Opt-in `--verify-signature` before install |
| `tests/test_package_signatures.py` | New: hermetic fixture suite |
| `.github/workflows/ci.yml` | New `verify-package-signature` job |
| `scripts/check-nightly.sh` | Section 21 gates |
| `docs/plans/ASP-378.md` | Plan document |

## Verification

```bash
# fixture suite (no live install, no network, no sudo)
python3 -m pytest tests/test_package_signatures.py -v

# syntax
bash -n scripts/verify-deb-signature.sh scripts/sign-deb.sh scripts/update.sh
```

## Non-goals honored

No production key created, no signing ceremony run, no `dpkg -i`/`/etc` changes,
no NATS restart, no money/publish/credential domain.