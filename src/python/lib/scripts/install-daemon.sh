#!/usr/bin/env bash
# Starship OS — Systemd Daemon Installer
# Installs all components to /opt/starship (canonical), creates users, enables services.
# Legacy /opt/starship etc. aliases are symlinked to the canonical root.
# Must run as root.
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INSTALL]${NC} $*"; }
warn() { echo -e "${YELLOW}[INSTALL]${NC} $*"; }
err()  { echo -e "${RED}[INSTALL]${NC} $*" >&2; exit 1; }
info() { echo -e "${BLUE}[INSTALL]${NC} $*"; }

# ─── Pre-flight checks ──────────────────────────────────────────────
if [[ "$(id -u)" != "0" ]]; then
    err "Must run as root. Use: sudo $0"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Starship OS — Daemon Installer     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ─── 1. Create system users ─────────────────────────────────────────
log "Creating system users..."

if ! id -u agnetic &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin \
        --comment "Starship OS Service Account" agnetic
    log "Created user: agnetic"
else
    info "User agnetic already exists"
fi

if ! id -u nats &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin \
        --comment "NATS Message Bus" nats
    log "Created user: nats"
else
    info "User nats already exists"
fi

# ─── 2. Create directory structure ──────────────────────────────────
log "Creating directory structure..."

DIRS=(
    /opt/starship/bin
    /opt/starship/lib/starship
    /opt/starship/lib/starship/agents
    /opt/starship/lib/starship/agents/skills
    /opt/starship/lib/starship/dashboard
    /opt/starship/lib/starship/tray
    /opt/starship/lib/starship/scripts
    /opt/starship/lib/starship/skills
    /opt/starship/lib/starship/souls
    /opt/starship/venv
    /etc/starship
    /etc/starship/nats
    /var/lib/starship
    /var/lib/starship/nats
    /var/lib/starship/message-history
    /var/log/starship
)

for d in "${DIRS[@]}"; do
    mkdir -p "$d"
done
log "Directories created"

# ─── 2b. Legacy aliases (canonical /opt/starship <- /opt/agnetic) ─────
# Mirrors deb postinst / starship-firstboot so systemd units that reference
# /opt/starship work even without firstboot.
ln -sfn /opt/starship /opt/agnetic
ln -sfn /etc/starship /etc/agnetic
ln -sfn /var/lib/starship /var/lib/agnetic
ln -sfn /var/log/starship /var/log/agnetic
# active.conf default if missing
if [[ ! -e /etc/starship/nats/active.conf ]]; then
    ln -sfn /etc/starship/nats/agent-bus.conf /etc/starship/nats/active.conf
fi
log "Legacy aliases created (/opt/agnetic -> /opt/starship, ...)"

# ─── 3. Install binaries ───────────────────────────────────────────
log "Installing binaries..."

# agneticctl CLI
if [[ -f "$REPO_DIR/agneticctl/agneticctl" ]]; then
    cp "$REPO_DIR/agneticctl/agneticctl" /opt/starship/bin/
    chmod 755 /opt/starship/bin/agneticctl
    ln -sf /opt/starship/bin/agneticctl /usr/local/bin/agneticctl
    log "Installed: agneticctl"
else
    warn "agneticctl binary not found — build it first"
fi

# StarAgent
if [[ -f "$REPO_DIR/agent/target/release/staragent" ]]; then
    cp "$REPO_DIR/agent/target/release/staragent" /opt/starship/bin/
    chmod 755 /opt/starship/bin/staragent
    log "Installed: staragent"
else
    warn "staragent binary not found — build it first"
fi

# ─── 4. Install Python application code ─────────────────────────────
log "Installing Python application code..."

# Agent daemon
cp "$REPO_DIR/agents/agent_daemon.py" /opt/starship/lib/starship/agents/
cp "$REPO_DIR/agents/run_agent.sh" /opt/starship/lib/starship/agents/ 2>/dev/null || true
cp "$REPO_DIR/agents/scheduler.py" /opt/starship/lib/starship/agents/ 2>/dev/null || true
cp "$REPO_DIR/agents/workflows.py" /opt/starship/lib/starship/agents/ 2>/dev/null || true
chmod +x /opt/starship/lib/starship/agents/agent_daemon.py
chmod +x /opt/starship/lib/starship/agents/run_agent.sh 2>/dev/null || true

# Dashboard
cp "$REPO_DIR/dashboard/server.py" /opt/starship/lib/starship/dashboard/
cp "$REPO_DIR/dashboard/index.html" /opt/starship/lib/starship/dashboard/
chmod +x /opt/starship/lib/starship/dashboard/server.py

# Status bridge
cp "$REPO_DIR/tray/agnetic-status.py" /opt/starship/lib/starship/tray/
chmod +x /opt/starship/lib/starship/tray/agnetic-status.py

# Scripts
cp "$REPO_DIR/scripts/message_history.py" /opt/starship/lib/starship/scripts/
chmod +x /opt/starship/lib/starship/scripts/message_history.py

# Skills
cp -r "$REPO_DIR/skills/"* /opt/starship/lib/starship/skills/ 2>/dev/null || true

