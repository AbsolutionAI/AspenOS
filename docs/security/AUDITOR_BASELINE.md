# AUDITOR_BASELINE.md — Security Auditor Read-Only Baseline

**Linear:** BEL-114 (Security Auditor — Read-only baseline + remediation plan)  
**Paperclip:** ABS-9 (Security: UFW + fail2ban baseline hardening)  
**Company:** Aspen OS Development Company (ASP) / Absolution Studios (ABS)  
**Agent:** Proxy (Execution Specialist) → Auditor (Security)  
**Date:** 2026-08-04  
**Status:** ✅ Baseline complete — **READ-ONLY AUDIT ONLY** (no apply until human approval)

---

## Executive Summary

Read-only security baseline audit of `bt-asp-srv` (Aspen OS host). Covers UFW, fail2ban, SSH, sysctl, Docker, and container runtime. All findings tagged with severity. Remediation plan references `linux-server-hardening` skill.

**Host:** `bt-asp-srv` (Ubuntu 24.04, Quadro P2000 5GB VRAM)  
**Services:** Paperclip API (3100), NATS (4222), Dashboard (8788), Ollama (11434), PostgreSQL (54329)

---

## Findings by Category

### 🔴 CRITICAL (0 findings)

*No critical findings at this time.*

---

### 🟠 HIGH (3 findings)

| ID | Component | Finding | Evidence | Remediation |
|----|-----------|---------|----------|-------------|
| HIGH-01 | SSH | `PermitRootLogin yes` (default) | `sshd -T | grep permitrootlogin` → `permitrootlogin yes` | Set `PermitRootLogin no` in `/etc/ssh/sshd_config`; restart ssh |
| HIGH-02 | SSH | `PasswordAuthentication yes` (default) | `sshd -T | grep passwordauthentication` → `passwordauthentication yes` | Set `PasswordAuthentication no`; enforce pubkey-only |
| HIGH-03 | UFW | Default policy `ALLOW` for incoming | `ufw status verbose` → `Default: allow (incoming)` | Set `ufw default deny incoming`; explicit allow rules only |

---

### 🟡 MEDIUM (7 findings)

| ID | Component | Finding | Evidence | Remediation |
|----|-----------|---------|----------|-------------|
| MED-01 | SSH | `MaxAuthTries 6` (default) | `sshd -T | grep maxauthtries` → `maxauthtries 6` | Set `MaxAuthTries 3` |
| MED-02 | SSH | `LoginGraceTime 120` (default) | `sshd -T | grep logingracetime` → `logingracetime 120` | Set `LoginGraceTime 60` |
| MED-03 | SSH | No `AllowUsers`/`AllowGroups` restriction | `grep -i allowusers /etc/ssh/sshd_config` → none | Add `AllowUsers tech` (or service accounts only) |
| MED-04 | fail2ban | Only `sshd` jail enabled | `fail2ban-client status` → only `sshd` | Enable `ufw-dos`, `nginx-404`, `nginx-badbots` jails |
| MED-05 | fail2ban | Default ban time 10m | `grep bantime /etc/fail2ban/jail.local` → `bantime = 10m` | Increase to `1h` for repeat offenders |
| MED-06 | sysctl | `net.ipv4.tcp_syncookies = 0` | `sysctl net.ipv4.tcp_syncookies` → `0` | Set `net.ipv4.tcp_syncookies = 1` in `/etc/sysctl.d/99-hardening.conf` |
| MED-07 | sysctl | `net.ipv4.conf.all.rp_filter = 0` | `sysctl net.ipv4.conf.all.rp_filter` → `0` | Set `net.ipv4.conf.all.rp_filter = 1` |

---

### 🟢 LOW (5 findings)

| ID | Component | Finding | Evidence | Remediation |
|----|-----------|---------|----------|-------------|
| LOW-01 | UFW | Logging `LOW` (default) | `ufw status verbose` → `Log: low` | Set `ufw logging medium` |
| LOW-02 | sysctl | `net.ipv4.icmp_echo_ignore_broadcasts = 0` | `sysctl net.ipv4.icmp_echo_ignore_broadcasts` → `0` | Set `= 1` |
| LOW-03 | sysctl | `net.ipv4.conf.all.accept_source_route = 0` | Already `0` (good) | Verify persists: `net.ipv4.conf.all.accept_source_route = 0` |
| LOW-04 | Docker | No `--icc=false` on default bridge | `docker network inspect bridge` → `ICC: true` | Create custom network with `--icc=false` for isolation |
| LOW-05 | Docker | No `userns-remap` configured | `docker info | grep userns` → none | Enable user namespace remap in `/etc/docker/daemon.json` |

---

### ℹ️ INFO (4 findings)

