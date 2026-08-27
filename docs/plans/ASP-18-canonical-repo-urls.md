# Plan: Canonical GitHub repo URLs (ASP-10 finding #4)

**Issue:** [ASP-18](/ASP/issues/ASP-18) — Hourly implementation sweep
**Source:** [ASP-10](/ASP/issues/ASP-10) audit finding #4 (MEDIUM) — old GitHub org URL
**Date:** 2026-08-04

## Problem

The codebase references `https://github.com/andromi-hash/starship-os` (and the
`andromi-hash` org in general) in shipped scripts, systemd units, the dashboard
agent-installer download URL, and live docs. The repo has since moved; both
`andromi-hash/starship-os` and `AbsolutionAI/starship-os` are 301-redirects to
the canonical **`https://github.com/AbsolutionAI/AspenOS`** (verified via GitHub
API / redirect chain, no redirect on the canonical name).

Stale URLs:
- Break the dashboard "Agent Installer" download path (`GITHUB_RELEASES`) on any
  environment where the redirect is not followed or the old org is revoked.
- Mislead contributors/security reporters reading the live README, SECURITY.md,
  and ARCHITECTURE_COMPLETE.md.

## Scope

Update `andromi-hash` → `AbsolutionAI` (and `starship-os` → `AspenOS` repo name)
in **functional/shipped** artifacts and **live** reference docs:

1. `scripts/build-iso.sh` — `--iso-publisher` metadata
2. `src/python/lib/scripts/build-iso.sh` — same (mirror copy)
3. `dashboard/server.py` — `GITHUB_RELEASES` agent-installer base URL
4. `scripts/install-agent-linux.sh` — release download URLs + help text
5. `scripts/deploy-agent.sh` — systemd `Documentation=`
6. `systemd/*.service` + `systemd/*.target` — `Documentation=` lines
7. `scripts/push-ci-workflows.py` + `src/python/lib/scripts/push-ci-workflows.py` — org API refs
8. `README.md` — canonical repo link + lineage links
9. `SECURITY.md` — security-advisory link
10. `docs/ARCHITECTURE_COMPLETE.md` — repository URL

Also fixed (discovered during verification):
- **`dashboard/server.py` — corrupted `handle_skills_marketplace`** (introduced in
  commit `d2fdfe0`): the function body lost its `SKILL_SOURCES` table, query/source
  parsing, and loop scaffolding, leaving orphaned lines that made the whole module
  fail `py_compile`. Restored the full known-good body from `d2fdfe0~1`.
  `python3 -m py_compile` now passes.

Out of scope (historical records, kept as-is):
- `CHANGELOG.md` (historical release log)
- `docs/plans/alpha-2.1-addendum.md`, `docs/plans/starship-os-streamline.md` (archival plan docs)
- `agents/` config YAML `docs`/url fields if any — verify; only update if a live functional URL

## Verification

- `grep -rn "andromi-hash"` returns no hits in the scoped files.
- `bash -n` clean on edited shell scripts; `python3 -m py_compile` on edited py files.
- Working tree otherwise clean.

## Out of scope / escalated

- `deploy/` stale units + ISO `runcmd` dev path → [ASP-17](/ASP/issues/ASP-17) (Architect-owned, blocked).
- `src/python/lib/` duplicate tree drift (older `agnet-os`-named scripts) → note, not restructured here.
- GitHub push auth remains a FOUNDATION follow-up (aspen-owned).

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — All acceptance criteria met. Canonical URL migration completed: `grep -rn "andromi-hash"` returns no hits in code/scripts/packaging paths. Shell scripts `bash -n` clean. Remaining out-of-scope items (deploy/ stale units, src/python/ drift, push auth) tracked separately.