# Souls
cp -r "$REPO_DIR/souls/"* /opt/starship/lib/starship/souls/ 2>/dev/null || true

# Skills (agents subdir)
cp -r "$REPO_DIR/agents/skills/"* /opt/starship/lib/starship/agents/skills/ 2>/dev/null || true

# GPU detection
cp "$REPO_DIR/scripts/detect-gpu.sh" /opt/starship/bin/
chmod +x /opt/starship/bin/detect-gpu.sh

log "Application code installed"

# ─── 5. Install YAML configs ───────────────────────────────────────
log "Installing YAML configs..."

cp "$REPO_DIR/agents/config.yaml" /etc/starship/ 2>/dev/null || true
cp "$REPO_DIR/agents/proxy.yaml" /etc/starship/ 2>/dev/null || true
cp "$REPO_DIR/agents/romi.yaml" /etc/starship/ 2>/dev/null || true
cp "$REPO_DIR/agents/ergo.yaml" /etc/starship/ 2>/dev/null || true
cp "$REPO_DIR/agents/orchestrator.yaml" /etc/starship/ 2>/dev/null || true

log "Configs installed to /etc/starship/"

# ─── 6. Install NATS config ────────────────────────────────────────
log "Installing NATS configuration..."

cp "$REPO_DIR/nats/agent-bus.conf" /etc/starship/nats/
cp "$REPO_DIR/nats/server.conf" /etc/starship/nats/ 2>/dev/null || true
cp "$REPO_DIR/nats/subjects.yaml" /etc/starship/nats/ 2>/dev/null || true

# Update NATS config to use correct paths
sed -i 's|/home/tech/agnetic-os/nats|/etc/starship/nats|g' /etc/starship/nats/agent-bus.conf 2>/dev/null || true

log "NATS config installed to /etc/starship/nats/"

# ─── 7. Create Python venv ─────────────────────────────────────────
log "Creating Python venv..."

python3 -m venv /opt/starship/venv
/opt/starship/venv/bin/pip install --upgrade pip -q
/opt/starship/venv/bin/pip install nats-py aiohttp httpx PyYAML lancedb ollama -q
log "Python venv created with dependencies"

# ─── 8. Install systemd units ──────────────────────────────────────
log "Installing systemd units..."

cp "$REPO_DIR/systemd/agnetic-nats.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/agnetic-staragent.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/agnetic-agent@.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/agnetic-dashboard.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/agnetic-status-bridge.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/agnetic-message-history.service" /etc/systemd/system/
cp "$REPO_DIR/systemd/agnetic-mesh.target" /etc/systemd/system/

systemctl daemon-reload
log "Systemd units installed and daemon reloaded"

# ─── 9. Set ownership ─────────────────────────────────────────────
log "Setting ownership..."

chown -R agnetic:agnetic /opt/starship
chown -R agnetic:agnetic /etc/starship
chown -R agnetic:agnetic /var/lib/starship
chown -R agnetic:agnetic /var/log/starship
chown -R nats:nats /var/lib/starship/nats

log "Ownership set"

# ─── 10. Enable and start services ─────────────────────────────────
log "Enabling services..."

systemctl enable agnetic-nats.service
systemctl enable agnetic-staragent.service
systemctl enable agnetic-agent@proxy.service
systemctl enable agnetic-agent@romi.service
systemctl enable agnetic-agent@ergo.service
systemctl enable agnetic-status-bridge.service
systemctl enable agnetic-message-history.service
systemctl enable agnetic-dashboard.service
systemctl enable agnetic-mesh.target

log "All services enabled"

# ─── 11. Start services ────────────────────────────────────────────
log "Starting services..."

systemctl start agnetic-nats.service
sleep 2
systemctl start agnetic-staragent.service
sleep 1
systemctl start agnetic-agent@proxy.service
systemctl start agnetic-agent@romi.service
systemctl start agnetic-agent@ergo.service
systemctl start agnetic-status-bridge.service
systemctl start agnetic-message-history.service
systemctl start agnetic-dashboard.service

sleep 3
log "All services started"

# ─── 12. Verify ────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Installation Complete — Service Status${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo ""

for unit in agnetic-nats agnetic-staragent agnetic-agent@proxy agnetic-agent@romi agnetic-agent@ergo agnetic-status-bridge agnetic-message-history agnetic-dashboard; do
    status=$(systemctl is-active "$unit.service" 2>/dev/null || echo "inactive")
    if [[ "$status" == "active" ]]; then
        echo -e "  ${GREEN}●${NC} $unit.service — ${GREEN}running${NC}"
    else
        echo -e "  ${RED}●${NC} $unit.service — ${RED}$status${NC}"
    fi
done

echo ""
echo -e "  Dashboard: http://localhost:8788"
echo -e "  NATS:      nats://localhost:4222"
echo -e "  CLI:       agneticctl --help"
echo ""
echo -e "  Logs:      journalctl -u agnetic-* -f"
echo -e "  Status:    systemctl status agnetic-mesh.target"
echo ""
