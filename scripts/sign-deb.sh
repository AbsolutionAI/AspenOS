#!/usr/bin/env bash
# Starship OS — Release Artifact Signer (F-014 / ASP-378)
# Creates a detached ASCII-armored PGP signature (<file>.asc) for a .deb or any
# artifact. This is the "ceremony executor": production releases are signed by a
# human with an out-of-band-held key (see security/packages/README.md). The
# fixture tests drive it with throwaway keys so the verify path is provable.
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    cat <<'EOF'
Usage: sign-deb.sh --local-user KEYID FILE [FILE.asc]

Creates a detached ASCII-armored signature for FILE at FILE.asc using gpg.

Options:
  --local-user KEYID   Signing identity to use (key id / email / fingerprint)
  --output SIGFILE     Output signature path (default: FILE.asc)
  -h, --help           Show this help

Examples:
  scripts/sign-deb.sh --local-user 269C56CD6F6130CB dist/starship-os_2.2.0_amd64.deb
  scripts/sign-deb.sh --local-user release@starship.os --output out.asc dist/pkg.deb

Verify with:
  scripts/verify-deb-signature.sh --keyring security/packages/starship-release.gpg FILE
EOF
}

KEYID=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --local-user) KEYID="${2:-}"; shift 2 ;;
        --output)     OUTPUT="${2:-}"; shift 2 ;;
        -h|--help)    usage; exit 0 ;;
        -*) echo "unknown option: $1" >&2; exit 1 ;;
        *) break ;;
    esac
done

if [[ -z "$KEYID" || $# -lt 1 ]]; then
    echo -e "${RED}[SIGN]${NC} --local-user KEYID and a FILE are required" >&2
    usage >&2
    exit 1
fi

FILE="$1"
OUTPUT="${OUTPUT:-$FILE.asc}"

if [[ ! -f "$FILE" ]]; then
    echo -e "${RED}[SIGN]${NC} artifact not found: $FILE" >&2
    exit 1
fi
if ! command -v gpg >/dev/null 2>&1; then
    echo -e "${RED}[SIGN]${NC} gpg not found — install gnupg2 (e.g. apt-get install gnupg2)" >&2
    exit 1
fi

# Interactive pinentry is fine for a human ceremony; batch tests pass a GPG
# agent with the throwaway key pre-imported.
gpg --batch --yes --detach-sign --armor --local-user "$KEYID" \
    --output "$OUTPUT" "$FILE"

echo -e "${GREEN}[SIGN]${NC} $(basename "$FILE") -> $OUTPUT (key $KEYID)"
echo -e "${GREEN}[SIGN]${NC} verify: scripts/verify-deb-signature.sh '$FILE'"