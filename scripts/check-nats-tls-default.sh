#!/usr/bin/env bash
# Starship OS — H-024 P0-2 NATS TLS-by-default CI gate
# Asserts the structural contract that ops/edge cells ship with NATS TLS on and
# fail closed. Fails if any of:
#   1. firstboot has no TLS mode resolver (ops/edge do not default to on)
#   2. TLS is not applied after bus selection against active.conf
#      (at least one bus mode is left unreachable)
#   3. the fail-closed guard is missing (required TLS silently degrades to clear)
#   4. mutual TLS is unavailable (gen-nats-tls.sh cannot emit verify: true)
#   5. a hardcoded 'verify: false' survives in shipped NATS conf templates
#
# Usage: bash scripts/check-nats-tls-default.sh [--self-test]
#   STARSHIP_TLS_GATE_ROOT  scan an alternate tree (used by --self-test)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${STARSHIP_TLS_GATE_ROOT:-$REPO_DIR}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

FIRSTBOOT="scripts/starship-firstboot.sh"
TLS_GEN="scripts/gen-nats-tls.sh"
GATE="scripts/check-nats-tls-default.sh"

for f in "$FIRSTBOOT" "$TLS_GEN" "$GATE"; do
  if [[ ! -f "$f" ]]; then
    echo -e "${RED}FAIL${NC} missing required file: $f"
    exit 1
  fi
done

# ─── Structural predicates ─────────────────────────────────────────────
# 1. TLS mode resolver exists and defaults ops/edge to on.
has_resolver() {
  grep -q '_resolve_tls_mode' "$FIRSTBOOT" \
    && grep -qE 'ops\|edge\)[[:space:]]*echo on' "$FIRSTBOOT"
}

# 2. TLS applied after bus selection, bus-agnostically (resolves active.conf).
tls_after_selection() {
  grep -q 'readlink -f /etc/starship/nats/active.conf' "$FIRSTBOOT" \
    && grep -q '_enable_nats_tls' "$FIRSTBOOT"
}

# 3. Fail closed: required-but-unavailable TLS must not silently continue.
fails_closed() {
  grep -q 'STARSHIP_NATS_TLS_BEST_EFFORT' "$FIRSTBOOT" \
    && grep -qE '^[[:space:]]*exit 1' "$FIRSTBOOT"
}

# 4. Mutual TLS reachable through the generator.
supports_mutual() {
  grep -q -- '--mutual' "$TLS_GEN" \
    && grep -q 'verify: true' "$TLS_GEN"
}

# 5. No hardcoded verify:false in shipped NATS conf templates.
conf_templates_clean() {
  ! grep -rnE '^[[:space:]]*verify:[[:space:]]*false' nats/ 2>/dev/null
}

PREDICATES=(
  has_resolver
  tls_after_selection
  fails_closed
  supports_mutual
  conf_templates_clean
)

run_gate() {
  local failed=()
  local p
  for p in "${PREDICATES[@]}"; do
    "$p" || failed+=("$p")
  done
  if [[ ${#failed[@]} -gt 0 ]]; then
    echo -e "${RED}FAIL — NATS TLS-by-default gate${NC}"
    echo "  Violated predicates: ${failed[*]}"
    echo "  H-024 requires ops/edge cells to enable NATS TLS at first boot and to"
    echo "  fail closed when the material cannot be established."
    return 1
  fi
  echo -e "${GREEN}PASS${NC} NATS TLS-by-default gate — ${#PREDICATES[@]} predicates hold"
  return 0
}

# ─── Self-test: mutate a copy, prove every predicate is load-bearing ────
if [[ "${1:-}" == "--self-test" ]]; then
  # Positive control: the untouched copy must pass, or the gate proves nothing.
  if ! run_gate >/dev/null 2>&1; then
    echo -e "${RED}FAIL${NC} self-test: gate rejects the clean tree; predicates are miscalibrated"
    run_gate
    exit 1
  fi
  echo "  self-test: clean copy passes (positive control)"

  FAILS=0
  for p in "${PREDICATES[@]}"; do
    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' RETURN
    mkdir -p "$TMP/scripts" "$TMP/nats"
    cp "$FIRSTBOOT" "$TLS_GEN" "$GATE" "$TMP/scripts/"
    cp nats/*.conf "$TMP/nats/" 2>/dev/null || true

    # Break exactly one predicate, then confirm the gate catches it.
    case "$p" in
      has_resolver)
        sed -i 's/ops|edge) echo on/ops|edge) echo off/' "$TMP/$FIRSTBOOT" ;;
      tls_after_selection)
        sed -i 's|readlink -f /etc/starship/nats/active.conf|cat /dev/null|' "$TMP/$FIRSTBOOT" ;;
      fails_closed)
        sed -i 's/^      exit 1$/      :/' "$TMP/$FIRSTBOOT" ;;
      supports_mutual)
        sed -i 's/verify: true/verify: false/' "$TMP/$TLS_GEN" ;;
      conf_templates_clean)
        printf 'tls {\n  verify: false\n}\n' >> "$TMP/nats/fleet-bus.conf" ;;
    esac

    # Run the gate as a subprocess rooted at the mutated copy: the script cds
    # to its root at startup, so an exported var on a function call is a no-op.
    if bash "$TMP/$GATE" >/dev/null 2>&1; then
      echo -e "${RED}FAIL${NC} self-test: predicate '$p' is NOT load-bearing (mutation went undetected)"
      FAILS=1
    else
      echo "  self-test: '$p' mutation detected"
    fi
    rm -rf "$TMP"
    trap - RETURN
  done

  if [[ "$FAILS" -ne 0 ]]; then
    exit 1
  fi
  echo -e "${GREEN}PASS${NC} self-test: all ${#PREDICATES[@]} predicates are load-bearing"
  exit 0
fi

run_gate