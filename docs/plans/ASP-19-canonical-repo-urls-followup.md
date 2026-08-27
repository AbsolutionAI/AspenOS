# Plan: Canonical repo URLs follow-up (ASP-18 gap)

**Issue:** [ASP-19](/ASP/issues/ASP-19) — Hourly implementation sweep
**Source:** [ASP-10](/ASP/issues/ASP-10) audit finding #4 (MEDIUM) — old GitHub org URL
**Predecessor:** [ASP-18](/ASP/issues/ASP-18) — canonical repo URL sweep
**Date:** 2026-08-04

## Problem

The ASP-18 sweep rewrote live `andromi-hash/*` references to
`https://github.com/AbsolutionAI/AspenOS`, but its scope omitted three
**shipped** artifacts that still point at the stale org:

1. `debian/DEBIAN/control` — `Homepage: https://github.com/andromi-hash/starship-os`
   (this is the `Homepage` field shipped in the .deb package metadata)
2. `starshipctl/go.mod` — `module github.com/andromi-hash/starship-os/starshipctl`
3. `starshipctl/main.go` — `import "github.com/andromi-hash/starship-os/starshipctl/cmd"`

The canonical repo is `https://github.com/AbsolutionAI/AspenOS`. Both old URLs
are 301-redirects (verified in ASP-18). Stale Go module paths break module
resolution for anyone cloning the repo and building `starshipctl` via `go install`
or a fresh `go mod tidy` that tries to re-resolve the self-path.

## Scope

Update to the canonical `github.com/AbsolutionAI/AspenOS` path in:

1. `debian/DEBIAN/control` — `Homepage:` value
2. `starshipctl/go.mod` — `module` directive (repo + module suffix preserved)
3. `starshipctl/main.go` — the single self import of `starshipctl/cmd`

The Go module is self-contained: `main.go` is the only consumer of the module
path, and `go.sum` has no self-reference, so the module-path change is mechanical
and cannot affect dependency resolution.

Out of scope (unchanged, per ASP-18):
- `CHANGELOG.md` (historical release log)
- `docs/plans/alpha-2.1-addendum.md`, `docs/plans/starship-os-streamline.md` (archival)
- `docs/solutions/asp-18-canonical-repo-urls.md` (records the previous sweep)

## Verification

- `grep -rn "andromi-hash"` returns **no** hits outside the explicitly
  out-of-scope historical/archival files.
- `bash -n` clean on any edited shell script (none touched here).
- `python3 -m py_compile` not applicable (no .py touched).
- Go build not runnable in this workspace (no toolchain); the change is a
  string-only module/import rename with no signature or dependency changes.
- Working tree otherwise unchanged.

## Compound

After implementation, record the follow-up gap (ASP-18 left shipped .deb/.go
artifacts stale) in `docs/solutions/` so future URL sweeps include `debian/`
and Go module metadata.

## Disposition

**COMPLETED** (ASP-482 sweep — 2026-08-26) — Follow-up canonical URL fixes completed. Shipped `.deb` and Go module metadata updated. Compound learning recorded at `docs/solutions/asp-19-canonical-repo-urls-followup.md`.
