#!/usr/bin/env bash
# Aspen OS — Apply AUDITOR_BASELINE SSH+UFW hardening (ASP-370 / H-HOST-01).
#
# Default mode is --dry-run: prints the planned ruleset + an evidence template
# and touches NOTHING. --apply requires root (sudo) and refuses unless every
# lockout-allowlist port is present in the planned ruleset.
#
# It NEVER runs `ufw enable` or restarts sshd itself; those two commands are
# printed as the human's final sudo steps (lockout-safe).
#
# Usage:
#   ./apply-auditor-baseline.sh                # dry-run (default)
#   sudo ./apply-auditor-baseline.sh --apply   # apply (gated)
set -euo pipefail

# ─── Lockout allowlist (MUST stay reachable) ────────────────────────────────
# Format "<proto> <port> <udp|tcp> <desc>". The --apply gate fails unless every
# tcp allowlisted port appears in the planned UFW ruleset below.
ALLOWLIST=(
  "tcp 22     SSH (pubkey only)"
  "tcp 443    nginx (Matrix/frozen)"
  "tcp 3100   Paperclip on Tailscale"
  "tcp 8788   Hermes dashboard"
  "tcp 3000   Buzz on Tailscale"
)
TAILSCALE_CIDR="100.64.0.0/10"
TAILSCALE_IF="tailscale0"

SSHD_DROPIN="/etc/ssh/sshd_config.d/99-aspen-baseline.conf"
MODE="dry-run"
FORCE=0

usage() {
    cat <<'EOF'
Usage: apply-auditor-baseline.sh [--apply] [--force]

  (no args)   dry-run: print planned ruleset + evidence template, change nothing
  --apply     require root (sudo); apply SSH drop-in + UFW rules (gated)
  --force     with --apply, allow apply when sshd is not available to validate
              the drop-in (still gated on the allowlist; NOT for firewall apply)

Env:
  ASPEN_SSH_ALLOW_USERS   space-separated user allowlist for sshd AllowUsers
                          (default: $SUDO_USER, else current user)
EOF
}

log()  { echo "[apply-auditor-baseline] $*"; }
err()  { echo "[apply-auditor-baseline] ERROR: $*" >&2; }

parse_args() {
    for a in "$@"; do
        case "$a" in
            --apply) MODE="apply" ;;
            --force) FORCE=1 ;;
            --help|-h) usage; exit 0 ;;
            *) err "unknown argument: $a"; usage >&2; exit 2 ;;
        esac
    done
}

resolve_admin_users() {
    if [[ -n "${ASPEN_SSH_ALLOW_USERS:-}" ]]; then
        # shellcheck disable=SC2086
        printf '%s\n' $ASPEN_SSH_ALLOW_USERS
        return
    fi
    local u="${SUDO_USER:-$USER}"
    [[ -n "$u" ]] && printf '%s\n' "$u" || return 0
}

render_sshd_conf() {
    local users
    users="$(resolve_admin_users | paste -sd' ' -)"
    if [[ -z "$users" ]]; then
        err "no SSH admin user resolved (whoami cannot be empty) — set ASPEN_SSH_ALLOW_USERS"
        return 1
    fi
    cat <<EOF
# Aspen OS security baseline — managed by apply-auditor-baseline.sh (ASP-370)
# Do not edit by hand; regenerate with the apply script.
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
AllowUsers ${users}
EOF
}

# Planned UFW rules (in apply order). First lines are the default policies.
render_ufw_rules() {
    cat <<EOF
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 443/tcp
ufw allow from ${TAILSCALE_CIDR} to any port 3100 proto tcp
ufw allow 8788/tcp
ufw allow from ${TAILSCALE_CIDR} to any port 3000 proto tcp
ufw allow in on ${TAILSCALE_IF}
EOF
}

