#!/usr/bin/env bash
# Starship OS - fleet node enrollment protocol (H-002 / ASP-170)
#
# Usage:
#   fleet-enroll.sh issue-token --node NAME [--days N] [--out DIR]
#   fleet-enroll.sh request     --node NAME --token TOKEN [--dir DIR] [--out DIR]
#   fleet-enroll.sh sign        --request DIR [--out DIR]
#   fleet-enroll.sh revoke      --node NAME [--reason TEXT] | --list  [--out DIR]
#
# Enrollment tokens are RSA-SHA256 signed by the fleet CA private key
# (ENROLL-v1:<node>:<expiry_epoch>.<base64 sig>), so only ops managers holding
# ca-key.pem can mint them and anyone holding ca.pem can verify them. The node
# generates its keypair locally (request); the ops manager signs the CSR only
# when the token is valid, unexpired, matches the CSR CN, and the node is not
# on <out>/revocations.list. A rogue node cannot obtain a fleet identity
# without a signed token.
set -euo pipefail

OUT="${STARSHIP_NATS_TLS:-}"
DAYS=825
NODE=""
TOKEN=""
REQDIR=""
REASON="compromised-key"
LIST=0

usage() {
  grep -E '^#   fleet-enroll\.sh' "$0" | sed 's/^# *//'
  exit "${1:-0}"
}

CMD=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --dir) REQDIR="$2"; shift 2 ;;
    --node) NODE="$2"; shift 2 ;;
    --token) TOKEN="$2"; shift 2 ;;
    --request) REQDIR="$2"; shift 2 ;;
    --days) DAYS="$2"; shift 2 ;;
    --reason) REASON="$2"; shift 2 ;;
    --list) LIST=1; shift ;;
    -h|--help) usage 0 ;;
    -*) echo "unknown: $1" >&2; usage 2 >&2 ;;
    *) if [[ -z "$CMD" ]]; then CMD="$1"; else echo "unexpected: $1" >&2; exit 2; fi; shift ;;
  esac
done

if [[ -z "$CMD" ]]; then
  echo "usage: fleet-enroll.sh {issue-token|request|sign|revoke} [options]" >&2
  exit 2
fi

if [[ -z "$OUT" ]]; then
  if [[ "$(id -u)" == "0" ]]; then
    OUT=/etc/starship/nats/tls
  else
    OUT="$(cd "$(dirname "$0")/.." && pwd)/nats/tls"
  fi
fi

command -v openssl >/dev/null || { echo "openssl required" >&2; exit 1; }

REVOCATIONS="$OUT/revocations.list"
VALID_NAME_RE='^[A-Za-z0-9][A-Za-z0-9._-]*$'

die() { echo "error: $*" >&2; exit 1; }

require_ca() {
  [[ -f "$OUT/ca.pem" ]] || die "fleet CA missing in $OUT - run scripts/gen-nats-tls.sh first"
}

check_name() {
  [[ -n "${1:-}" ]] || die "node name required (--node NAME)"
  [[ "$1" =~ $VALID_NAME_RE ]] || die "invalid node name: $1"
}

is_revoked() {
  local name="$1"
  [[ -f "$REVOCATIONS" ]] || return 1
  awk '$1 !~ /^#/ && $1 != "" { print $1 }' "$REVOCATIONS" | grep -qx -- "$name"
}

# Write the canonical token payload for NODE/EXPIRY to FILE.
write_payload() {
  printf 'ENROLL-v1:%s:%s\n' "$1" "$2" > "$3"
}

verify_token() {
  # verify_token TOKEN NAME -> exit 0 iff signature valid AND bound to NAME
  local payload sig_b64 tmpdir tokfile sigfile claimed expiry now
  [[ -n "${1:-}" ]] || die "enrollment token required (--token)"
  payload="${1%%.*}"
  sig_b64="${1##*.}"
  [[ -n "$payload" && -n "$sig_b64" && "$payload" != "$1" ]] \
    || die "malformed enrollment token"
  claimed="$(printf '%s' "$payload" | cut -d: -f2)"
  expiry="$(printf '%s' "$payload" | cut -d: -f3)"
  [[ "$payload" == "ENROLL-v1:$claimed:$expiry" ]] || die "malformed enrollment token"
  check_name "$claimed"
  [[ "$expiry" =~ ^[0-9]+$ ]] || die "malformed enrollment token expiry"
  now="$(date +%s)"
  [[ "$expiry" -ge "$now" ]] || die "enrollment token expired ($(( (now - expiry) / 86400 )) days ago)"

  require_ca
  tmpdir="$(mktemp -d)"; tokfile="$tmpdir/payload"; sigfile="$tmpdir/sig"
  openssl x509 -in "$OUT/ca.pem" -noout -pubkey > "$tmpdir/ca-pub.pem" 2>/dev/null \
    || { rm -rf "$tmpdir"; die "cannot extract fleet CA public key"; }
  write_payload "$claimed" "$expiry" "$tokfile"
  if ! base64 -d <<<"$sig_b64" > "$sigfile" 2>/dev/null; then
    rm -rf "$tmpdir"
    die "malformed enrollment token signature"
  fi
  if ! openssl dgst -sha256 -verify "$tmpdir/ca-pub.pem" -signature "$sigfile" "$tokfile" >/dev/null 2>&1; then
    rm -rf "$tmpdir"
    die "enrollment token signature invalid (not signed by the fleet CA)"
  fi
  rm -rf "$tmpdir"
  if [[ -n "${2:-}" && "$claimed" != "$2" ]]; then
    die "enrollment token is for node '$claimed', not '$2'"
  fi
}

