#!/usr/bin/env bash
# Starship OS — rotate NATS nkey pairs only
# Usage:
#   bash scripts/rotate-nkeys.sh [--dry-run|--force] [--out DIR]
# Default: --dry-run (print what would change, no files written)
#
# Lighter than full rotate-nats-creds.sh: only changes nkey entries,
# leaving passwords untouched.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${STARSHIP_NATS_CREDS:-$REPO_DIR/nats/creds}"
MODE="dry-run"
GRACE=30
AUDIT_LOG="/var/log/starship/rotation-audit.log"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) MODE="dry-run"; shift ;;
    --force)   MODE="force";  shift ;;
    --out)     OUT="$2";      shift 2 ;;
    --grace)   GRACE="$2";    shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--dry-run|--force] [--out DIR] [--grace SECONDS]"
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

find_nk() {
  if command -v nk &>/dev/null; then
    command -v nk
    return
  fi
  for p in "$HOME/go/bin/nk" /root/go/bin/nk /usr/local/bin/nk; do
    [[ -x "$p" ]] && { echo "$p"; return; }
  done
  return 1
}

gen_nkey_pair() {
  local nk_bin
  nk_bin="$(find_nk)" || return 1
  "$nk_bin" -gen user -pubout 2>/dev/null
}

CONF="$OUT/fleet-accounts.conf"
BAK="${OUT}/fleet-accounts.conf.nkey-bak-$(date +%s)"

echo "=== NKEY ROTATION ==="

declare -A NK_PUB NK_SEED
for role in ops edge red blue telem; do
  NK_PUB[$role]=""
  NK_SEED[$role]=""
  if pair=$(gen_nkey_pair); then
    seed=$(echo "$pair" | sed -n '1p')
    pub=$(echo "$pair" | sed -n '2p')
    if [[ "$seed" == S* && "$pub" == U* ]]; then
      NK_SEED[$role]="$seed"
      NK_PUB[$role]="$pub"
      echo "  $role: new pub=$pub"
    fi
  fi
done

if [[ "$MODE" == "dry-run" ]]; then
  echo ""
  echo "  [DRY-RUN] Would update nkey entries in $CONF"
  echo "  [DRY-RUN] Would write new seeds to $OUT/creds/*.nk"
  echo "  [DRY-RUN] Would SIGHUP nats-server"
  echo "  [DRY-RUN] Pass --force to execute."
  exit 0
fi

[[ -f "$CONF" ]] || { echo "ERROR: $CONF not found" >&2; exit 1; }
cp "$CONF" "$BAK"

for role in ops edge red blue telem; do
  if [[ -n "${NK_SEED[$role]:-}" ]]; then
    printf '%s\n' "${NK_SEED[$role]}" > "$OUT/creds/${role}.nk"
    printf '%s\n' "${NK_PUB[$role]}"  > "$OUT/creds/${role}.nk.pub"
    chmod 600 "$OUT/creds/${role}.nk"
    chmod 644 "$OUT/creds/${role}.nk.pub"
  fi
done

# Update nkey lines in config (replace existing nkey entries)
# This modifies the conf file in-place rather than regenerating from template,
# preserving existing passwords.
for role in ops edge red blue telem; do
  pub="${NK_PUB[$role]:-}"
  if [[ -n "$pub" ]]; then
    # Replace any existing nkey entry for this role's user entry
    sed -i "/${role}\"/,/]/ {
      s|nkey: \"[^\"]*\"|nkey: \"${pub}\"|
    }" "$CONF" 2>/dev/null || true
  fi
done
chmod 600 "$CONF"

NATS_PID=$(pgrep -x nats-server 2>/dev/null || true)
if [[ -n "$NATS_PID" ]]; then
  kill -HUP "$NATS_PID" 2>/dev/null || true
  echo "  SIGHUP nats-server sent"
fi

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "$ts  NKEY ROTATION OK: nkey pairs rotated (backup=$BAK)" >> "$AUDIT_LOG" 2>/dev/null || true

echo ""
echo "=== Summary ==="
echo "  Nkey files: $OUT/creds/*.nk"
echo "  Config:     $CONF"
echo "  Backup:     $BAK"