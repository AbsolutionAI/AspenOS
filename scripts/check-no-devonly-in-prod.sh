#!/usr/bin/env bash
# Starship OS — H-019 Dev-only isolation CI gate
# Fails if any Dev-only package / tool / path (ADR-0008, docs/PACKAGES.md)
# is referenced from a production surface (deb staging, ISO content, Docker).
# Usage: bash scripts/check-no-devonly-in-prod.sh [--self-test]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PACKAGES_MD="docs/PACKAGES.md"
if [[ ! -f "$PACKAGES_MD" ]]; then
  echo -e "${RED}FAIL${NC} missing classification source: $PACKAGES_MD"
  exit 1
fi

# ─── 1. Build Dev-only marker pattern from docs/PACKAGES.md ───────────
# Dev-only tokens come from three places:
#  - the classification matrix "Dev-only" row examples
#  - the "## Dev-only Examples" bullet list
#  - ADR-0008 rule 3: the owning tree marker "aspen-dev/"
MARKERS=()

matrix_tokens=$(awk -F'|' '/^\|\s*\*\*Dev-only\*\*/{print $6}' "$PACKAGES_MD")
examples_tokens=$(sed -n '/## Dev-only Examples (internal only)/,/## /p' "$PACKAGES_MD" \
  | grep '^\- ' | sed 's/^\- //; s/ (.*//' | tr -d '`')

for t in $matrix_tokens $examples_tokens; do
  # normalize punctuation-noise, lowercase for case-insensitive match later
  t="$(printf '%s' "$t" | sed 's/[.,:]//g')"
  # drop noise words that are not specific package/tool identifiers
  case "$t" in
    scripts|tools|sandbox|internal|tooling|aspen-dev) continue ;;
  esac
  [[ -n "$t" ]] && MARKERS+=("$t")
done
MARKERS+=("aspen-dev/")

# ─── 2. Production scan roots ──────────────────────────────────────────
# Trees staged by scripts/build-deb.sh / scripts/build-iso.sh, plus every
# Dockerfile under the repo. Build artifacts (dist/, agent/target/) excluded.
PROD_ROOTS=( agents config dashboard debian iso nats packaging scripts services skills souls systemd tray )
SCAN_TARGETS=()
for r in "${PROD_ROOTS[@]}"; do [[ -e "$r" ]] && SCAN_TARGETS+=("$r"); done

# Dockerfiles (repo has none today; protective if added later)
mapfile -t DOCKERFILES < <(find . -path ./.git -prune -o \
  -type f \( -iname 'dockerfile' -o -iname '*.dockerfile' -o -iname '.dockerignore' \) -print 2>/dev/null)
SCAN_TARGETS+=( "${DOCKERFILES[@]}" )

if [[ "${#MARKERS[@]}" -eq 0 ]]; then
  echo -e "${RED}FAIL${NC} no Dev-only markers could be parsed from $PACKAGES_MD"
  exit 1
fi

# ─── 3. Build grep pattern ─────────────────────────────────────────────
PATTERN=""
for m in "${MARKERS[@]}"; do
  p="$(printf '%s' "$m" | sed 's|[][(){}.+*?^$\\/]|\\&|g')"
  [[ -n "$PATTERN" ]] && PATTERN="$PATTERN|"
  PATTERN="$PATTERN$p"
done

# ─── 4. Scan & report ──────────────────────────────────────────────────
if [[ "${1:-}" == "--self-test" ]]; then
  # Plant a temporary Dev-only marker under a scanned root and require a fail.
  PLANT_DIR="$(mktemp -d "$REPO_DIR/skills/.devonly-selftest.XXXXXX")"
  trap 'rm -rf "$PLANT_DIR"' EXIT
  printf '%s\n' "aspen-package-mesh planted for self-test" > "$PLANT_DIR/planted.txt"
  if grep -rniI -E "$PATTERN" "${SCAN_TARGETS[@]}" | grep -v "$PLANT_DIR" \
      | grep -q . 2>/dev/null; then
    echo -e "${RED}FAIL${NC} self-test: unexpected pre-existing Dev-only reference"
    exit 1
  fi
  if grep -rniI -E "$PATTERN" "${SCAN_TARGETS[@]}" | grep -q "$PLANT_DIR"; then
    echo -e "${GREEN}PASS${NC} self-test: planted Dev-only marker detected (gate fails as intended)"
    exit 0
  fi
  echo -e "${RED}FAIL${NC} self-test: planted Dev-only marker was NOT detected"
  exit 1
fi

MATCHES=$(grep -rniI -E "$PATTERN" "${SCAN_TARGETS[@]}" \
    --exclude-dir=.git --exclude-dir=target --exclude-dir=dist 2>/dev/null || true)

if [[ -n "$MATCHES" ]]; then
  echo -e "${RED}FAIL — Dev-only isolation gate${NC}"
  echo "  Dev-only packages / tooling must never appear in production surfaces."
  echo "  Markers (from $PACKAGES_MD / ADR-0008 rule 3): ${MARKERS[*]}"
  echo "  Matching references:"
  printf '%s\n' "$MATCHES" | sed 's/^/    /'
  exit 1
fi

echo -e "${GREEN}PASS${NC} Dev-only isolation gate — no Dev-only references in production surfaces"
exit 0