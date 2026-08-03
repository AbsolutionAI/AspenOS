#!/usr/bin/env bash
# Starship OS — Update Script
# Downloads and installs a newer starship-os .deb, backs up config, verifies services.
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[UPDATE]${NC} $*"; }
warn() { echo -e "${YELLOW}[UPDATE]${NC} $*"; }
err()  { echo -e "${RED}[UPDATE]${NC} $*" >&2; exit 1; }
info() { echo -e "${BLUE}[UPDATE]${NC} $*"; }

PACKAGE="starship-os"
BACKUP_BASE="/var/lib/starship/updates"
DEB_PATH=""
DEB_URL=""
DRY_RUN=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -f, --file FILE    Path to the new .deb package"
    echo "  -u, --url URL      URL to download the new .deb from"
    echo "  -d, --dry-run      Check versions and show what would happen without installing"
    echo "  -h, --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  sudo $0 --file dist/starship-os_2.2.0_amd64.deb"
    echo "  sudo $0 --url https://example.com/starship-os_2.2.0_amd64.deb"
    exit 0
}

# ─── Parse args ───────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--file)  DEB_PATH="${2:-}"; shift 2 ;;
        -u|--url)   DEB_URL="${2:-}"; shift 2 ;;
        -d|--dry-run) DRY_RUN=true; shift ;;
        -h|--help)  usage ;;
        *)          err "Unknown option: $1" ;;
    esac
done

if [[ -z "$DEB_PATH" && -z "$DEB_URL" ]]; then
    err "Specify a .deb with --file or --url"
fi
if [[ -n "$DEB_PATH" && -n "$DEB_URL" ]]; then
    err "Specify either --file or --url, not both"
fi

# ─── Preflight ────────────────────────────────────────────────────────
if [[ "$(id -u)" != "0" ]]; then
    err "Must run as root. Use: sudo $0"
fi

if ! command -v dpkg &>/dev/null; then
    err "dpkg not found — this updater targets Debian/Ubuntu systems"
fi

# ─── Resolve the new .deb ─────────────────────────────────────────────
if [[ -n "$DEB_URL" ]]; then
    mkdir -p "$BACKUP_BASE"
    local_arch="$BACKUP_BASE/starship-os-update-$(date +%Y%m%d-%H%M%S).deb"
    log "Downloading $DEB_URL ..."
    if ! curl -fsSL "$DEB_URL" -o "$local_arch"; then
        err "Failed to download $DEB_URL"
    fi
    DEB_PATH="$local_arch"
fi

if [[ ! -f "$DEB_PATH" ]]; then
    err "Package file not found: $DEB_PATH"
fi
DEB_PATH="$(readlink -f "$DEB_PATH")"

# ─── Compare versions ─────────────────────────────────────────────────
installed="$(dpkg-query -W -f='${Version}' "$PACKAGE" 2>/dev/null || echo none)"
pkg_version="$(dpkg-deb -f "$DEB_PATH" Version 2>/dev/null || echo unknown)"

log "Installed:  $installed"
log "New package: $pkg_version"

if [[ "$installed" != "none" && "$installed" == "$pkg_version" ]]; then
    warn "Installed version ($installed) is already current — nothing to do."
    exit 0
fi

if [[ "$DRY_RUN" == "true" ]]; then
    info "DRY RUN — no changes made. Would install $pkg_version."
    exit 0
fi

# ─── Back up config ───────────────────────────────────────────────────
if [[ -d /etc/starship ]]; then
    backup_dir="$BACKUP_BASE/config-$pkg_version-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    cp -a /etc/starship/. "$backup_dir/"
    log "Config backed up to $backup_dir"
fi

# ─── Install ──────────────────────────────────────────────────────────
log "Installing $DEB_PATH ..."
dpkg -i "$DEB_PATH" || {
    warn "dpkg -i failed — attempting dependency fix (apt-get -f install)"
    if command -v apt-get &>/dev/null; then
        apt-get -f install -y || warn "apt-get -f install also failed — check dpkg status"
    fi
}

# ─── Verify ───────────────────────────────────────────────────────────
new_installed="$(dpkg-query -W -f='${Version}' "$PACKAGE" 2>/dev/null || echo unknown)"
log "Verifying installation ..."
if [[ "$new_installed" == "$pkg_version" ]]; then
    log "Update complete: $new_installed"
else
    warn "Version mismatch after install (installed=$new_installed, expected=$pkg_version)."
    warn "Run: dpkg --audit && dpkg -i $DEB_PATH"
fi

if command -v systemctl &>/dev/null; then
    log "Service status:"
    systemctl --no-pager --no-legend --state=active list-units 'agnetic-*' 2>/dev/null | head -20 || true
fi

echo ""
log "Update finished."
