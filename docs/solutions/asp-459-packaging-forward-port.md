# Learning: Forward-port packaging hygiene onto a long-running feature branch

**Ticket:** ASP-459
**Date:** 2026-08-25

## Problem

The `ox/packaging-hygiene` branch (PR #15) shipped packaging fixes on `master`
— health-checker unit wiring, deploy/ archive, ISO root migration — but the
long-running `hermes/asp-459-packaging-forward-port` branch had diverged
significantly from `master`. It carried 30+ independent change sets (security
H-series, memory API, robotics fleet, dual-human gate, estop range cell, docs
architecture) layered on top of an older `master` baseline.

Forward-porting the packaging hygiene required:
1. Merging `origin/master` into the feature branch (a large merge with broad
   diff context but few actual conflicts).
2. Verifying the packaging changes applied correctly in the forward-port
   context — e.g., the health-checker unit wiring existed on `master` but
   wasn't visible from the feature branch until the merge.
3. Adding worktree-aware and portable-CI support so the branch could be
   developed and tested from `git worktree` checkouts.

## Changes

| Commit | What | Why |
|---|---|---|
| `c0c4990` | Merge `origin/master` into `hermes/asp-459-packaging-forward-port` | Bring packaging hygiene, CI fixes, and architecture docs into the feature branch |
| `48d5b57` | Wire starship-health-checker through deb lifecycle + install-daemon | Forward-port of the master-side fix; adjusted for the feature branch's directory layout |
| `1aacd3b` | Worktree-aware smoke-fleet-bus + portable CARGO detection | The feature branch was developed via `git worktree`; hardcoded paths and pwd assumptions broke |

### Worktree-aware changes (commit `1aacd3b`)

- **Makefile `CARGO`**: Changed from `$(HOME)/.cargo/bin/cargo` to
  `$(shell command -v cargo 2>/dev/null || echo "$(HOME)/.cargo/bin/cargo")`.
  Portable across CI runners, worktrees, and hosts.
- **Makefile `fleet-smoke`**: Added `--repo-root "$$(pwd)"` so the smoke
  script can determine the repo root explicitly rather than via `__file__`
  resolution (which breaks in worktree symlink layouts).
- **`scripts/smoke-fleet-bus.py`**: Added `--repo-root` CLI flag and
  `ASPEN_REPO_ROOT` env var, with argparse docstring. Falls back to the
  original `Path(__file__).resolve().parent` for backward compatibility.

## Reflection

### Forward-port strategy

A large merge (`origin/master` → feature branch) was the right call here:
rebasing 30+ commits onto a moving master would have been error-prone and
lossy. The merge was clean (no semantic conflicts) despite touching 165 files
— most changes were additive or in disjoint paths. The key validation step
was confirming that the packaging hygiene changes from `master` actually
appeared in the merged tree and that any branch-specific adjustments
(like `48d5b57`) were correctly layered on top.

### Worktree compatibility

`git worktree` is a powerful workflow for multi-branch development, but it
exposes assumptions about `__file__` resolution, `$PWD`, and `$HOME`. Three
specific findings:
1. `Path(__file__).resolve()` returns the symlink target in a worktree, not
   the worktree root — scripts that walk `../` from their own location may
   reach the wrong directory.
2. `$(pwd)` / `$(shell pwd)` reflects the shell's working directory, which
   is the worktree root — this is reliable.
3. `command -v` is more portable than hardcoded `$HOME/.cargo/bin/cargo`
   paths, especially across CI environments where `$HOME` varies and the
   toolchain may be installed elsewhere.

### Portable CARGO detection

The original `CARGO := $(HOME)/.cargo/bin/cargo` worked only when rustup
installed cargo in the default location. The forward-port made it portable
by falling back to `command -v cargo`, which resolves through `$PATH` and
works across distributions, CI runners, and container environments. This
pattern should be extended to other toolchain paths (`GO`, `CC`, `PYTHON`).

## Files changed

- `Makefile` — portable CARGO detection, `--repo-root` in fleet-smoke target
- `scripts/smoke-fleet-bus.py` — `--repo-root` CLI flag + `ASPEN_REPO_ROOT` env var

## Related

- PR #15 `ox/packaging-hygiene` — original packaging hygiene change set
- `docs/solutions/ox-packaging-hygiene.md` — packaging hygiene compound learning
- `docs/solutions/asp-190-health-checker-unit-deployment.md` — four-touchpoint systemd wiring
- `docs/solutions/asp-192-deploy-stale-units.md` — deploy/ archive learning
- `docs/solutions/asp-463-ci-assertion-hardening.md` — complementary CI fixes