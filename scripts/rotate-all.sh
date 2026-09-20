#!/usr/bin/env bash
# Starship OS — orchestrated secret rotation coordinator
# Usage:
#   bash scripts/rotate-all.sh [--dry-run|--force] [--nats-only] [--nkeys-only] [--sm-only]
# Default: --dry-run (show full plan, no changes)
#   --force        execute all rotation steps
#   --nats-only    only NATS passwords
#   --nkeys-only   only nkey pairs
#   --sm-only      only SecretsManager master key
#
# Do NOT run against live bt-asp-srv without captain approval.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODE="dry-run"
RUN_NATS=1
RUN_NKEYS=1
RUN_SM=1
AUDIT_LOG="/var/log/starship/rotation-audit.log"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)     MODE="dry-run";    shift ;;
    --force)       MODE="force";      shift ;;
    --nats-only)   RUN_NKEYS=0; RUN_SM=0; shift ;;
    --nkeys-only)  RUN_NATS=0; RUN_SM=0;  shift ;;
    --sm-only)     RUN_NATS=0; RUN_NKEYS=0; shift ;;
    -h|--help)
      echo "Usage: $0 [--dry-run|--force] [--nats-only|--nkeys-only|--sm-only]"
      echo ""
      echo "  Rotates all secret types in dependency order:"
      echo "    1. SecretsManager master key (if --sm-only or all)"
      echo "    2. NATS account passwords  (if --nats-only or all)"
      echo "    3. NATS nkey pairs          (if --nkeys-only or all)"
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

FLAG=""
[[ "$MODE" == "force" ]] && FLAG="--force"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Starship OS — Automated Secret Rotation            ║"
echo "║  Mode: $MODE"
echo "║  $(date -u +%Y-%m-%dT%H:%M:%SZ) UTC"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Step 0: Safety check
if pgrep -x nats-server &>/dev/null; then
  NATS_HOST="$(hostname 2>/dev/null || echo 'unknown')"
  echo "  WARNING: nats-server is running on $NATS_HOST"
  echo "  Rotation will SIGHUP NATS and briefly affect live connections."
  if [[ "$MODE" == "dry-run" ]]; then
    echo "  (Dry-run: no actual changes)"
  fi
  echo ""
fi

# Step 1: SecretsManager key rotation
if [[ "$RUN_SM" -eq 1 ]]; then
  echo "──────────────────────────────────────────────────────"
  echo "  Step 1: SecretsManager master key rotation"
  echo "──────────────────────────────────────────────────────"
  if [[ "$MODE" == "force" ]]; then
    echo "  SecretsManager rotation requires interactive password input."
    echo "  Run 'bash scripts/rotate-secrets-manager.sh --force' separately."
    echo "  (Skipping in coordinator for now — use --sm-only for interactive run)"
    echo "  SKIPPED"
  else
    bash "$REPO_DIR/scripts/rotate-secrets-manager.sh" --dry-run
  fi
  echo ""
fi

# Step 2: NATS credential rotation
if [[ "$RUN_NATS" -eq 1 ]]; then
  echo "──────────────────────────────────────────────────────"
  echo "  Step 2: NATS account password rotation"
  echo "──────────────────────────────────────────────────────"
  bash "$REPO_DIR/scripts/rotate-nats-creds.sh" ${FLAG:---dry-run}
  echo ""
fi

# Step 3: NKEY rotation
if [[ "$RUN_NKEYS" -eq 1 ]]; then
  echo "──────────────────────────────────────────────────────"
  echo "  Step 3: NATS nkey pair rotation"
  echo "──────────────────────────────────────────────────────"
  bash "$REPO_DIR/scripts/rotate-nkeys.sh" ${FLAG:---dry-run}
  echo ""
fi

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Rotation $([[ "$MODE" == "dry-run" ]] && echo "DRY-RUN COMPLETE" || echo "COMPLETE")"
echo "║"
echo "║  Post-rotation actions:"
echo "║  1. Distribute new creds/*.env files to all agents"
echo "║  2. Restart agent processes to pick up new creds"
echo "║     (systemctl restart agnetic-core on each host)"
if [[ "$RUN_SM" -eq 1 ]] && [[ "$MODE" == "force" ]]; then
  echo "║  3. Update AGENTIC_MASTER_PASSWORD on all hosts"
fi
echo "║  4. Verify connectivity: nats pub test"
echo "║"
echo "║  Audit log: $AUDIT_LOG"
echo "╚══════════════════════════════════════════════════════╝"