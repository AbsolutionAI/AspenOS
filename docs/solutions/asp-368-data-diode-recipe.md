# ASP-368 / F-020: Software Data-Diode Policy Recipe

**Status:** AUDITOR_APPROVED (QUEUED — do not apply without dual-human authorization)
**Source:** Security Threat Model v2.2 (ASP-298) — MEDIUM finding F-020
**Master Spec ref:** `docs/sor/ASPENGROVE_MASTER_SPEC_v4.0.md` §3.4
**Parent issue:** ASP-368
**Updated:** 2026-09-20

---

## 1. Problem Statement

OSINT agents (Ergo, Proxy with `osint-threat` skill, WorldMonitor integration)
require outbound internet access for intelligence gathering. Without a data
diode, these agents — if compromised via an external feed, RCE in a tool call,
or supply-chain attack — could be used as a bridge from Z0 (Internet) into Z1
(Fleet Bus / NATS) and from there into Z2/Z3/Z4 (Plant zones).

The Master Spec requires software data-diode emulation **now**, with hardware
diode (Securacore / Vigilant class) planned for future classified domains.

**Threat model entry (F-020):** Software data-diode missing for OSINT/ingest
path — an OSINT agent compromise could leak plant telemetry or inject commands
via NATS.

---

## 2. Architecture & Data Flow

```
 Z0 (Internet/WAN)
      │
      │  HTTPS/TCP outbound only
      ▼
┌─────────────────────┐
│  OSINT Node / DMZ    │  ← Dedicated host or VM
│  • Ergo / Proxy      │
│  • WorldMonitor       │
│  • osint-threat skill │
└────────┬────────────┘
         │
         │  NATS publish only: aspen.sentinel.osint.ingest
         │  NO subscribe. NO plant subjects.
         ▼
  Z1 (Fleet Bus / NATS JetStream)
         │
         ▼
  Z2/Z3/Z4 (Plant zones — NOT reachable from OSINT node)
```

**Direction rules:**
- OSINT node → Internet: outbound only (no inbound listener)
- Internet → OSINT node: DENY ALL (no reverse shell path)
- OSINT node → NATS: publish `aspen.sentinel.osint.ingest` only (no subscribe)
- NATS → OSINT node: DENY ALL (no command injection path)
- OSINT node → Plant zones (Z2/Z3/Z4): DENY ALL (no lateral movement)

---

## 3. nftables Recipe (Primary)

Apply on the OSINT node. Replace every placeholder below before apply.

