#!/bin/bash
# Setup NATS with auth + JetStream (dev/lab helper).
# Prefer gen-nats-accounts.sh — this wrapper no longer embeds live passwords (H-017).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${NATS_OUT:-$ROOT/nats}"
NATS_URL="${NATS_URL:-nats://127.0.0.1:4222}"

echo "=== Generating accounts conf (no secrets in git) ==="
bash "$ROOT/scripts/gen-nats-accounts.sh" --out "$OUT" --host 127.0.0.1

CONF="$OUT/fleet-accounts.conf"
if [[ ! -f "$CONF" ]]; then
  echo "FAIL: expected $CONF from gen-nats-accounts.sh" >&2
  exit 1
fi

echo "=== Stopping existing NATS ==="
pkill -x nats-server 2>/dev/null || true
sleep 1

echo "=== Starting NATS with auth + JetStream ==="
nats-server -c "$CONF" &
sleep 1

echo "=== Verifying NATS is running ==="
if pgrep -x nats-server >/dev/null; then
  echo "OK"
else
  echo "FAIL" >&2
  exit 1
fi

if [[ -f "$OUT/nats.env" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$OUT/nats.env"; set +a
fi

echo "=== Testing auth (ops creds from nats.env if present) ==="
if command -v nats >/dev/null 2>&1; then
  nats pub --server="$NATS_URL" agnetic.test.hello "test" 2>/dev/null && echo "OK" || echo "FAIL (check nats.env / nkeys)"
else
  echo "SKIP (nats CLI not installed)"
fi

echo "=== Creating JetStream streams (best-effort) ==="
if command -v nats >/dev/null 2>&1; then
  nats str add --server="$NATS_URL" AGENTS --subjects "agnetic.agent.>" --storage file --max-age 72h --max-msgs 1000000 2>/dev/null || true
  nats str add --server="$NATS_URL" TELEMETRY --subjects "agnetic.telemetry.>" --storage file --max-age 24h --max-msgs 500000 2>/dev/null || true
fi

echo "=== Setup complete ==="
echo "Server: $NATS_URL"
echo "Config: $CONF"
echo "Client env: $OUT/nats.env (mode 600; gitignored under nats/creds/)"
echo "Do not commit substituted conf or passwords. Rotate any historically leaked lab tokens."
