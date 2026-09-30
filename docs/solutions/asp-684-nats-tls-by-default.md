# ASP-684 — NATS TLS by default on ops/edge cells (compound)

**Issue:** ASP-684 · **Control:** H-024 P0-2 · **Sweep:** ASP-701
**Plan:** `docs/plans/ASP-684.md` · **Deployment guide:** `docs/security/H-024-wan-mtls-deployment.md`

## Deliverable

TLS is now on by default for `ops` and `edge` cells, applied through a bus-agnostic path,
with mutual TLS available for WAN and a fail-closed guard so the control cannot silently
degrade to plaintext.

- Gate: `scripts/check-nats-tls-default.sh` (5 predicates, `--self-test` proves each load-bearing)
- Firstboot: `_resolve_tls_mode`, `_enable_nats_tls` (post-bus-selection)
- Generator: `gen-nats-tls.sh --mutual`
- Tests: `tests/test_nats_tls_default.py` (29)
- CI job `security-nats-tls` · nightly Section 23 · threat model §8 item 16 → `[x]`

## What was actually wrong

The ticket read "set `STARSHIP_NATS_TLS=1` in firstboot templates". The capability was
already built and shipped. Turning the flag on would have shipped a control that does
nothing on two of three bus paths.

Concretely, the TLS block lived *inside* `_enable_accounts_bus`. Bus selection routes:

| Profile | Bus | Old TLS block reachable? |
|---|---|---|
| `ops` (generator present) | accounts | yes |
| `ops` (generator absent) | fleet-bus | **no** |
| `edge` | agent-bus | **no** |

So `STARSHIP_NATS_TLS=1` set on an `edge` cell was silently ignored. **A security knob that
lies is more dangerous than a missing one** — it produces operator confidence with zero
encryption. That, not the missing default, is the finding worth remembering.

The fix was structural rather than additive: resolve TLS mode *before* bus selection, then
apply it *after*, resolving `/etc/starship/nats/active.conf`. One path, three bus modes.

## Lessons

### 1. "Enable the flag" and "the flag works" are different tickets

Reading the ticket as a one-line default would have produced a green CI job, a `[x]` in the
threat model, and an unencrypted `edge` fleet. Before flipping a default, trace every
caller of the code the flag gates. The mismatch was only visible by mapping
profile → bus-mode → function.

**Grep:** when a ticket says "enable X", first count how many code paths X is reachable from.

### 2. An idempotency guard can silently swallow a *mode change*

`gen-nats-tls.sh` opened with:

```bash
if [[ -f "$OUT/server-cert.pem" && -f "$OUT/server-key.pem" ]]; then
  echo "TLS already present"; exit 0
fi
```

Correct when "already present" means "already in the requested mode". Once `--mutual`
existed, it was wrong: running `--mutual` against a server-auth cell exited 0, printed a
reassuring message, and changed nothing. The operator's WAN upgrade silently no-ops.

Fixed by comparing the mode on disk against the requested mode, and re-issuing only the
snippet (certs survive — re-issuing config is not key rotation).

**Grep:** idempotency guards keyed on *existence* are wrong once *configuration* varies.
Key on the full desired state, not on "is there anything here".

### 3. A default that fails open is worse than no default

The original generation call ran under `|| true`. Harmless while TLS was opt-in. Once TLS
is the default, `|| true` means: TLS silently unavailable → NATS runs in clear → the
operator believes the H-024 control is active.

Hence fail-closed: required-but-unavailable TLS exits non-zero with a message naming both
the fix and the `STARSHIP_NATS_TLS_BEST_EFFORT=1` commissioning escape.

This is the one behavioural risk in the change and it is deliberate. A commissioning cell
missing `openssl` should fail at first boot, loudly, where a human is present — not at 3am
on a WAN link.

**Grep:** when promoting an optional control to a default, audit every suppression
operator (`|| true`, `2>/dev/null`, `set +e`) guarding it.

### 4. A gate whose self-test asserts the wrong thing proves nothing

First draft of `--self-test` ran the gate and asserted it *failed*. That is backwards —
on a clean tree it should pass — and it "passed" for the wrong reason: the gate reads its
files relative to `cd`, and an env var exported onto a shell *function* call does not
re-run the `cd`. Every mutation went undetected while the self-test reported success.

A self-test that cannot fail is worse than no self-test, because it manufactures the
appearance of verification. Rewritten to copy the tree, mutate one predicate at a time,
and run the gate as a *subprocess* rooted at the copy. Now it also asserts a positive
control (clean copy must pass) so a miscalibrated gate cannot masquerade as a working one.

**Grep:** a test that passes both before and after your change is not a test. Always
include a positive control alongside the mutation.

### 5. Prefer deriving a count over restating it

The ops baseline said 150 checks. I needed 159. Rather than edit the number, derive it:
105 line-start `check` calls + 3 indented + 44 Section 7 loop iterations − 2 conditional-skipped
= 150 on `origin/master`. After: +8 (Section 23) +1 (new script hits the Section 7 loop) = 159.

