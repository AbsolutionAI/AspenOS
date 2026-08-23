# BEL-51 — UFW draft rule set (DO NOT APPLY blindly)

**Status:** draft only — requires human `sudo` review  
**Host role:** Paperclip / Hermes / Matrix / dev server (tailnet preferred)

## Intent
Default-deny incoming; allow admin + known local services; keep AI/control plane off the public internet.

## Proposed commands (review first)

```bash
# Install if needed
# sudo apt-get install -y ufw

sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH — PREFER locking to tailnet / known IPs in production
sudo ufw allow 22/tcp comment 'ssh'

# If Tailscale is primary access, consider:
# sudo ufw allow in on tailscale0
# and avoid wide-open 22 from WAN

# Optional LAN only examples (ADJUST interface/CIDR):
# sudo ufw allow from 192.168.0.0/16 to any port 3100 proto tcp comment 'paperclip-lan'
# sudo ufw allow from 192.168.0.0/16 to any port 50080 proto tcp comment 'agent-zero-lan'

# Matrix / HTTPS only if this host is the public edge:
# sudo ufw allow 80/tcp
# sudo ufw allow 443/tcp

# Explicitly do NOT publish:
# - 11434 Ollama (localhost only already)
# - 3100 Paperclip to 0.0.0.0/0
# - 54329 Paperclip postgres
# - 50080 Agent Zero to WAN

sudo ufw status verbose
# sudo ufw --force enable   # ONLY after confirming SSH still reachable
```

## Pre-flight checklist
1. Active SSH session + second session or console access  
2. Confirm Tailscale still up if relying on it  
3. `ss -lntp` inventory saved  
4. Agree which services are public vs tailnet  

## Rollback
```bash
sudo ufw disable
# or
sudo ufw delete allow <rule>
```

## Related
- IDENTIFY-1 inventory  
- PROTECT-4 Ollama localhost (done)  
- PROTECT-5 nginx/Matrix review  
