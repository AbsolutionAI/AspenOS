#!/usr/bin/env bash
# Starship OS — H-020 package classification gate (ADR-0008 rule 4)
#
# ADR-0008 rule 4: "All packages must declare `classification` in
# `pyproject.toml` / `Cargo.toml` / `package.json`." Nothing enforced that
# rule, so a package could ship with no tier at all and PACKAGES.md — the
# declared source of truth for classification — could drift from what the
# package actually declares. This gate closes both gaps.
#
# Companion to scripts/check-no-devonly-in-prod.sh (H-019), which enforces the
# other direction: that Dev-only names never leak into production surfaces.
# A package with no declared tier is invisible to H-019, which is why this
# gate exists separately.
#
# Usage:
#   bash scripts/check-package-classification.sh [--self-test]
#
# Env:
#   PACKAGE_ROOTS   newline/space separated package parent dirs to scan.
#                   Default: plugins. Tests override this to point at a
#                   fixture tree instead of mutating the real plugins/.
#   PACKAGES_MD     path to the classification source of truth.
#                   Default: docs/PACKAGES.md
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PACKAGES_MD="${PACKAGES_MD:-docs/PACKAGES.md}"
if [[ ! -f "$PACKAGES_MD" ]]; then
  echo -e "${RED}FAIL${NC} missing classification source of truth: $PACKAGES_MD"
  exit 1
fi

# Package parent dirs. A subdirectory of one of these counts as a package when
# it holds a supported manifest (see MANIFESTS in the python block below).
read -r -a ROOT_LIST <<<"${PACKAGE_ROOTS:-plugins}"

command -v python3 >/dev/null 2>&1 || {
  echo -e "${RED}FAIL${NC} python3 is required to parse package manifests"
  exit 1
}

# ---------------------------------------------------------------------------
# The gate logic lives in python3 because the manifests are TOML and JSON and
# must be parsed structurally. A grep for "classification" would match a
# dependency named e.g. "classification-utils" or a key nested under
# [project.optional-dependencies], both of which are false passes.
# ---------------------------------------------------------------------------
run_gate() {
  local sor="$1"
  shift
  python3 - "$sor" "$@" <<'PY'
import json
import re
import sys
import tomllib
from pathlib import Path

packages_md = Path(sys.argv[1])
roots = [Path(r) for r in sys.argv[2:]]

VALID = ("core", "plugin", "dev-only")

# ADR-0008 rule 4, verbatim: the manifests it names, plus manifest.json which
# the plugin catalog already uses (plugins/aspen-gatekeeper/manifest.json).
MANIFESTS = ("pyproject.toml", "plugin.json", "package.json", "Cargo.toml", "manifest.json")

# Where `classification` may live inside each manifest.
def declared(root: Path):
    """Return (value, source) for the declared classification, or (None, None)."""
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        data = tomllib.loads(pyproject.read_text())
        value = (data.get("tool", {}).get("aspen", {}) or {}).get("classification")
        if value is not None:
            return value, str(pyproject)
        # Rust packages keep the same key under [package.metadata.aspen].
        cargo = root / "Cargo.toml"
        if cargo.is_file():
            data = tomllib.loads(cargo.read_text())
            value = (
                data.get("package", {}).get("metadata", {}).get("aspen", {}) or {}
            ).get("classification")
            if value is not None:
                return value, str(cargo)
        return None, None

    for name in ("plugin.json", "package.json", "manifest.json"):
        manifest = root / name
        if manifest.is_file():
            data = json.loads(manifest.read_text())
            value = data.get("classification")
            if value is not None:
                return value, str(manifest)
            return None, None

    return None, None


def package_name(root: Path) -> str:
    for name in ("plugin.json", "package.json", "manifest.json"):
        manifest = root / name
        if manifest.is_file():
            value = json.loads(manifest.read_text()).get("name")
            if value:
                return str(value)
    for name in ("pyproject.toml", "Cargo.toml"):
        manifest = root / name
        if manifest.is_file():
            data = tomllib.loads(manifest.read_text())
            value = (data.get("project", {}) or data.get("package", {}) or {}).get("name")
            if value:
                return str(value)
    return root.name


# ── PACKAGES.md expectations ────────────────────────────────────────────
# A tier assertion is a markdown table row whose tier cell is one of VALID,
# read the same way the H-019 gate reads that matrix (its examples cell). Only
# cells *after* the tier cell are scanned for package names, so the tier word
# itself and the tier's prose definition never register as package names.
# Prose mentions outside a tier row are coverage evidence, not tier claims —
# aspen-gatekeeper is described in a "## Plugin: aspen-gatekeeper" body and
# must not be read as a second, competing tier claim.
TIER_CELL = re.compile(
    r"^\|\s*\*{0,2}(" + "|".join(re.escape(v) for v in VALID) + r")\*{0,2}\s*\|",
    re.IGNORECASE,
)
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
# Words that appear in tier cells and must never be treated as package names.
VOCABULARY = {"core", "plugin", "dev", "devonly", "dev-only", "only", "tier", "name"}


def expectations(text: str):
    """Map package name -> set of tiers asserted by PACKAGES.md tier rows."""
    found: dict[str, set] = {}
    mentioned: set[str] = set()
    for line in text.splitlines():
        bare = line.replace("`", "")
        mentioned.update(NAME.findall(bare))
        match = TIER_CELL.match(bare)
        if not match:
            continue
        tier = match.group(1).lower()
        cells = bare.split("|")[2:]  # drop the leading empty field and tier cell
        for name in NAME.findall(" ".join(cells)):
            if name.lower() in VOCABULARY:
                continue
            found.setdefault(name, set()).add(tier)
    return found, mentioned


sor_text = packages_md.read_text()
sor_tiers, sor_mentions = expectations(sor_text)

failures: list[str] = []
packages: list[tuple[str, str, str]] = []

for parent in roots:
    if not parent.is_dir():
        continue
    for root in sorted(p for p in parent.iterdir() if p.is_dir()):
        if not any((root / m).is_file() for m in MANIFESTS):
            continue
        name = package_name(root)
        value, source = declared(root)

        if value is None:
            failures.append(
                f"{root}: no `classification` declared in any of "
                f"{', '.join(MANIFESTS)} (ADR-0008 rule 4)"
            )
            continue
        if not isinstance(value, str) or value.strip().lower() not in VALID:
            failures.append(
                f"{root}: classification {value!r} is not one of {', '.join(VALID)} "
                f"(declared in {source})"
            )
            continue

        tier = value.strip().lower()
        packages.append((str(root), name, tier))

        if name not in sor_mentions:
            failures.append(
                f"{root}: package {name!r} is not mentioned in {packages_md}, "
                f"which is the classification source of truth"
            )
            continue
        asserted = sor_tiers.get(name)
        if asserted and tier not in asserted:
            failures.append(
                f"{root}: declares classification {tier!r} but {packages_md} "
                f"classifies it as {sorted(asserted)}"
            )

if failures:
    print("FAIL — package classification gate (H-020)")
    print("  Every package must declare a valid `classification` (ADR-0008 rule 4)")
    print("  and agree with the classification source of truth.")
    for line in failures:
        print(f"    - {line}")
    sys.exit(1)

for path, name, tier in packages:
    print(f"  {tier:<9} {name}  ({path})")
print(f"PASS — {len(packages)} package(s) declare a classification matching {packages_md}")
PY
}