csr_cn() {
  openssl req -in "$1" -noout -subject -nameopt RFC2253 2>/dev/null \
    | grep -o 'CN=[^,]*' | head -1 | cut -d= -f2
}

# ── issue-token: mint a signed enrollment token for one node ────────────

cmd_issue_token() {
  check_name "$NODE"
  require_ca
  [[ -f "$OUT/ca-key.pem" ]] || die "fleet CA key missing in $OUT (needed to sign tokens)"
  is_revoked "$NODE" && die "node '$NODE' is revoked - remove from $REVOCATIONS first"
  local expiry tokfile sigfile sig_b64
  expiry=$(( $(date +%s) + DAYS * 86400 ))
  tokfile="$(mktemp)"; sigfile="$(mktemp)"
  write_payload "$NODE" "$expiry" "$tokfile"
  openssl dgst -sha256 -sign "$OUT/ca-key.pem" -out "$sigfile" "$tokfile" 2>/dev/null
  sig_b64="$(base64 -w0 "$sigfile")"
  rm -f "$tokfile" "$sigfile"
  echo "Enrollment token for '$NODE' (valid ${DAYS}d):"
  echo "ENROLL-v1:$NODE:$expiry.$sig_b64"
}

# ── request: node side - keypair + CSR stay local ───────────────────────

cmd_request() {
  check_name "$NODE"
  local dir="${REQDIR:-$OUT/enroll/$NODE}"
  mkdir -p "$dir"
  chmod 700 "$dir"
  verify_token "$TOKEN" "$NODE"
  openssl req -newkey rsa:4096 -nodes \
    -keyout "$dir/node-$NODE-key.pem" \
    -out "$dir/node-$NODE.csr" \
    -subj "/O=Starship OS/OU=node/CN=$NODE" 2>/dev/null
  chmod 600 "$dir/node-$NODE-key.pem"
  chmod 644 "$dir/node-$NODE.csr"
  printf '%s\n' "$TOKEN" > "$dir/enrollment-token"
  chmod 600 "$dir/enrollment-token"
  echo "enrollment request ready: $dir (ship node-$NODE.csr + enrollment-token to ops;"
  echo "the private key node-$NODE-key.pem never leaves this directory)"
}

# ── sign: ops side - validate token, sign CSR, emit identity ────────────

cmd_sign() {
  [[ -n "$REQDIR" ]] || die "--request DIR required"
  [[ -f "$REQDIR/enrollment-token" ]] || die "no enrollment-token in $REQDIR"
  local csr cert_key token cn base outname
  csr="$(ls "$REQDIR"/*.csr 2>/dev/null | head -1)" || true
  [[ -n "${csr:-}" && -f "$csr" ]] || die "no CSR (*.csr) in $REQDIR"
  token="$(head -1 "$REQDIR/enrollment-token")"
  cn="$(csr_cn "$csr")"
  check_name "$cn"
  verify_token "$token" "$cn"
  is_revoked "$cn" && die "node '$cn' is on the revocation list ($REVOCATIONS) - refusing to sign"
  require_ca
  [[ -f "$OUT/ca-key.pem" ]] || die "fleet CA key missing in $OUT"
  base="node-${cn}"
  openssl x509 -req -in "$csr" -CA "$OUT/ca.pem" -CAkey "$OUT/ca-key.pem" \
    -CAcreateserial -out "$OUT/${base}-cert.pem" -days "$DAYS" -sha256 2>/dev/null
  cat > "$OUT/${base}.env" <<EOF
# Node client identity issued via fleet enrollment (H-002)
STARSHIP_NATS_TLS=1
STARSHIP_NATS_CA=${OUT}/ca.pem
STARSHIP_NATS_CERT=${OUT}/${base}-cert.pem
STARSHIP_NODE_ID=${cn}
EOF
  chmod 644 "$OUT/${base}-cert.pem"
  chmod 600 "$OUT/${base}.env"
  rm -f "$REQDIR/enrollment-token" "$REQDIR"/*.csr
  echo "signed node identity: $OUT/${base}-cert.pem (CN=$cn)"
  echo "ship back: ${base}-cert.pem + ${base}.env (the node keeps its own key)"
}

# ── revoke: manage the fleet revocation list ────────────────────────────

cmd_revoke() {
  require_ca
  touch "$REVOCATIONS"
  chmod 600 "$REVOCATIONS"
  if [[ "$LIST" == "1" ]]; then
    if [[ -s "$REVOCATIONS" ]]; then
      cat "$REVOCATIONS"
    else
      echo "(no revoked nodes)"
    fi
    return 0
  fi
  check_name "$NODE"
  if is_revoked "$NODE"; then
    echo "node '$NODE' already revoked"
    return 0
  fi
  printf '# revoked %s (%s)\n%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$REASON" "$NODE" >> "$REVOCATIONS"
  echo "revoked '$NODE' (added to $REVOCATIONS)"
  echo "enforcement: signing refuses re-issue; fleet daemon drops peer events;" \
    "nats_connect fails closed when the revoked identity connects"
}

case "$CMD" in
  issue-token) cmd_issue_token ;;
  request) cmd_request ;;
  sign) cmd_sign ;;
  revoke) cmd_revoke ;;
  *) echo "unknown command: $CMD" >&2; exit 2 ;;
esac
