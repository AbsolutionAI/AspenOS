# ASP-574: CI gate for Dev-only package isolation (H-019)

## Problem

ADR-0008 defines three package tiers (Core / Plugin / Dev-only) and PACKAGES.md is the
single source of truth, but nothing enforced that Dev-only tooling from the `aspen-dev/`
tree never leaks into production packaging surfaces (Debian packages, ISO images,
Dockerfiles). Threat-model item H-019 (severity 6.0) had the check pattern prescribed
(`scripts/check-no-devonly-in-prod.sh`) but no file existed in the tree — a previous
attempt (ASP-567) was false-done.

## Solution

A fail-closed gate script `scripts/check-no-devonly-in-prod.sh`:

1. **Parses `docs/PACKAGES.md`** — requires the `## Dev-only Examples` section and extracts
   every `- <identifier>` bullet (e.g. `aspen-package-mesh`, `compound-engineering-gate-tools`,
   `gatekeeper/minimal_shim.py`), so PACKAGES.md remains the source of truth for the Dev-only set.
   Missing doc or section ⇒ build fails (cannot establish the set).
2. **Adds a static baseline** for markers not expressible as a plain bullet: `aspen-dev/`
   (the dev-only repo path) plus `grok-build` / `minimal_shim` (non `aspen-` prefixed dev
   tools from the ADR/PACKAGES matrix).
3. **Scans only the production deployment surface** — `debian/`, `iso/`, `packaging/`,
   `systemd/`, plus any `Dockerfile*` anywhere in the tree — using case-insensitive
   fixed-string grep (no regex-escaping surprises), reporting every `file:line` for any hit.
4. **Wired as a CI gate** — `.github/workflows/ci.yml` job `security-devonly-isolation`
   (push + PR) and `scripts/check-nightly.sh` Section 16 (runs via the scheduled nightly workflow).

Deliberately **not** scanning `src/`: `src/python/gatekeeper/minimal_shim.py` is a Dev-only
prototype whose *presence* is still asserted by check-nightly.sh Section 12; the gate guards
the deployment surface, not the source tree.

## Key findings / gotchas

- `grep ... -- -e <pat>` treats the `-e` as a filename; the options must be passed before
  `-- file`. Caught via a negative test that failed to fail.
- In-line regexes containing `[[` inside bash `[[ ... =~ ... ]]` break parsing — hoist the
  regex into a variable first.
- `grep -I` (binary ignore) cleanly skips binaries such as `packaging/windows/staragent.exe`.
- Extracting ids from the PACKAGES.md Dev-only section keeps docs and gate in lockstep;
  a drift (section renamed/missing) fails the build rather than silently weakening the gate.

## Test evidence

| Case | Result |
|------|--------|
| Clean current tree (26 production files) | exit 0, `OK: ... scanned 26/26 files, 6 markers` |
| Planted `aspen-package-mesh` in `debian/DEBIAN/control` + `minimal_shim` in an ISO hook | exit 1, both `file:line` hits reported |
| Planted `aspen-package-mesh` in a Dockerfile | exit 1, `./Dockerfile:2` hit reported |
| `bash -n` on both shell scripts; `pyyaml` parse of both workflows | clean |

## Files

| File | Purpose |
|------|---------|
| `scripts/check-no-devonly-in-prod.sh` | Gate script (H-019 / ADR-0008) |
| `.github/workflows/ci.yml` | New `security-devonly-isolation` job |
| `scripts/check-nightly.sh` | New Section 16: Dev-only package isolation |
| `docs/plans/ASP-574.md` | Plan (mandatory CE plan-first) |

## Future improvements

- Onboard Dev-only markers from package manifests (`pyproject.toml` `classification = "dev-only"`)
  as package-catalog enforcement lands (BEL-164).
- Consider scanning `dist/`/built artifacts as part of release signing instead of the source tree.