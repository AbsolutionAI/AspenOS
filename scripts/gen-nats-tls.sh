#!/usr/bin/env bash
# Starship OS — generate self-signed TLS material for NATS fleet
# Usage: bash scripts/gen-nats-tls.sh [--out DIR] [--host CN] [--node NAME]
# Writes: ca.pem, server-cert.pem, server-key.pem, client-cert.pem, client-key.pem
#         With --node NAME: node-<NAME>-cert.pem/-key.pem/.env signed by the
#         same fleet CA (per-node mTLS identity, issued by the ops manager).
# H-006 (ASP-174): TLS is enabled by default in new deployments; the generated
# server snippet sets verify:true so clients must present fleet-CA certificates.
set -euo pipefail

OUT="${STARSHIP_NATS_TLS:-}"
HOST="${STARSHIP_NATS_TLS_HOST:-starship-nats.local}"
DAYS=825
NODE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --days) DAYS="$2"; shift 2 ;;
    --node) NODE="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--out DIR] [--host CN] [--days N] [--node NAME]"
      exit 0
      ;;
    *) echo "unknown: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$OUT" ]]; then
  if [[ "$(id -u)" == "0" ]]; then
    OUT=/etc/starship/nats/tls
  else
    OUT="$(cd "$(dirname "$0")/.." && pwd)/nats/tls"
  fi
fi

mkdir -p "$OUT"
chmod 700 "$OUT"

command -v openssl >/dev/null || { echo "openssl required" >&2; exit 1; }

issue_node_cert() {
  # Per-node mTLS identity signed by the fleet CA (ops manager issues these
  # and ships node-<NAME>-*.pem + node-<NAME>.env to the enrolling node).
  local name="$1"
  local base="node-${name}"
  [[ "$name" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "invalid node name: $name" >&2; exit 2; }
  if [[ ! -f "$OUT/ca.pem" || ! -f "$OUT/ca-key.pem" ]]; then
    echo "fleet CA missing in $OUT — run without --node first" >&2
    exit 1
  fi
  openssl req -newkey rsa:2048 -nodes -keyout "$OUT/${base}-key.pem" \
    -out "$OUT/${base}.csr" \
    -subj "/O=Starship OS/OU=node/CN=${name}" 2>/dev/null
  openssl x509 -req -in "$OUT/${base}.csr" -CA "$OUT/ca.pem" -CAkey "$OUT/ca-key.pem" \
    -CAcreateserial -out "$OUT/${base}-cert.pem" -days "$DAYS" -sha256 2>/dev/null
  rm -f "$OUT/${base}.csr"
  chmod 600 "$OUT/${base}-key.pem"
  chmod 644 "$OUT/${base}-cert.pem"
  cat > "$OUT/${base}.env" <<EOF
# Node client identity for mTLS — source before connecting to the fleet bus
STARSHIP_NATS_TLS=1
STARSHIP_NATS_CA=${OUT}/ca.pem
STARSHIP_NATS_CERT=${OUT}/${base}-cert.pem
STARSHIP_NATS_KEY=${OUT}/${base}-key.pem
NATS_URL=tls://${HOST}:4222
EOF
  chmod 600 "$OUT/${base}.env"
  echo "node cert issued: $OUT/${base}-cert.pem (CN=${name}, signed by fleet CA)"
}

if [[ -n "$NODE" ]]; then
  issue_node_cert "$NODE"
  echo "TLS material: $OUT"
  exit 0
fi

if [[ -f "$OUT/server-cert.pem" && -f "$OUT/server-key.pem" && "${STARSHIP_NATS_TLS_FORCE:-}" != "1" ]]; then
  echo "TLS already present in $OUT (set STARSHIP_NATS_TLS_FORCE=1 to regenerate)"
  exit 0
fi

# CA
openssl req -x509 -newkey rsa:4096 -sha256 -days "$DAYS" -nodes \
  -keyout "$OUT/ca-key.pem" -out "$OUT/ca.pem" \
  -subj "/O=Starship OS/CN=Starship Fleet CA" 2>/dev/null

# Server
openssl req -newkey rsa:4096 -nodes -keyout "$OUT/server-key.pem" \
  -out "$OUT/server.csr" \
  -subj "/O=Starship OS/CN=${HOST}" 2>/dev/null
openssl x509 -req -in "$OUT/server.csr" -CA "$OUT/ca.pem" -CAkey "$OUT/ca-key.pem" \
  -CAcreateserial -out "$OUT/server-cert.pem" -days "$DAYS" -sha256 \
  -extfile <(printf "subjectAltName=DNS:%s,DNS:localhost,IP:127.0.0.1" "$HOST") 2>/dev/null

# Ops/admin client identity (per-node identities: --node <NAME>)
openssl req -newkey rsa:4096 -nodes -keyout "$OUT/client-key.pem" \
  -out "$OUT/client.csr" \
  -subj "/O=Starship OS/CN=starship-client" 2>/dev/null
openssl x509 -req -in "$OUT/client.csr" -CA "$OUT/ca.pem" -CAkey "$OUT/ca-key.pem" \
  -CAcreateserial -out "$OUT/client-cert.pem" -days "$DAYS" -sha256 2>/dev/null

rm -f "$OUT/server.csr" "$OUT/client.csr" "$OUT/ca.srl"
chmod 600 "$OUT"/*-key.pem
chmod 644 "$OUT/ca.pem" "$OUT/server-cert.pem" "$OUT/client-cert.pem"
chown -R nats:nats "$OUT" 2>/dev/null || true

# Snippet to append to fleet-accounts / fleet-bus
cat > "$OUT/tls.conf.snippet" <<EOF
# H-006 (ASP-174): mTLS — non-TLS clients are rejected and every client must
# present a certificate signed by this fleet CA (verify: true).
tls {
  cert_file: "${OUT}/server-cert.pem"
  key_file:  "${OUT}/server-key.pem"
  ca_file:   "${OUT}/ca.pem"
  verify: true
  timeout: 5
}
EOF

cat > "$OUT/client.env" <<EOF
# Source for TLS clients (nats-py: tls=... or NATS_URL=tls://)
# Ops/admin client — per-node identities ship as node-<NAME>.env
STARSHIP_NATS_TLS=1
STARSHIP_NATS_CA=${OUT}/ca.pem
STARSHIP_NATS_CERT=${OUT}/client-cert.pem
STARSHIP_NATS_KEY=${OUT}/client-key.pem
NATS_URL=tls://${HOST}:4222
EOF
chmod 600 "$OUT/client.env"

echo "TLS material: $OUT"
echo "  ca.pem server-cert.pem server-key.pem client-*.pem"
echo "  snippet: $OUT/tls.conf.snippet (mTLS: verify:true)"
echo "  client:  $OUT/client.env"
echo "  node identity: bash $0 --out $OUT --node <name>"