# Allowlist gate: every allowlisted tcp port must appear in the UFW rules.
# Supports both "N/tcp" (ufw allow 22/tcp) and "port N" (allow from X to any
# port N proto tcp) forms. Returns 0 (pass) or 1 (fail) and prints what is
# missing.
check_allowlist_in_rules() {
    local rules
    rules="$(render_ufw_rules)"
    local missing=0 port proto line found
    for entry in "${ALLOWLIST[@]}"; do
        read -r proto port _desc <<<"$entry"
        if [[ "$proto" != "tcp" ]]; then
            continue
        fi
        found=0
        while IFS= read -r line; do
            [[ -z "$line" ]] && continue
            if [[ "$line" =~ (^|[[:space:]])${port}/tcp([[:space:]]|$) ]] \
               || [[ "$line" =~ (^|[[:space:]])port[[:space:]]+${port}([[:space:]]|$) ]]; then
                found=1
                break
            fi
        done <<<"$rules"
        if [[ "$found" -eq 0 ]]; then
            err "allowlist port ${proto}/${port} missing from planned ruleset — refusing"
            missing=1
        fi
    done
    return "$missing"
}

capture_before_evidence() {
    cat <<EOF
# Before evidence (dry-run, no secrets) — captured $(date -u +%Y-%m-%dT%H:%M:%SZ)
## Current sshd effective config (where readable, no secrets)
$(if command -v sshd >/dev/null 2>&1; then sshd -T 2>/dev/null | grep -Ei '^(permitrootlogin|passwordauthentication|pubkeyauthentication|allowusers|kbdinteractiveauthentication|challengeresponseauthentication) ' || echo "(sshd -T not readable without root)"; else echo "(sshd not present in PATH)"; fi)
## Current UFW status (if any)
$(if command -v ufw >/dev/null 2>&1 && [[ -x /usr/sbin/ufw ]] && /usr/sbin/ufw status 2>/dev/null; then /usr/sbin/ufw status 2>/dev/null || echo "(ufw status requires root)"; else echo "(ufw not present)"; fi)
EOF
}

do_apply() {
    if [[ "${EUID}" -ne 0 ]]; then
        err "localhost root required for --apply; run: sudo $0 --apply"
        exit 1
    fi

    # Safety gate: refuse unless the allowlist is fully represented.
    if ! check_allowlist_in_rules; then
        err "allowlist gate failed — nothing applied. Firewall allowlist and sshd drop-in must not be changed without lockout ports."
        exit 3
    fi

    log "writing sshd drop-in: ${SSHD_DROPIN}"
    mkdir -p "$(dirname "${SSHD_DROPIN}")"
    render_sshd_conf > "${SSHD_DROPIN}"
    chmod 0644 "${SSHD_DROPIN}"

    if command -v sshd >/dev/null 2>&1; then
        if sshd -t -f "${SSHD_DROPIN}" 2>/dev/null; then
            log "sshd config validity: OK ($(grep -c . "${SSHD_DROPIN}") lines)"
        elif [[ "${FORCE}" -eq 1 ]]; then
            log "WARNING: sshd -t validation unavailable/failed — continuing due to --force"
        else
            err "sshd -t validation failed on ${SSHD_DROPIN} — refusing to leave a broken config"
            err "re-run with --force ONLY if you are sure the drop-in is valid"
            exit 4
        fi
    else
        log "sshd not in PATH — skipping live validity check (drop-in written; verify before reload)"
    fi

    log "applying UFW rules (default-deny + allowlist)"
    # Apply safely; on any failure, do NOT continue to the next rule silently.
    while read -r rule; do
        if [[ -z "$rule" ]]; then
            continue
        fi
        log "  ufw ${rule#ufw }"
        ufw ${rule#ufw }
    done < <(render_ufw_rules)

    log "DONE — apply window complete. Human/hardening step, run with sudo:"
    log "  sudo ufw --force enable"
    log "  sudo systemctl reload ssh"
}

main() {
    parse_args "$@"

    log "mode=${MODE}"
    if [[ "$MODE" == "dry-run" ]]; then
        log "dry-run: no changes will be made"
    fi

    echo
    log "planned SSH drop-in (${SSHD_DROPIN}):"
    echo "---"
    render_sshd_conf
    echo "---"
    echo
    log "planned UFW rules:"
    echo "---"
    render_ufw_rules
    echo "---"

    if check_allowlist_in_rules; then
        log "allowlist gate: PASS (all lockout ports present in planned rules)"
    else
        log "allowlist gate: FAIL (see above)"
        if [[ "$MODE" == "apply" ]]; then
            exit 3
        fi
    fi

    if [[ "$MODE" == "dry-run" ]]; then
        echo
        log "=== BEFORE (evidence template, no secrets) ==="
        echo
        capture_before_evidence
        echo
        log "To apply: sudo $0 --apply"
        log "No changes were made."
    else
        do_apply
    fi
}

main "$@"