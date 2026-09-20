#!/usr/bin/env bash
# Starship OS — Package Signature Verifier (F-014 / ASP-378)
# Verifies a .deb (or any artifact) against a pinned PGP keyring using gpgv.
# The verify path is the CI gate: unsigned, tampered, or unknown-key artifacts FAIL.
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    cat <<'EOF'
Usage: verify-deb-signature.sh [--keyring KEYRING] FILE [FILE.asc]

Verifies FILE against the detached PGP signature (default sidecar FILE.asc)
using gpgv and a pinned keyring (default security/packages/starship-release.gpg).

Exit codes:
  0  signature valid and key trusted by the keyring
  1  signature valid but key NOT in the keyring (unknown/untrusted)
  2  signature BAD / file tampered
  3  environment error (gpgv missing, signature missing, keyring missing)
EOF
    exit 0
}

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
KEYRING=""
KEYRING_DEFAULT="$REPO_DIR/security/packages/starship-release.gpg"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --keyring) KEYRING="${2:-}"; shift 2 ;;
        -h|--help) usage ;;
        -*) echo "unknown option: $1" >&2; usage ;;
        *) break ;;
    esac
done

if [[ $# -lt 1 || $# -gt 2 ]]; then
    usage
fi

FILE="$1"
SIG="${2:-$FILE.asc}"
KEYRING="${KEYRING:-$KEYRING_DEFAULT}"

# ─── Environment / arguments ────────────────────────────────────────
if ! command -v gpgv >/dev/null 2>&1; then
    echo -e "${RED}[VERIFY]${NC} gpgv not found — install gnupg2 (e.g. apt-get install gnupg2)" >&2
    exit 3
fi
if [[ ! -f "$FILE" ]]; then
    echo -e "${RED}[VERIFY]${NC} artifact not found: $FILE" >&2
    exit 3
fi
if [[ ! -f "$SIG" ]]; then
    echo -e "${RED}[VERIFY]${NC} missing signature: $SIG (artifact is UNSIGNED)" >&2
    exit 3
fi
if [[ ! -f "$KEYRING" ]]; then
    echo -e "${RED}[VERIFY]${NC} trust anchor keyring not found: $KEYRING" >&2
    exit 3
fi

# ─── Verify (gpgv is the intended tool: fixed keyring, no web-of-trust) ─
STATUS_LOG=$(mktemp)
set +e
gpgv --status-fd 1 --keyring "$KEYRING" "$SIG" "$FILE" >"$STATUS_LOG" 2>&1
GRC=$?
set -e

GOOD=$(grep -c '\[GNUPG:\] GOODSIG' "$STATUS_LOG" 2>/dev/null || true)
VALIDSIG=$(grep -c '\[GNUPG:\] VALIDSIG' "$STATUS_LOG" 2>/dev/null || true)
NO_PUBKEY=$(grep -c '\[GNUPG:\] NO_PUBKEY' "$STATUS_LOG" 2>/dev/null || true)
BADSIG=$(grep -c '\[GNUPG:\] BADSIG' "$STATUS_LOG" 2>/dev/null || true)
rm -f "$STATUS_LOG"

if [[ "$GRC" -eq 0 && "$GOOD" -ge 1 && "$VALIDSIG" -ge 1 ]]; then
    echo -e "${GREEN}[VERIFY]${NC} OK — $(basename "$FILE") signed by a trusted key ($(basename "$KEYRING"))"
    exit 0
fi

if [[ "$NO_PUBKEY" -ge 1 || "$GRC" -eq 1 ]]; then
    echo -e "${RED}[VERIFY]${NC} FAIL — signature present but key NOT trusted by $(basename "$KEYRING")" >&2
    exit 1
fi

if [[ "$BADSIG" -ge 1 || "$GRC" -eq 2 ]]; then
    echo -e "${RED}[VERIFY]${NC} FAIL — BAD signature: $(basename "$FILE") has been tampered with or signed by an unknown key" >&2
    exit 2
fi

echo -e "${RED}[VERIFY]${NC} FAIL — signature verification failed (exit $GRC)" >&2
exit 2