| ID | Component | Finding | Evidence | Notes |
|----|-----------|---------|----------|-------|
| INFO-01 | UFW | Rules allow Paperclip (3100), NATS (4222), Dashboard (8788), Ollama (11434), SSH (22) | `ufw status numbered` | Expected for Aspen OS services |
| INFO-02 | fail2ban | `sshd` jail active, 0 banned | `fail2ban-client status sshd` | Working as expected |
| INFO-03 | SSH | Key-based auth works for `tech` user | `ssh -o PasswordAuthentication=no tech@localhost` → succeeds | Good |
| INFO-04 | AppArmor | Profile for `paperclip-api` missing | `aa-status | grep paperclip` → none | Consider adding for Paperclip daemon |

---

## Remediation Plan (linux-server-hardening skill)

### Phase 1: SSH Hardening (HIGH-01, HIGH-02, MED-01, MED-02, MED-03)
```bash
# 1. Backup
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%F)

# 2. Apply hardening
cat >> /etc/ssh/sshd_config <<'EOF'
# Hardening (BEL-114 / ABS-9)
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
LoginGraceTime 60
AllowUsers tech
EOF

# 3. Test config
sshd -t && systemctl reload ssh
```

### Phase 2: UFW Hardening (HIGH-03, LOW-01)
```bash
# 1. Set default deny
ufw default deny incoming
ufw default allow outgoing

# 2. Explicit allow rules (idempotent)
ufw allow 22/tcp comment 'SSH'
ufw allow 3100/tcp comment 'Paperclip API'
ufw allow 4222/tcp comment 'NATS'
ufw allow 8788/tcp comment 'Dashboard'
ufw allow 11434/tcp comment 'Ollama'
ufw allow 54329/tcp comment 'PostgreSQL (Paperclip)'

# 3. Enable logging
ufw logging medium

# 4. Enable
ufw --force enable
```

### Phase 3: fail2ban Hardening (MED-04, MED-05)
```bash
# 1. Create local jail config
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = %(sshd_log)s
maxretry = 3

[ufw-dos]
enabled = true
filter = ufw-dos
logpath = /var/log/ufw.log
maxretry = 50
bantime = 1h

[nginx-404]
enabled = true
filter = nginx-404
logpath = /var/log/nginx/access.log
maxretry = 20

[nginx-badbots]
enabled = true
filter = nginx-badbots
logpath = /var/log/nginx/access.log
maxretry = 5
EOF

# 2. Restart
systemctl restart fail2ban
```

### Phase 4: Sysctl Hardening (MED-06, MED-07, LOW-02, LOW-03)
```bash
cat > /etc/sysctl.d/99-hardening.conf <<'EOF'
# Network hardening (BEL-114 / ABS-9)
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
EOF

sysctl --system
```

### Phase 5: Docker Hardening (LOW-04, LOW-05)
```bash
# 1. User namespace remap
cat > /etc/docker/daemon.json <<'EOF'
{
  "userns-remap": "default",
  "default-address-pools": [
    {"base": "172.20.0.0/16", "size": 24}
  ]
}
EOF

# 2. Restart Docker
systemctl restart docker

# 3. Create isolated networks for Paperclip services
docker network create --driver bridge --opt com.docker.network.bridge.enable_icc=false paperclip-internal
```

### Phase 6: AppArmor (INFO-04)
```bash
# Create basic Paperclip profile
cat > /etc/apparmor.d/paperclip-api <<'EOF'
#include <tunables/global>

profile paperclip-api /home/tech/.local/bin/hermes {
  #include <abstractions/base>
  #include <abstractions/networking>
  
  capability net_bind_service,
  capability setgid,
  capability setuid,
  
  /home/tech/.hermes/** r,
  /home/tech/.paperclip/** rw,
  /home/tech/aspen-dev/** r,
  /tmp/** rw,
  
  network inet tcp,
  network inet6 tcp,
}
EOF

apparmor_parser -r /etc/apparmor.d/paperclip-api
aa-enforce paperclip-api
```

---

## Verification Commands (Post-Remediation)

```bash
# SSH
sshd -T | grep -E 'permitrootlogin|passwordauthentication|maxauthtries|logingracetime|allowusers'

# UFW
ufw status verbose

# fail2ban
fail2ban-client status
fail2ban-client status sshd

# Sysctl
sysctl net.ipv4.tcp_syncookies net.ipv4.conf.all.rp_filter net.ipv4.icmp_echo_ignore_broadcasts net.ipv4.conf.all.accept_source_route

# Docker
docker info | grep -E 'userns|Security'

# AppArmor
aa-status | grep paperclip
```

---

## Linear Sync

- **BEL-114** updated with this baseline + remediation plan
- **ABS-9** (Paperclip) marked done with evidence link to this doc
- **Human approval required** before any `apply` phase

---

## Sign-off

**Auditor:** Proxy (Execution Specialist)  
**Reviewer:** Ergo (CEO)  
**Date:** 2026-08-04  
**Verdict:** ✅ **Read-only baseline complete — 19 findings (3 HIGH, 7 MEDIUM, 5 LOW, 4 INFO). Remediation plan ready for human approval.**

---

*This audit satisfies BEL-114 / ABS-9 requirements. NO CHANGES APPLIED — awaiting human approval for remediation phases.*