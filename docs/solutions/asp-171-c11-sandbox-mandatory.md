# C11 sandbox_run + policyexec mandatory, fail closed (ASP-171 / H-003)

**Date:** 2026-08-24
**Tickets:** ASP-171 (H-003), ASP-354, ASP-188

## Problem

The Python-native sandbox (`subprocess`-based) and Python policy checker were
the default tool execution paths. The C11 replacements (`sandbox_run` for
sandboxing, `policyexec` for tool policy) existed as optional opt-ins behind
`STARSHIP_SANDBOX_NATIVE=1`. A deployment could silently fall back to the
weaker Python path.

## Solution

1. **`sandbox_run` installed to `/opt/starship/bin`** by `install-daemon.sh`,
   removing the need for `STARSHIP_SANDBOX_NATIVE=1` as an opt-in environment
   variable.
2. **seccomp allowlist in the C11 sandbox** (`HAVE_SECCOMP`, libseccomp) —
   benchmarks confirmed p50 overhead < 2ms vs Python subprocess (ADR 0001 gate).
   Compilation without libseccomp produces a loud warning but still succeeds
   (permissive mode for cross-compilation targets).
3. **`policy_native.py` bridges** Python `check_tool()` calls to the C11
   `policyexec` binary, so both enforcement paths read the same
   `config/policy.default.json`.
4. **Fail-closed behavior** — if the C11 binary is missing or crashes, the
   Python fallback logs a warning and applies the same policy rules rather
   than silently opening the gate.

## Patterns to reuse

1. **Benchmark before flipping defaults.** ADR-0001 established a p50 overhead
   gate (C11 less than 2x Python). Benchmarks confirmed compliance before making
   C11 mandatory. (See `docs/adr/0001-c11-agent-runtime.md` and `scripts/bench-sandbox.sh`.)
2. **Loud warning on missing dep, not silent fallback.** Compilation without
   libseccomp warns prominently rather than quietly dropping the feature.
3. **Python→C11 bridge preserves the same JSON contract.** `policyexec` reads
   the same `config/policy.default.json` as the Python `fleet_policy` module.
   The bridge is just a subprocess call with JSON I/O — no schema translation.

## Verification

- `scripts/bench-sandbox.sh` — C11 p50 under 2ms (ADR gate).
- `tests/test_ops_tool_policy.py` — 51 tests use the real `policyexec` binary.
- `tests/test_native_mandatory.py` — verifies C11 binaries are installed and
  the Python bridge works.

## Remaining

- Windows cross-compilation for `sandbox_run`/`policyexec` is not yet supported
  (no libseccomp on Windows).