| Variable | Example | Description |
|----------|---------|-------------|
| `OSINT_IFACE` | `eth0` | OSINT node primary data interface |
| `NATS_SERVER_IP` | `10.5.100.10` | Fleet bus NATS server (port 4222) |
| `DNS_RESOLVER_IP` | `10.5.100.1` | Upstream DNS resolver |
| `MGMT_IFACE` | `tailscale0` | Management interface if separate from data path (see §9 #2) |

> **WARNING:** `flush ruleset` in the ruleset below erases ALL existing
> nftables rules. If the node has pre-existing firewall rules (Tailscale,
> Docker, UFW-generated nftables), they will be removed. The activation
> script backs up current rules; restore with the rollback script if needed.

### 3.1 Base ruleset: `osint-diode.nft`

```nftables
#!/usr/sbin/nft -f

# Flush existing ruleset — CAUTION: removes ALL nftables rules on this host
flush ruleset

table inet diode {
    chain base {
        type filter hook input priority 0; policy drop;

        # Management interface — allow SSH (set MGMT_IFACE to your management
        # interface, e.g. tailscale0, or comment out if no separate mgmt path)
        # iif $MGMT_IFACE tcp dport 22 accept

        # Loopback — allow all
        iif lo accept

        # Established/related return traffic (response to our outbound)
        ct state established,related accept

        # ICMP ping / path MTU (limited)
        ip protocol icmp icmp type { echo-request, echo-reply, destination-unreachable, time-exceeded, parameter-problem } accept
        ip6 nexthdr icmpv6 icmpv6 type { echo-request, echo-reply, destination-unreachable, packet-too-big, time-exceeded, parameter-problem, neighbour-solicitation, neighbour-advertisement } accept

        # Log and drop everything else inbound (rate-limited)
        log prefix "DIODE-DROP-IN " flags all limit rate 5/minute counter drop
    }

    chain outbound {
        type filter hook output priority 0; policy drop;

        # Loopback — allow all
        oif lo accept

        # Allow outbound DNS to known resolver only
        udp dport 53 ip daddr $DNS_RESOLVER_IP accept
        tcp dport 53 ip daddr $DNS_RESOLVER_IP accept

        # Allow outbound HTTPS for OSINT feeds (no HTTP — enforce TLS)
        tcp dport 443 accept

        # Allow outbound NATS to fleet bus only (port 4222)
        tcp dport 4222 ip daddr $NATS_SERVER_IP accept

        # Allow NTP for clock sync
        udp dport 123 accept

        # Log and drop everything else (rate-limited)
        log prefix "DIODE-DROP-OUT " flags all limit rate 5/minute counter drop
    }

    chain forward {
        type filter hook forward priority 0; policy drop;
        log prefix "DIODE-DROP-FWD " limit rate 5/minute counter drop
    }
}
```

**Hardening notes:**
- Block HTTP (port 80) — OSINT agents must use HTTPS only
- Block all inbound connections — no SSH from the Internet side. Management
  access must use a dedicated interface (Tailscale / VPN / out-of-band mgmt).
  If the host has no separate mgmt interface, **do not apply this ruleset** at
  a remote site without a local console — you will lose access.
- Block raw ICMP beyond echo/path-MTU types
- Block all forwarding — OSINT node is not a router

### 3.2 Activation script: `apply-osint-diode.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# ASP-368 — Software Data-Diode Apply Script
# ============================================================
# HUMAN GATE: Do NOT run this script without dual-human
# authorization. This modifies host firewall.
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RULESET="${SCRIPT_DIR}/osint-diode.nft"
BACKUP_DIR="/var/backups/nftables"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

# Pre-flight: require nftables
if ! command -v nft &>/dev/null; then
    echo "ERROR: nftables not found. Install: apt install nftables"
    exit 1
fi

# Backup current ruleset
mkdir -p "${BACKUP_DIR}"
nft list ruleset > "${BACKUP_DIR}/pre-diode-${TIMESTAMP}.nft" 2>/dev/null || true
echo "Backup saved: ${BACKUP_DIR}/pre-diode-${TIMESTAMP}.nft"

# Validate syntax before applying
nft --check -f "${RULESET}"
echo "Syntax OK. Applying ruleset..."

# Apply
nft -f "${RULESET}"
echo "Data-diode ruleset applied."

# Verify
echo "=== Active ruleset ==="
nft list table inet diode
```

### 3.3 Rollback: `remove-osint-diode.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# ASP-368 — Software Data-Diode Rollback
# ============================================================

# Delete the diode table entirely (reverts to system default)
nft delete table inet diode 2>/dev/null && \
    echo "Data-diode table removed. Firewall reverted to system defaults." || \
    echo "No diode table found (already clean)."

# Note: if the system had custom rules before the diode, restore from
# /var/backups/nftables/pre-diode-*.nft
echo "Restore previous ruleset with:  nft -f /var/backups/nftables/pre-diode-<TIMESTAMP>.nft"
```

---

## 4. iptables Alternative (Legacy Systems)

For systems without nftables (older Ubuntu 20.04, CentOS 7, etc.), the
equivalent iptables ruleset. Apply with `iptables-restore < osint-diode.ipt`.
Replace `NATS_SERVER_IP` and `DNS_RESOLVER_IP` with your values before apply.

### `osint-diode.ipt`

```text
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT DROP [0:0]

# Loopback
-A INPUT -i lo -j ACCEPT
-A OUTPUT -o lo -j ACCEPT

# Management interface (uncomment and set your mgmt interface if separate)
# -A INPUT -i <MGMT_IFACE> -p tcp --dport 22 -j ACCEPT

# Established/related return traffic
-A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
-A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# ICMP limited
-A INPUT -p icmp --icmp-type echo-request -j ACCEPT
-A INPUT -p icmp --icmp-type echo-reply -j ACCEPT
-A INPUT -p icmp --icmp-type destination-unreachable -j ACCEPT
-A INPUT -p icmp --icmp-type time-exceeded -j ACCEPT
-A INPUT -p icmp --icmp-type parameter-problem -j ACCEPT
-A OUTPUT -p icmp --icmp-type echo-request -j ACCEPT
-A OUTPUT -p icmp --icmp-type echo-reply -j ACCEPT

# Outbound DNS
-A OUTPUT -p udp --dport 53 -d DNS_RESOLVER_IP -j ACCEPT
-A OUTPUT -p tcp --dport 53 -d DNS_RESOLVER_IP -j ACCEPT

# Outbound HTTPS (OSINT feeds)
-A OUTPUT -p tcp --dport 443 -j ACCEPT

# Outbound NATS
-A OUTPUT -p tcp --dport 4222 -d NATS_SERVER_IP -j ACCEPT

# Outbound NTP
-A OUTPUT -p udp --dport 123 -j ACCEPT

# Log dropped (rate-limited to avoid log flood)
-A INPUT -m limit --limit 5/min -j LOG --log-prefix "DIODE-IPT-DROP-IN: "
-A OUTPUT -m limit --limit 5/min -j LOG --log-prefix "DIODE-IPT-DROP-OUT: "
-A FORWARD -m limit --limit 5/min -j LOG --log-prefix "DIODE-IPT-DROP-FWD: "

COMMIT
```

---

## 5. Process Isolation for OSINT Agents

OSINT agents run under systemd with **mandatory** sandboxing flags. This is the
second layer of the diode — even if firewall rules are bypassed (local process),
the systemd sandbox constrains what the agent process can do.

### 5.1 Recommended systemd unit override (`/etc/systemd/system/<service>.d/diode.conf`)

```ini
[Service]
# Filesystem sandbox
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/var/lib/agnetic/osint
ReadOnlyPaths=/etc/agnetic

# Network sandbox — allow internet, restrict IPC
PrivateNetwork=false
RestrictAddressFamilies=AF_INET AF_INET6 AF_NETLINK AF_UNIX
IPAddressAllow=0.0.0.0/0
IPAddressDeny=

# Process sandbox
NoNewPrivileges=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectKernelLogs=true
ProtectClock=true
ProtectHostname=true
ProtectControlGroups=true
MemoryDenyWriteExecute=true
LockPersonality=true
RestrictRealtime=true
SystemCallArchitectures=native
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM
CapabilityBoundingSet=CAP_NET_BIND_SERVICE CAP_NET_RAW

# No root or setuid escalation
PrivateUsers=true
RemoveIPC=true
UMask=0077
```

### 5.2 NATS account: OSINT-only permissions

The OSINT node authenticates with a dedicated NATS account that can **only**
publish to `aspen.sentinel.osint.ingest`. It cannot subscribe, cannot publish
to `aspen.fleet.*`, `starship.*`, or any other subject.

In the NATS accounts template (`fleet-accounts.conf.tmpl`):

```text
accounts {
    STARSHIP_OSINT: {
        users: [
            { user: "osint-agent", password: "$OSINT_NATS_PASSWORD" }
        ]
        permissions: {
            publish: { allow: ["aspen.sentinel.osint.ingest"] }
            subscribe: { allow: [] }
        }
        exports: [
            { stream: { account: STARSHIP_OPS, subject: "aspen.sentinel.osint.ingest" } }
        ]
    }
    # ... other accounts unchanged
}
```

**Hardening note:** Use nkey-based auth instead of password when possible
(following ASP-536 / H-011 pattern).

### 5.3 OSINT agent YAML config (fleet.yaml)

```yaml
agents:
  - id: osint-collector
    account: STARSHIP_OSINT
    plant: osint                      # Dedicated plant zone
    tools:
      allow: [http_get, web_search, web_extract, delegate_to_agent]
      deny: [write_file, shell, agent_shell, opencode, opendesign]
    sandbox: systemd                  # Use the diode.conf override above
```

**Tool restrictions:**
- OSINT agents do NOT have `write_file`, `shell`, `agent_shell`, `opencode`,
  or `opendesign` — no code execution or file write capability
- OSINT agents CAN use `http_get`, `web_search`, `web_extract` — read-only
  intelligence gathering
- OSINT agents CAN `delegate_to_agent` only within the `osint` plant

---

## 6. Validation Steps

Run these after applying the diode to confirm one-way enforcement:

### 6.1 Inbound blocked (from internet to OSINT node)

```bash
# From outside the OSINT node (e.g., a test VM):
curl -s -o /dev/null -w "%{http_code}" http://OSINT_NODE_IP:8080
# Expected: connection refused or timeout (not 200)

nc -zv OSINT_NODE_IP 22
# Expected: connection refused
```

### 6.2 Outbound restricted

```bash
# On the OSINT node itself:
curl -s -o /dev/null -w "%{http_code}" http://example.com
# Expected: connection refused (HTTP blocked; HTTPS should work)

curl -s -o /dev/null -w "%{http_code}" https://api.osint-feeds.com
# Expected: 200 or similar success

nc -zv NATS_SERVER_IP 4222
# Expected: connection succeeds (NATS allowed)

nc -zv PLANT_NODE_IP 4222
# Expected: connection refused or timeout
```

### 6.3 NATS subject enforcement

```bash
# Attempt to publish to plant subject:
nats pub aspen.fleet.node.command.test "test" \
  --server nats://NATS_SERVER_IP:4222 --user osint-agent --password $OSINT_NATS_PASSWORD
# Expected: permissions violation error

# Attempt to subscribe:
nats sub aspen.sentinel.osint.ingest \
  --server nats://NATS_SERVER_IP:4222 --user osint-agent --password $OSINT_NATS_PASSWORD
# Expected: permissions violation error

# Authorized publish:
nats pub aspen.sentinel.osint.ingest '{"source":"test","content":"validation"}' \
  --server nats://NATS_SERVER_IP:4222 --user osint-agent --password $OSINT_NATS_PASSWORD
# Expected: OK
```

### 6.4 systemd sandbox verification

```bash
# Check that OSINT agent unit loaded the override:
systemctl cat agnetic-agent@osint | grep -E 'ProtectSystem|NoNewPrivileges|IPAddressAllow'

# Verify process is confined:
systemd-analyze security agnetic-agent@osint
# Expected: SAFE or MEDIUM (not UNSAFE)
```

---

## 7. Human Gate Procedure

**DO NOT** apply the host firewall rules without dual-human authorization.
The iptables/nftables rules in this recipe control ALL traffic on the OSINT
node — a mistake can isolate the node completely.

### 7.1 Gate flow

```
┌─────────────────────────────────────────────────────┐
│  1. Engineer proposes_act on aspen.safety.act.gate   │
│     Payload includes: diff of ruleset, target host   │
│     ID, rollback procedure, scheduled window          │
├─────────────────────────────────────────────────────┤
│  2. Dual human authorization required:                │
│     - First distinct human authorizes (`authorize`)  │
│     - Second distinct human authorizes (`authorize`)  │
│     (See ADR-0009 Phase 1 / ASP-540)                 │
├─────────────────────────────────────────────────────┤
│  3. Apply during maintenance window (no OSINT loss)  │
│     Run apply-osint-diode.sh                          │
├─────────────────────────────────────────────────────┤
│  4. Run validation steps (§6)                         │
│     Confirm: inbound blocked, outbound restricted,    │
│     NATS subjects enforced, sandbox active            │
├─────────────────────────────────────────────────────┤
│  5. Log outcome to aspen.sentinel.audit.event         │
│     Include: ruleset hash, validation results,        │
│     authorizing human IDs, rollback backup path       │
└─────────────────────────────────────────────────────┘
```

### 7.2 Pre-flight checklist

- [ ] Ruleset reviewed by second engineer
- [ ] Management access path confirmed (console / Tailscale / out-of-band)
- [ ] Backup of current nftables/iptables ruleset saved
- [ ] Rollback script tested on non-production node
- [ ] NATS account changes validated in staging
- [ ] OSINT agent tool restrictions confirmed in fleet.yaml
- [ ] systemd override file written and syntax-checked
- [ ] Maintenance window communicated to team

---

## 8. Design Decisions & Constraints

| Decision | Rationale |
|----------|-----------|
| **nftables as primary, iptables as fallback** | nftables is the modern Linux firewall (default in Ubuntu 22.04+, Debian 11+). iptables provided for older OSINT host deployments. |
| **Block all inbound, allow limited outbound** | OSINT agents are consumers of external data — they initiate all connections. No service listens on the OSINT node. |
| **No HTTP (port 80) outbound** | OSINT feeds must use TLS. Prevents plaintext injection and MITM on external data. |
| **Dedicated NATS account with publish-only** | Even if the OSINT node is fully compromised, the attacker cannot subscribe to plant telemetry or inject commands to other agents. |
| **Systemd sandbox as second layer** | Defence in depth: if a local privilege escalation bypasses nftables (e.g., the attacker runs as root and deletes the ruleset), the systemd sandbox still constrains process capabilities. |
| **No classified domains yet** | Hardware diode (Securacore / Vigilant) deferred until classified manufacturing / CUI domains are active. Software diode is sufficient for current OSINT scope. |

---

## 9. Open Items (Residual)

1. **Persistence** — The nftables ruleset in this recipe is not persistent across
   reboot. On production deployment, persist via `/etc/nftables.conf` or
   `nft list ruleset > /etc/nftables.conf` after apply, and enable
   `nftables.service`.

2. **Tailscale / VPN coexistence** — If the OSINT node uses Tailscale for
   management access, the ruleset must allow Tailscale's interface
   (`tailscale0`, typically `100.x.y.z/10`). Add a rule:
   `iif tailscale0 accept` or scope management to the Tailscale interface.

3. **WireGuard / VPN for OSINT feeds** — Some OSINT sources require a VPN
   exit node. If used, add the VPN interface to the allow list similarly.

4. **Monitoring** — Add the `DIODE-DROP-` logged events to the Sentinel audit
   trail (`aspen.sentinel.audit.event`) for alerting on blocked traffic
   attempts.

5. **Credential rotation** — OSINT NATS account password should be rotated on
   the same 90-day cadence as other NATS credentials (H-017).

---

## 10. Related Documents

- `docs/SECURITY_THREAT_MODEL_v2.2.md` — F-020 entry
- `docs/sor/ASPENGROVE_MASTER_SPEC_v4.0.md` §3.4 — Data-diode requirement
- `docs/adr/ADR-0007-nats-subject-contracts-sentinel-c2.md` — `aspen.sentinel.osint.ingest` subject contract
- `docs/FLEET.md` — Subject table, OSINT ingest subject
- `docs/adr/ADR-0009.md` — Gatekeeper / dual-human approval + capability tokens
- `docs/solutions/asp-536-nats-acl-template.md` — NATS per-role ACL template pattern
- `docs/ops/WEEKLY_ARCHITECTURE_REVIEW_2026-08-24.md` — D5: software data-diode recipe added to backlog
- `docs/architecture/WORLDMONITOR_INTEGRATION.md` — OSINT Global Dashboard integration

---

*End of recipe. Next review: Before production apply or when classified domains are added.*