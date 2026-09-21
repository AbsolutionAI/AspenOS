#!/usr/bin/env bash
# Starship OS — pull Ollama models for selected hardware profile (F-013)
#
# Models are pulled by tag (Ollama 0.32.11 rejects @sha256: pull refs) and then
# verified against config/models-digests.yaml. A mismatch exits FATAL; a model
# with no pin warns in dev mode and fails under STARSHIP_STRICT_DIGESTS=1.
# Digest truth & verification live in scripts/resolve-model-digests.py.
#
# Re-pin with:
#   python3 scripts/resolve-model-digests.py
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROFILES="${STARSHIP_PROFILES_YAML:-$REPO_DIR/config/profiles.yaml}"
MODELS_YAML="${STARSHIP_MODELS_YAML:-$REPO_DIR/config/models.yaml}"
RESOLVER="$REPO_DIR/scripts/resolve-model-digests.py"
PROFILE="${1:-}"

if [[ -z "$PROFILE" ]]; then
  if [[ -f /etc/starship/profile.yaml ]]; then
    PROFILE=$(awk '/^profile:/{print $2; exit}' /etc/starship/profile.yaml)
  elif [[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/starship/profile.yaml" ]]; then
    PROFILE=$(awk '/^profile:/{print $2; exit}' "${XDG_CONFIG_HOME:-$HOME/.config}/starship/profile.yaml")
  else
    bash "$REPO_DIR/scripts/select-profile.sh" >/dev/null
    PROFILE=$(awk '/^profile:/{print $2; exit}' "${XDG_CONFIG_HOME:-$HOME/.config}/starship/profile.yaml" 2>/dev/null || echo server)
    [[ -f /etc/starship/profile.yaml ]] && PROFILE=$(awk '/^profile:/{print $2; exit}' /etc/starship/profile.yaml)
  fi
fi

PROFILE="${PROFILE:-server}"
INCLUDE_OPTIONAL="${STARSHIP_PULL_OPTIONAL:-0}"

if ! command -v ollama &>/dev/null; then
  echo "ERROR: ollama not installed" >&2
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 required" >&2
  exit 1
fi

if [[ ! -f "$RESOLVER" ]]; then
  echo "ERROR: model digest resolver not found: $RESOLVER" >&2
  exit 1
fi

# The resolver reads the same pins file install-models.sh is validating against.
PINS_YAML="${STARSHIP_PINS_YAML:-$REPO_DIR/config/models-digests.yaml}"
export STARSHIP_PINS_YAML="$PINS_YAML"

# Emit "name\tupstream" for every model the profile wants.
mapfile -t PULL_LIST < <(python3 - "$PROFILES" "$MODELS_YAML" "$PROFILE" "$INCLUDE_OPTIONAL" <<'PY'
import sys, yaml
from pathlib import Path
profiles_path, models_path, name, opt = sys.argv[1:5]
profiles = yaml.safe_load(Path(profiles_path).read_text())
models = yaml.safe_load(Path(models_path).read_text())["models"]
p = profiles["profiles"][name]
want = list(p.get("models", {}).get("required", []))
if opt in ("1", "true", "yes"):
    want += list(p.get("models", {}).get("optional", []))
for m in want:
    meta = models.get(m, {})
    print(f"{m}\t{meta.get('upstream', m)}")
PY
)

# Print the pinned digest for a model (empty if the model has no pin).
pinned_digest() {
  local name="$1" upstream="$2" out
  out="$(python3 "$RESOLVER" --digest "$name" 2>/dev/null)" || out=""
  if [[ -z "$out" ]]; then
    out="$(python3 "$RESOLVER" --digest "$upstream" 2>/dev/null)" || out=""
  fi
  printf '%s' "$out"
}

echo "=== Pulling models for profile: $PROFILE ==="
FAILED=0
for entry in "${PULL_LIST[@]}"; do
  alias_name="${entry%%$'\t'*}"
  upstream="${entry#*$'\t'}"
  expected="$(pinned_digest "$alias_name" "$upstream")"

  if [[ -z "$expected" ]]; then
    if [[ "${STARSHIP_STRICT_DIGESTS:-0}" == "1" ]]; then
      echo "FATAL: no digest pin for $alias_name ($upstream) and strict mode is on" >&2
      FAILED=1
      continue
    fi
    echo "→ ollama pull $upstream   (no pin — dev mode, verification skipped)"
  else
    echo "→ ollama pull $upstream   (pinned $expected)"
  fi

  if ! ollama pull "$upstream" >/dev/null 2>&1; then
    echo "WARN: failed to pull $upstream" >&2
    continue
  fi

  if [[ -n "$expected" ]]; then
    if python3 "$RESOLVER" --verify-local "$alias_name" >/dev/null 2>&1; then
      echo "✓ $alias_name digest verified ($expected)"
    else
      echo "FATAL: digest mismatch for $alias_name ($upstream) — expected $expected" >&2
      FAILED=1
    fi
  fi
done

if [[ "$FAILED" -ne 0 ]]; then
  echo "ERROR: one or more models failed digest verification (F-013)" >&2
  exit 1
fi

# Create Eve alias if Modelfile present (the base model was digest-verified
# above; the alias is a local view over the same pinned layers).
MODEFILE="$REPO_DIR/config/models/Eve-V2-Unleashed.Modelfile"
if [[ -f "$MODEFILE" ]]; then
  if ! ollama list 2>/dev/null | grep -qi 'Eve-V2-Unleashed'; then
    echo "→ ollama create Eve-V2-Unleashed"
    ollama create Eve-V2-Unleashed -f "$MODEFILE" || true
  fi
fi

echo "Done. Models:"
ollama list 2>/dev/null || true