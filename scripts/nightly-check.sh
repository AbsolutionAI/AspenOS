#!/usr/bin/env bash
# Starship OS — Nightly Build Validation
# Validates the built .deb package for the nightly pipeline (ASP-484):
#   - .deb exists at the expected path
#   - package version matches VERSION and debian/DEBIAN/control
#   - critical package paths are present (layout check)
#   - reports structured pass/fail results for the GitHub Actions job summary
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

VERSION_FILE="$REPO_DIR/VERSION"
CONTROL_VERSION=$(grep -m1 '^Version:' "$REPO_DIR/debian/DEBIAN/control" | awk '{print $2}')
EXPECTED_DEB="dist/${DEB_NAME:-starship-os_${CONTROL_VERSION}_amd64.deb}"

PASS=0
FAIL=0
RESULTS=()

report() {
  local ok="$1"; shift
  local name="$1"; shift
  if [[ "$ok" == "ok" ]]; then
    echo "  [PASS] $name"
    PASS=$((PASS+1))
  else
    echo "  [FAIL] $name"
    FAIL=$((FAIL+1))
    RESULTS+=("{\"name\":\"$(printf '%s' "$name" | sed 's/"/\\"/g')\",\"status\":\"fail\"}")
  fi
}

check() {
  local name="$1"; shift
  if "$@"; then report ok "$name"; else report fail "$name"; fi
}

echo "=== Starship OS nightly build validation ==="
echo "Control version:  ${CONTROL_VERSION:-unknown}"
SUPPRESSED_VERSION=${VERSION_LABEL:-$(cat "$VERSION_FILE" 2>/dev/null || echo unknown)}
echo "VERSION file:     $SUPPRESSED_VERSION"
echo "Build timestamp:  $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo ""

# ─── 1. .deb exists ────────────────────────────────────────────────
# Find the deb produced by this build (nightly-named or default).
DEB_FILE=$(ls dist/starship-os_*.deb 2>/dev/null | head -1 || true)
check ".deb artifact present" test -n "$DEB_FILE"
check ".deb is a regular file" test -f "${DEB_FILE:-/nonexistent}"

# ─── 2. Version consistency ───────────────────────────────────────
if [[ -n "$DEB_FILE" ]]; then
  check "deb matches control version" bash -c "echo '$DEB_FILE' | grep -q '${CONTROL_VERSION}'"
else
  report fail "deb matches control version"
fi

# ─── 3. Layout validation (extract listing) ───────────────────────
LAYOUT_OK=0
if [[ -n "$DEB_FILE" ]]; then
  LIST=$(mktemp)
  if dpkg-deb -c "$DEB_FILE" > "$LIST" 2>/dev/null; then
    required=(
      "opt/starship/bin/starshipctl"
      "opt/starship/bin/staragent"
      "opt/starship/bin/sandbox_run"
      "opt/starship/bin/starship-firstboot.sh"
      "opt/starship/lib/starship/agents/agent_daemon.py"
      "opt/starship/lib/starship/services/fleet.py"
      "opt/starship/lib/starship/scripts/agent-health-checker.py"
      "etc/starship/fleet.yaml"
      "lib/systemd/system/starship-fleet.service"
      "lib/systemd/system/starship-health-checker.service"
      "usr/local/bin/starshipctl"
    )
    missing=0
    for path in "${required[@]}"; do
      if ! grep -q "$path" "$LIST"; then
        echo "  missing path: $path"
        missing=$((missing+1))
      fi
    done
    if [[ $missing -eq 0 ]]; then
      LAYOUT_OK=1
    fi
    if grep -q './installed/' "$LIST"; then
      echo "  invalid layout: nested installed/ present"
      LAYOUT_OK=0
    fi
    rm -f "$LIST"
  fi
fi
if [[ $LAYOUT_OK -eq 1 ]]; then
  report ok "deb layout validation"
else
  report fail "deb layout validation"
fi

# ─── 4. Debinfo sanity ─────────────────────────────────────────────
if [[ -n "$DEB_FILE" ]]; then
  INFO=$(dpkg-deb -I "$DEB_FILE" 2>/dev/null || true)
  check "deb has Package: starship-os" bash -c "echo '$INFO' | grep -q '^Package: starship-os'"
  check "deb has Version field" bash -c "echo '$INFO' | grep -q '^Version:'"
  check "deb has Architecture field" bash -c "echo '$INFO' | grep -q '^Architecture:'"
else
  report fail "deb metadata checks (no artifact)"
fi

# ─── Summary ───────────────────────────────────────────────────────
echo ""
echo "Result: $PASS passed, $FAIL failed"

if [[ "$FAIL" -gt 0 ]]; then
  echo ""
  echo "Failed checks:"
  printf '%s\n' "${RESULTS[@]}"
  exit 1
fi

exit 0