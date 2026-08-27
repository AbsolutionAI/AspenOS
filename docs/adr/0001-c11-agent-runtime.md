# ADR 0001 — C11 agent runtime feasibility

**Status:** Accepted (spike authorized)  
**Date:** 2026-07-15  
**Deciders:** Starship OS maintainers  
**Related:** `docs/PERFORMANCE_PLAN.md`, `src/c/`, `docs/plans/starship-os-streamline.md`

## Context

Agent runtime, tool sandbox, and healer are currently Python. Hot paths (sandbox fork/exec, policy match, vector search) show measurable overhead under load. The product plan targets a **C11** native stack for:

- `starshipd` — agent loop + NATS client
- `policyexec` — sandbox + policy gate
- `heald` — self-healing watchdog

Inspiration: Slermes architecture (not vendored). Python remains the orchestration/skills/OpenCode bridge layer.

## Decision

1. **Proceed with a C11 sandbox spike** before rewriting the agent loop.
2. **Keep Python agent_daemon** as the control plane through Alpha 2.1.
3. **Native modules ship as optional libraries** loaded via ctypes/cffi or subprocess first; full `starshipd` replacement is Phase 2+.
4. **Security baseline for sandbox:** Linux namespaces (`CLONE_NEWPID`, `CLONE_NEWNS`) + seccomp-bpf allowlist; fail closed when unsupported.
5. **NATS subjects stay dual-prefix** (`starship.*` / `agnetic.*`); C11 code must use the same dual-publish helpers.

## Options considered

| Option | Pros | Cons |
|--------|------|------|
| A. Stay Python-only | Fastest ship | Ceiling on latency/isolation |
| B. C11 full rewrite now | Max performance | High risk; blocks 2.1 packaging |
| **C. Spike sandbox first (chosen)** | De-risks isolation; incremental | Two runtimes temporarily |
| D. Rust for all native | Memory safety | Toolchain + team split; Go already used for CLI |

## Spike scope (authorized)

Minimal compile targets under `src/c/`:

- `sandbox_run` — fork+exec with timeout, stdout/stderr capture, path allowlist env
- Unit test / demo: run `echo hello` and reject `mount`
- Document wall-clock overhead vs Python `subprocess`

**Out of scope for spike:** full agent loop, Ollama client, JetStream consumer.

## Consequences

- Add `gcc`/`clang` + `libseccomp-dev` to build-deps for optional native package.
- ISO `edge` profile may omit C11 binaries; `server`/`ops` include when built.
- Policy JSON remains shared contract between Python and C11.
- If spike fails on WSL/seccomp, fall back to Python sandbox + AppArmor only.

## Success criteria

- [x] `sandbox_run` builds on Ubuntu 24.04
- [x] Allowed command exits 0 with captured stdout
- [x] Denied syscall/path fails closed (non-zero) — `mount` → exit 126
- [x] **Overhead** p50 < 2ms for trivial command **vs Python baseline**
  (`overhead = c11_internal_wall_p50 − py_exec_p50`). Absolute internal
  latency is diagnostic only — it tracks host fork/exec floor and must not
  be the CI gate (ratified ASP-354 / ASP-189 / ASP-389, 2026-08-23).

## Benchmark

Run: `make bench` or `bash scripts/bench-sandbox.sh 200`  
Gate: `ADR_P50_OVERHEAD_MAX` (default `2.0`) on **overhead**, not absolute p50.

### Historical (2026-07-15, N=200, `/bin/echo ok`)

| Metric | p50 (ms) | p95 (ms) | Notes |
|--------|----------|----------|-------|
| **c11_internal_wall** | **~0.51** | ~0.76 | fork+exec inside `sandbox_run` |
| c11_outer_spawn | ~1.13 | ~2.15 | Python spawns sandbox binary |
| py_exec | ~0.51 | ~0.80 | `subprocess.run` argv |
| py_shell | ~0.98 | ~1.55 | shell path (CommandExecutor-like) |

**Verdict (historical host):** overhead p50 ≈ 0.51 − 0.51 = **~0 ms** ≪ 2 ms — criterion met.
Absolute internal p50 happened to also be ≪ 2 ms on that kernel; that coincidence is **not** the gate.
Outer spawn adds ~0.6 ms bootstrap vs bare py_exec; still acceptable for Alpha 2.1 optional path.

### Revalidation (2026-08-23, BT-ASP-SRV, N=300)

Environmental fork/exec floor rose (~2.9 ms bare). Seccomp ≈ +0.46 ms; unprivileged ns soft-fail ≈ 0.
Measured overhead p50 ≈ **+0.51 ms** → PASS under the same ADR overhead gate. See
`docs/solutions/asp-354-c11-sandbox-perf-regression.md`.

## Seccomp (Phase 3)

- Built with `-DHAVE_SECCOMP=1` when `libseccomp` is available
- Child applies BPF allowlist before `exec` (fail closed on load error → exit 125)
- Default deny: `socket`, `mount`, `ptrace`, `reboot`, …
- Disable: `./sandbox_run --no-seccomp -- …`

## Namespaces (Phase 4)

- Best-effort `unshare(CLONE_NEWNS)` + `unshare(CLONE_NEWPID)` before exec
- Soft-fail without `CAP_SYS_ADMIN` (common for non-root agents)
- PID NS re-forks so command is PID 1 in the new namespace
- Disable: `./sandbox_run --no-ns -- …`

## Optional Python bridge

- `agents/sandbox_native.py` — subprocess bridge to `sandbox_run`
- Mandatory by default since H-003: `STARSHIP_SANDBOX_NATIVE=0` opts out (deprecated). Used by `CommandExecutor` in `agents/tools.py`; startup gate `agents/native_check.py` fails closed if the binary is missing.
- Binary discovery: `STARSHIP_SANDBOX_RUN`, `PATH`, `/opt/starship/bin/sandbox_run`, repo spike path

## policyexec (Phase 4)

- Binary: `src/c/policyexec/policyexec`
- Shared JSON: `config/policy.default.json` → `/etc/starship/policy.json`
- CLI: `check-tool` · `check-command` · `run` · `list`
- Role overlay: `--role red-team` (or `STARSHIP_FLEET_ROLES`)
- Python: `agents/policy_native.py` — mandatory by default since H-003 (`STARSHIP_POLICY_NATIVE=0` opts out, deprecated)
- Contract: same deny/allow/blocklist arrays as Python `PolicyManager` / fleet roles

## starshipd / heald (Phase 5 spikes)

- `src/c/starshipd` — dual-prefix subject map + heartbeat loop (`--once` for tests)
- `src/c/heald` — `/proc` liveness probes (logs recoveries; Python healer still CP)
- Full NATS agent loop + auto-restart remain Python until later ADR

## References

- `src/c/README.md`
- `src/c/sandbox_spike/`
- `scripts/bench-sandbox.sh`
- `agents/sandbox_native.py`
- `security/apparmor/agnetic-agent`
