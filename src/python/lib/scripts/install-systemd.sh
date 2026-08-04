#!/bin/bash
# Install Starship OS systemd services
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -d "$REPO_DIR/systemd" ]; then
    SERVICES_DIR="$REPO_DIR/systemd"
else
    SERVICES_DIR="/opt/starship/systemd"
fi
SYSTEMD_DIR="/etc/systemd/system"

SERVICES=(agnetic-nats agnetic-staragent agnetic-agent@ agnetic-dashboard agnetic-status-bridge agnetic-message-history)

echo "=== Installing Starship OS Systemd Services ==="
echo ""
echo "  Source: $SERVICES_DIR"

for svc in "${SERVICES[@]}"; do
    if [[ "$svc" == *@ ]]; then
        src="$SERVICES_DIR/$svc.service"
        [ -f "$src" ] || src="$SERVICES_DIR/${svc%-}.service"
    else
        src="$SERVICES_DIR/$svc.service"
    fi
    if [ -f "$src" ]; then
        echo "  Installing ${svc}..."
        sudo cp "$src" "$SYSTEMD_DIR/${svc}.service"
        sudo systemctl daemon-reload 2>/dev/null
    else
        echo "  WARNING: $src not found, skipping"
    fi
done

if [ -f "$SERVICES_DIR/agnetic-mesh.target" ]; then
    echo "  Installing agnetic-mesh.target..."
    sudo cp "$SERVICES_DIR/agnetic-mesh.target" "$SYSTEMD_DIR/agnetic-mesh.target"
fi

echo ""
echo "=== Enabling services ==="
sudo systemctl enable "${SERVICES[@]}" agnetic-mesh.target 2>/dev/null || true
sudo systemctl enable agnetic-agent@proxy.service agnetic-agent@romi.service agnetic-agent@ergo.service 2>/dev/null || true

echo ""
echo "=== Current status ==="
for svc in "${SERVICES[@]}" agnetic-mesh.target; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        echo "  ✓ $svc is active"
    else
        echo "  ○ $svc is inactive"
    fi
done

echo ""
echo "=== Next steps ==="
echo "  To start all services: sudo systemctl start agnetic-nats agnetic-staragent agnetic-agent@proxy agnetic-agent@romi agnetic-agent@ergo agnetic-dashboard"
echo "  To view logs: journalctl -u agnetic-nats -f"
