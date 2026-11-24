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
- [x] Overhead p50 < 2ms for trivial command (vs Python baseline)

## Benchmark (2026-07-15, N=200, `/bin/echo ok`)

Run: `make bench` or `bash scripts/bench-sandbox.sh 200`

| Metric | p50 (ms) | p95 (ms) | Notes |
|--------|----------|----------|-------|
| **c11_internal_wall** | **~0.51** | ~0.76 | fork+exec inside `sandbox_run` |
| c11_outer_spawn | ~1.13 | ~2.15 | Python spawns sandbox binary |
| py_exec | ~0.51 | ~0.80 | `subprocess.run` argv |
| py_shell | ~0.98 | ~1.55 | shell path (CommandExecutor-like) |

**Verdict:** C11 internal p50 **≪ 2ms** — criterion met on that host. Outer spawn adds ~0.6ms for process bootstrap; still acceptable for Alpha 2.1 optional path.

## Gate retune (ASP-807, 2026-11-24)

The July absolute reading (`c11_internal p50 < 2ms`) is not a stable SLO on the GitHub-hosted `ubuntu-latest` runners that execute the required `smoke` job. Same commit (`faa0ff2`), N=100, `/bin/echo ok`:

| Run | Runner | c11_internal p50 | c11_internal p95 | py_exec p50 | overhead |
|-----|--------|------------------|------------------|-------------|----------|
| [smoke job 138864085830](https://github.com/AbsolutionAI/AspenOS/actions/runs/45512669584) | ubuntu-latest (in-suite, old absolute gate) | 1.723 | 1.756 | 1.385 | 0.338 |
| [bench job 138864085841](https://github.com/AbsolutionAI/AspenOS/actions/runs/45512669757) | ubuntu-latest, AMD EPYC 9V74, kernel 7.0.0-1020-azure | 2.263 | 2.361 | 1.925 | 0.338 |
| [smoke job 138867018133](https://github.com/AbsolutionAI/AspenOS/actions/runs/45513530327) | ubuntu-latest (in-suite, retuned gate, `e912e36`) | 2.436 | 2.543 | 2.078 | 0.358 |

The slow isolated SKU's minimum sample was 2.203ms, so every sample missed an absolute 2ms wall. The retuned in-suite smoke job measured p50 2.436ms (p95 2.543ms) and would have failed that wall too; it passed the new gate. Seccomp accounts for ~0.32ms of the isolated wall (`--no-seccomp` p50 2.011; bare fork+exec p50 1.956, p95 2.032). Stripping seccomp cannot put p95 under 2ms. Warmup and a retry cannot either: the miss is the whole distribution, not a tail.

Overhead versus the same-run Python `subprocess` baseline is 0.338–0.358ms across these runs. That is the ADR criterion ("overhead p50 < 2ms … vs Python baseline"). The smoke gate now fails unless both of these hold:

1. `c11_internal p50 - py_exec p50 < 2ms` (unchanged 2ms overhead budget; measured ~0.35ms, so a sandbox that adds 2ms over echo still fails).
2. `c11_internal p50 < 5ms` absolute ceiling. 5ms is about 2.0× the slower in-suite p95 (2.543ms on the retuned smoke job) and about 2.1× the isolated slow-SKU p95 (2.361ms), and above the control-plane host's historical max (~3.7ms). A doubled wall on the slow SKU still fails. Observed SKU spread cannot.

Host nightly numbers were not used to pick the ceiling. They only confirm the ceiling is above a known slower machine so the required check is not pinned to one Azure SKU.

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
- Enable: `STARSHIP_SANDBOX_NATIVE=1` (used by `CommandExecutor` in `agents/tools.py`)
- Binary discovery: `STARSHIP_SANDBOX_RUN`, `PATH`, `/opt/starship/bin/sandbox_run`, repo spike path

## policyexec (Phase 4)

- Binary: `src/c/policyexec/policyexec`
- Shared JSON: `config/policy.default.json` → `/etc/starship/policy.json`
- CLI: `check-tool` · `check-command` · `run` · `list`
- Role overlay: `--role red-team` (or `STARSHIP_FLEET_ROLES`)
- Python: `agents/policy_native.py` via `STARSHIP_POLICY_NATIVE=1`
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
