# Learning: Seccomp allowlist drift between branches must be caught by nightly checks

**Ticket:** ASP-478

## Problem

The C11 sandbox (`sandbox_run.c`) on `master` was missing 6 syscalls from its seccomp allowlist that glibc needs on kernel 7.x:

- `sigaltstack` — glibc signal stack setup during `__libc_start_main`
- `prctl` — glibc runtime feature detection (arch_prctl on x86)
- `poll` — glibc I/O multiplexing in stdio initialization
- `sched_getaffinity` — glibc CPU count detection for thread pool sizing
- `get_mempolicy` — glibc NUMA-aware memory allocation
- `landlock_create_ruleset` — glibc Landlock LSM probe (kernel >=6.x, glibc >=2.38)

The fix existed on `hermes/asp-459-packaging-forward-port` but was never forward-ported to `master` when that branch merged. Discovered by ASP-477 nightly check (2026-08-25), which runs `make smoke` on `master` and found C11 sandbox crashing.

## Fix

Cherry-picked the 6-syscall addition plus `ns_warn()` helper from `hermes/asp-459-packaging-forward-port` to `master` (`src/c/sandbox_spike/sandbox_run.c`, 13 insertions, 4 deletions). Also removed an unused `ns_flags` variable and renamed a trace field from `ns` to `ns_req` to avoid implying actual namespace bits were captured.

## Patterns to reuse

- **Nightly allowlist drift checks**: ASP-477's approach of running `make smoke` on master caught this before a release cut.
- **Forward-port checklist**: When merging branches that touch kernel-facing code (seccomp, namespaces, capabilities), verify the allowlists haven't diverged. Use `git diff` on the allowlist portions of sandbox_run.c.
- **Seccomp allowlist hygiene**: Add a build-time assertion or test that enumerates expected syscalls and fails if any are missing. Currently only runtime-tested via sandbox echo + deny tests.