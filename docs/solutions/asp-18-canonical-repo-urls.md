# Compound Learning: Canonical repo URLs + dashboard import corruption

**Issue:** [ASP-18](/ASP/issues/ASP-18) — Hourly implementation sweep
**Source finding:** [ASP-10](/ASP/issues/ASP-10) #4 (stale org URL) + incidental bug
**Date:** 2026-08-04

## Symptom

- Shipped scripts, systemd units, and the dashboard pointed at
  `github.com/andromi-hash/starship-os` — an org/repo that has moved.
- `dashboard/server.py` failed `python3 -m py_compile` with `IndentationError`
  at line ~1275, meaning the dashboard service could not even import.

## Root cause

1. **Repo moved:** the canonical location is now
   `github.com/AbsolutionAI/AspenOS`. Both old URLs (`andromi-hash/starship-os`
   and `AbsolutionAI/starship-os`) are 301-redirects to it. `git remote -v` in
   the workspace pointed at `AbsolutionAI/starship-os` — a redirect target, not
   the canonical name.
2. **Silent corruption:** commit `d2fdfe0` (feat: Phases 1A-2D) replaced the
   body of `handle_skills_marketplace()` in `dashboard/server.py` with orphaned
   loop fragments (`items = await resp.json()` under a bare `def`), deleting the
   `SKILL_SOURCES` table, query/source parsing, and `for src in sources:` loop.
   Because the corruption happened inside one function, the module still parsed
   as a file until a strict compile (py_compile / import) — which the build
   pipeline does not run, so it shipped silently.

## What fixed it

- Rewrote all live `andromi-hash/*` references to `AbsolutionAI/AspenOS` in
  build-iso.sh (both copies), dashboard server.py `GITHUB_RELEASES`, agent
  installer script, deploy script, all 8 systemd units' `Documentation=`,
  push-ci-workflows.py (both copies), README, SECURITY, ARCHITECTURE_COMPLETE,
  and shield.js.
- Restored `handle_skills_marketplace()` from the last-known-good commit
  (`d2fdfe0~1`). Verified `python3 -m py_compile` and `ast.parse` pass.

## Pattern / guardrail

1. **Never trust `git remote -v` or README for the canonical URL.** Resolve the
   real repo name via the GitHub API (`/repos/OWNER/NAME`) or the redirect chain
   (`curl -I -L` and follow `location:`). A 200 does not mean canonical.
2. **Shell/Python linting is not enough to catch a corrupted file.** Add a
   compile step (`bash -n` for shell, `py_compile`/`import` for Python) to the
   smoke/build gate so a syntax-broken module fails CI before release. The
   dashboard unit files and server.py are shipped by `scripts/build-deb.sh` and
   `scripts/install-daemon.sh`, so a broken import is a runtime outage, not a
   cosmetic one.

## Refs

- Plan: `docs/plans/ASP-18-canonical-repo-urls.md`
- Related: `docs/solutions/asp-16-health-checker-path.md` (path canonicalization pattern)
