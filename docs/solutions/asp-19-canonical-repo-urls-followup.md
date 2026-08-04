# Compound Learning: URL sweeps must include deb metadata + Go module paths

**Issue:** [ASP-19](/ASP/issues/ASP-19) — Hourly implementation sweep
**Source finding:** [ASP-10](/ASP/issues/ASP-10) #4 (stale org URL)
**Related:** [ASP-18](/ASP/issues/ASP-18) — first canonical-repo-URL sweep
**Date:** 2026-08-04

## Symptom

After [ASP-18](/ASP/issues/ASP-18) rewrote live `andromi-hash/*` references to
`AbsolutionAI/AspenOS`, three **shipped** artifacts still carried the stale org:

- `debian/DEBIAN/control` — `Homepage:` field in the .deb package metadata
- `starshipctl/go.mod` — Go `module` directive
- `starshipctl/main.go` — the self-import of `starshipctl/cmd`

These are exactly the kind of files a `grep -rn "andromi-hash"` surface sweep
walks past: the plan for ASP-18 enumerated a specific file list and did not
include `debian/` or `starshipctl/`.

## Root cause

A **scoped-file-list sweep** (plan enumerates N files, grep verifies only those
files) misses artifacts that are shipped but live outside the enumerated list.
Go module paths and deb `Homepage:` fields are user-visible build/runtime
identity, so a stale org there is not cosmetic: a fresh `go mod tidy` / `go install`
on the old path fails to resolve, and the .deb advertises the wrong project home.

## What fixed it

- Verified the stale refs with `grep -rn "andromi-hash"` and categorized each
  hit as shipped-functional vs archival (CHANGELOG, old plan docs).
- Updated `debian/DEBIAN/control`, `starshipctl/go.mod`, and
  `starshipctl/main.go` to the canonical `github.com/AbsolutionAI/AspenOS` path.
- Confirmed the Go module is self-contained (only `main.go` imports the module
  path; no self-reference in `go.sum`), so the rename is mechanical.

## Pattern / guardrail

1. **For URL/rename sweeps, verify with an *unfiltered* grep and triage every hit
   by category** (shipped-functional vs archival), rather than grepping only the
   plan's enumerated files. Archival exceptions are explicit, not implicit.
2. **Always include `debian/` and Go module files (`go.mod`, `*.go` imports) in
   repo-identity sweeps.** Package metadata and module paths are shipped artifacts.
3. When renaming a Go module path, check `go.sum` for self-references and confirm
   no external consumers import the module path before treating it as mechanical.

## Refs

- Plan: `docs/plans/ASP-19-canonical-repo-urls-followup.md`
- Related: `docs/solutions/asp-18-canonical-repo-urls.md` (original sweep),
  `docs/solutions/asp-16-health-checker-path.md` (path canonicalization pattern)