case "${1:-}" in
  --self-test)
    # Fixtures live outside the repo, so the real plugins/ tree is never
    # mutated and a crashed run leaves nothing behind. A throwaway source of
    # truth is used as well, so the self-test asserts the gate's own parsing
    # and does not depend on what docs/PACKAGES.md happens to say today.
    FIXTURE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/pkgclass-selftest.XXXXXX")"
    trap 'rm -rf "$FIXTURE_ROOT"' EXIT
    mkdir -p "$FIXTURE_ROOT/compliant/compliant-pkg" "$FIXTURE_ROOT/undeclared/undeclared-pkg"
    cat > "$FIXTURE_ROOT/PACKAGES.md" <<'MD'
# Fixture classification matrix

| Tier          | Examples       |
|---------------|----------------|
| **Dev-only** | compliant-pkg |
MD
    cat > "$FIXTURE_ROOT/compliant/compliant-pkg/plugin.json" <<'JSON'
{
  "name": "compliant-pkg",
  "version": "0.0.0",
  "description": "H-020 self-test fixture: declares dev-only and agrees with the source of truth",
  "classification": "dev-only"
}
JSON
    cat > "$FIXTURE_ROOT/undeclared/undeclared-pkg/plugin.json" <<'JSON'
{
  "name": "undeclared-pkg",
  "version": "0.0.0",
  "description": "H-020 self-test fixture: classification deliberately absent"
}
JSON

    # Positive control first: a gate that fails everything would satisfy a
    # detection-only self-test, so prove a compliant package still passes.
    if ! run_gate "$FIXTURE_ROOT/PACKAGES.md" "$FIXTURE_ROOT/compliant" >/dev/null; then
      echo -e "${RED}FAIL${NC} self-test: a compliant package was rejected"
      exit 1
    fi
    echo -e "${GREEN}PASS${NC} self-test: compliant package accepted"

    if run_gate "$FIXTURE_ROOT/PACKAGES.md" "$FIXTURE_ROOT/undeclared" >/dev/null; then
      echo -e "${RED}FAIL${NC} self-test: package with no classification was NOT detected"
      exit 1
    fi
    echo -e "${GREEN}PASS${NC} self-test: missing classification detected (gate would fail)"
    ;;

  "")
    run_gate "$PACKAGES_MD" "${ROOT_LIST[@]}"
    ;;

  *)
    echo "Usage: $0 [--self-test]" >&2
    exit 2
    ;;
esac