The 2 conditional-skipped deb checks only reconcile *because* the arithmetic closes. Had
it not, the baseline would have been wrong for an unrelated reason and I would have copied
the error forward. This is the ASP-672 failure mode (a stale count surviving because nobody
re-derived it) avoided by spending two minutes on arithmetic.

Confirmed empirically against the 2026-09-26 nightly record
(`docs/ops/nightly-results-2026-09-26T12-20.md`), which reports **149 passed, 1 failed
(150 total)** on `origin/master` — matching the derivation above. After this change:
`113` column-0 calls + `1` deb + `45` Section 7 iterations = **159**. Note the two indented
deb checks are an `if`/`else`, so exactly one executes; counting both is the easy way to
land on 158 and think the baseline was off by one.

### 6. Assert the resolver, not a reimplementation of it

The TLS-mode matrix has 8 combinations. Tempting to reimplement `_resolve_tls_mode` in
Python and test that. That would pass even if the bash were broken.

The test instead extracts the real function body from `starship-firstboot.sh` and executes
it via `bash -c`. The tests are bound to the shipped implementation, and a rename or
signature change in bash breaks them loudly instead of leaving a green suite testing a
phantom.

**Grep:** when testing logic that lives in another language, never reimplement it in the
test language — extract and execute the original.

## A skip guard that was not a capability check

Worth recording because the shape is easy to re-introduce, and because it masqueraded as
"pre-existing environmental noise" for long enough to block a QA gate.

`tests/test_holographic_ingest.py::test_explicit_db_env_writes_holographic` verifies the
holographic dual-write by importing `MemoryStore` from the Hermes agent tree at
`/home/tech/.hermes/hermes-agent` — an out-of-repo optional dependency. The test guarded
that import like this:

```python
except ModuleNotFoundError as exc:
    if "tools.registry" in str(exc) or "holographic" in str(exc):
        pytest.skip("Hermes holographic plugin not available")
    raise
```

The intent is clearly "skip if the optional plugin isn't here." The implementation is a
**name allowlist**. The moment the missing module was anything other than those two names —
here `ruamel.yaml`, pulled in by the plugin's own YAML backend — the guard stopped matching
and re-raised, turning an ordinary missing-optional-dependency into a hard suite failure.

The rule: an import guard around an *optional* dependency should test the capability
(`except ImportError`), never the identity of the missing symbol. If the module is genuinely
required, import it unguarded and let it fail loudly; if it is optional, any resolution
failure means the same thing.

Two things worth being precise about:

- **The fix did not weaken the test.** `path.exists()` runs before the import, so the
  repo's own dual-write behaviour is still asserted on every host. Only the half that
  cannot be evaluated without an external tree skips. Mutation-checked: breaking the
  dual-write still fails the test rather than skipping it.
- **A green suite is a property of a test, not of the change.** Calling this "pre-existing,
  not mine, do not CE-GATE on it" was locally true and operationally useless — the QA
  harness gates on exit code, which cannot see change attribution. The correct move for a
  red suite that blocks other work is to fix it in the same pass, not to annotate it.

The `nats-server` `skipif` guards in `tests/test_nats_tls_default.py` get this right: they
gate on capability (`shutil.which("nats-server") is None`) and skip. Match that pattern.

## Residual / follow-up

- **Rotation cadence** is not introduced here. Generated material is valid 825 days and
  regeneration is idempotent, so it will not silently rotate a live cell. H-017 (threat
  model §8 item 11) owns NATS credential rotation.
- **`server`/dev profile stays plaintext** on loopback agent-bus by design. If dev ever
  needs to exercise mTLS, that is a profile-level change, not a firstboot default change.
- **The `ruamel` suite failure is fixed**, not deferred. It was pre-existing and environmental
  (external `/home/tech/.hermes/hermes-agent` tree), but a non-zero suite exit is not
  attributable by tooling, so it kept blocking automated QA on this work. The cause was a
  defect in the test's own skip guard — see "A skip guard that was not a capability check"
  below. It now skips cleanly and the suite exits 0.

## Verification

| Check | Result |
|---|---|
| `bash -n` on all 4 touched scripts | pass |
| `check-nats-tls-default.sh` | PASS — 5 predicates |
| `check-nats-tls-default.sh --self-test` | PASS — positive control + all 5 mutations detected |
| `tests/test_nats_tls_default.py` | 29 passed (incl. 3 real `nats-server -t` parses) |
| nightly Section 23 (8 checks, run verbatim) | all PASS |
| `pytest tests/` | 495 passed, 4 skipped, exit 0 (no failures) |
| `tests/test_ci_assertions.py` + `test_nats_secret_modes.py` | 43 passed |
| `.github/workflows/ci.yml` parses | 9 jobs incl. `security-nats-tls` |
| `openssl verify` on generated chain | pass |

## Mutant summary

The gate's 5 predicates were each broken individually against a copied tree and the gate
turned red every time — the control is load-bearing in both directions, not merely
present.