#!/usr/bin/env bash
# Starship OS — enforce mode 600 on NATS creds & secret paths (ASP-373 / F-009)
#
# Idempotent. Locks NATS secret/config paths to 600 (creds dir 700) and fixes
# ownership so the daemons that legitimately need the files can read them at
# mode 600:
#   - nats.env        -> agnetic:agnetic (fleet/status/dashboard run as agnetic)
#   - nats-token      -> root:root      (only firstboot reads it, as root)
#   - server confs    -> nats:nats      (nats daemon reads active.conf target)
#   - creds/ tls/     -> root:root
#
# Optional single arg: ROOT prefix so tests/fixtures and build-deb staging can
# run the same logic against a scratch dir. Root-only ownership fixes are
# skipped when ROOT is given.
#
# Usage: bash scripts/fix-nats-secret-modes.sh [ROOT]

set -euo pipefail

ROOT="${1:-}"

_lock() {
  # "$1" = absolute or root-prefixed path; chmod 600 if present.
  local fpath="$ROOT$1"
  if [[ -e "$fpath" ]]; then chmod 600 "$fpath"; fi
}

_lock /etc/starship/nats.env
_lock /etc/starship/nats-token
_lock /etc/starship/nats/fleet-accounts.conf
_lock /etc/starship/nats/fleet-bus.active.conf
_lock /etc/starship/nats/server.conf
_lock /etc/starship/nats/tls/client.env

if [[ -d "$ROOT/etc/starship/nats/creds" ]]; then
  chmod 700 "$ROOT/etc/starship/nats/creds"
  find "$ROOT/etc/starship/nats/creds" -type f -exec chmod 600 {} +
fi

if [[ -d "$ROOT/etc/starship/nats/tls" ]]; then
  chmod 700 "$ROOT/etc/starship/nats/tls"
  find "$ROOT/etc/starship/nats/tls" -type f -name '*-key.pem' -exec chmod 600 {} +
fi

if [[ -z "$ROOT" ]]; then
  if command -v id >/dev/null 2>&1 && [[ "$(id -u)" == "0" ]]; then
    chown agnetic:agnetic /etc/starship/nats.env 2>/dev/null || true
    chown root:root /etc/starship/nats-token 2>/dev/null || true
    chown nats:nats /etc/starship/nats/fleet-accounts.conf \
      /etc/starship/nats/fleet-bus.active.conf \
      /etc/starship/nats/server.conf 2>/dev/null || true
  fi
fi