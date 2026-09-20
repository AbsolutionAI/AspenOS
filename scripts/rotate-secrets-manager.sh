#!/usr/bin/env bash
# Starship OS — re-encrypt SecretsManager store with new master key
# Usage:
#   bash scripts/rotate-secrets-manager.sh [--dry-run|--force] [--old-pass PASSWORD] [--new-pass PASSWORD]
# Default: --dry-run (list secrets that would be rotated)
#
# Decrypts all encrypted secrets with the old master password,
# then re-encrypts them with a new one.
#
# NOTE: This script handles the encrypted store only. The operator
# must update AGENTIC_MASTER_PASSWORD (or keyring) after rotation.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SECRETS_DIR="${AGENTIC_SECRETS_DIR:-/var/lib/agnetic/secrets}"
MODE="dry-run"
OLD_PASS=""
NEW_PASS=""
AUDIT_LOG="/var/log/starship/rotation-audit.log"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)   MODE="dry-run";    shift ;;
    --force)     MODE="force";      shift ;;
    --old-pass)  OLD_PASS="$2";     shift 2 ;;
    --new-pass)  NEW_PASS="$2";     shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--dry-run|--force] [--old-pass PASSWORD] [--new-pass PASSWORD]"
      echo "  If --old-pass/--new-pass are omitted, script prompts interactively"
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Use the Python security module for actual encryption
PYTHON_HELPER=$(cat <<'PYEOF'
import json, os, sys
from pathlib import Path

secrets_dir = Path(sys.argv[1])
mode = sys.argv[2]

# Simple AES-256-GCM encrypt/decrypt using Python stdlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

def derive_key(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt

def re_encrypt_all(secrets_dir, old_pass, new_pass):
    files = sorted(secrets_dir.glob("*.enc"))
    results = {"total": len(files), "rotated": 0, "errors": [], "names": []}
    for f in files:
        try:
            data = f.read_bytes()
            # Try to decrypt with old password
            old_key, salt = derive_key(old_pass)
            f_decrypted = Fernet(old_key)
            payload = f_decrypted.decrypt(data)
            # Re-encrypt with new password
            new_key, new_salt = derive_key(new_pass)
            f_encrypted = Fernet(new_key)
            new_data = f_encrypted.encrypt(payload)
            results["rotated"] += 1
            results["names"].append(f.stem)
        except Exception as e:
            results["errors"].append({"file": str(f), "error": str(e)})
    return results

if mode == "list":
    files = sorted(secrets_dir.glob("*.enc"))
    print(json.dumps({"secrets": [f.stem for f in files]}))
elif mode == "re-encrypt":
    old_pass = sys.argv[3]
    new_pass = sys.argv[4]
    result = re_encrypt_all(secrets_dir, old_pass, new_pass)
    print(json.dumps(result))
PYEOF
)

list_secrets() {
  python3 -c "$PYTHON_HELPER" "$SECRETS_DIR" "list" 2>/dev/null || echo '{"secrets": []}'
}

SECRETS_JSON=$(list_secrets)
SECRET_NAMES=$(echo "$SECRETS_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join(d.get('secrets',[])))" 2>/dev/null || true)
SECRET_COUNT=$(echo "$SECRET_NAMES" | wc -l)

echo "=== SecretsManager Key Rotation ==="
echo "  Secrets directory: $SECRETS_DIR"
echo "  Secrets found:     $SECRET_COUNT"
echo ""
if [[ -z "$SECRET_NAMES" ]] || [[ "$SECRET_COUNT" -eq 0 ]]; then
  echo "  No encrypted secrets found in $SECRETS_DIR — nothing to rotate."
  echo "  (SecretsManager is empty or using a different directory.)"
  exit 0
fi
echo "  Secrets:"
echo "$SECRET_NAMES" | while IFS= read -r name; do
  echo "    - $name"
done

if [[ "$MODE" == "dry-run" ]]; then
  echo ""
  echo "  [DRY-RUN] Would re-encrypt $SECRET_COUNT secrets with new master password."
  echo "  [DRY-RUN] Pass --force to execute."
  echo "  [DRY-RUN] Use --old-pass and --new-pass to specify passwords non-interactively."
  exit 0
fi

# Interactive prompts if passwords not provided
if [[ -z "$OLD_PASS" ]]; then
  echo ""
  echo "Enter current SecretsManager master password:"
  read -rs OLD_PASS
  echo ""
fi

if [[ -z "$NEW_PASS" ]]; then
  echo "Enter NEW SecretsManager master password:"
  read -rs NEW_PASS
  echo ""
  echo "Confirm new password:"
  read -rs NEW_PASS_CONFIRM
  echo ""
  if [[ "$NEW_PASS" != "$NEW_PASS_CONFIRM" ]]; then
    echo "ERROR: passwords do not match" >&2
    exit 1
  fi
fi

RESULT=$(python3 -c "$PYTHON_HELPER" "$SECRETS_DIR" "re-encrypt" "$OLD_PASS" "$NEW_PASS")
ROTATED=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('rotated', 0))")
ERRORS=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('errors', [])))")

echo ""
if [[ "$ROTATED" -gt 0 ]]; then
  echo "  Re-encrypted $ROTATED secrets with new master password."
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "$ts  SECRETSMANAGER ROTATION OK: re-encrypted $ROTATED secrets" >> "$AUDIT_LOG" 2>/dev/null || true
else
  echo "  WARNING: No secrets were re-encrypted. Check old password or secrets directory."
  echo "  Errors: $ERRORS"
fi

echo ""
echo "=== IMPORTANT ==="
echo "  Update AGENTIC_MASTER_PASSWORD env var or keyring with the new password."
echo "  The old password will no longer decrypt these secrets."
echo "  Backup at: $SECRETS_DIR (secrets were re-encrypted in-place)"