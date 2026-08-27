#!/usr/bin/env bash
# Setup NATS with multi-tenant accounts auth + JetStream (H-001 / H-017).
# Generates fresh credentials via gen-nats-accounts.sh — never prints secrets.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# src/python/lib/scripts → prefer monorepo root scripts when present
if [[ -f "$REPO_DIR/../../../../scripts/gen-nats-accounts.sh" ]]; then
  ROOT="$(cd "$REPO_DIR/../../../.." && pwd)"
elif [[ -f "$REPO_DIR/scripts/gen-nats-accounts.sh" ]]; then
  ROOT="$REPO_DIR"
else
  ROOT="$REPO_DIR"
fi
OUT="${STARSHIP_NATS_OUT:-$ROOT/nats}"
HOST="${STARSHIP_NATS_HOST:-[IP_ADDRESS]}"
PORT="${STARSHIP_NATS_PORT:-4222}"
GEN="$ROOT/scripts/gen-nats-accounts.sh"
[[ -f "$GEN" ]] || GEN="/opt/starship/lib/starship/scripts/gen-nats-accounts.sh"

echo "=== Generating multi-tenant NATS accounts (no live secrets in repo) ==="
[[ -f "$GEN" ]] || { echo "missing gen-nats-accounts.sh" >&2; exit 1; }
bash "$GEN" --out "$OUT" --host "$HOST" --port "$PORT"

CONF="$OUT/fleet-accounts.conf"
ENV_FILE="$OUT/nats.env"
[[ -f "$CONF" ]] || { echo "missing generated conf: $CONF" >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || { echo "missing generated env: $ENV_FILE" >&2; exit 1; }

echo "=== Stopping existing NATS ==="
pkill -x nats-server 2>/dev/null || true
sleep 1

echo "=== Starting NATS with accounts conf ==="
nats-server -c "$CONF" &
sleep 1

echo "=== Verifying NATS is running ==="
if pgrep -x nats-server >/dev/null; then
  echo "OK"
else
  echo "FAIL: nats-server did not start" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

NATS_URL="${NATS_URL:-nats://${HOST}:${PORT}}"

echo "=== Testing authenticated pub ==="
if command -v nats >/dev/null 2>&1; then
  if nats pub --server="$NATS_URL" starship.test.hello "test" 2>/dev/null; then
    echo "OK"
  else
    echo "FAIL: authenticated pub rejected" >&2
    exit 1
  fi

  echo "=== Creating JetStream streams (best-effort) ==="
  nats str add --server="$NATS_URL" AGENTS \
    --subjects "starship.agent.>,agnetic.agent.>" \
    --storage file --max-age 72h --max-msgs 1000000 2>/dev/null || true
  nats str add --server="$NATS_URL" TELEMETRY \
    --subjects "starship.telemetry.>,agnetic.telemetry.>" \
    --storage file --max-age 24h --max-msgs 500000 2>/dev/null || true
else
  echo "skip: nats CLI not installed"
fi

echo "=== Setup complete ==="
echo "Server conf: $CONF"
echo "Client env:  $ENV_FILE  (source it; do not commit)"
echo "Mode:        accounts (H-001). Legacy nats/server.conf is placeholder-only (H-017)."
