# Security Architecture — Starship OS 2.1

Defense-in-depth across tools, policy, message bus, packaging, and OS confinement.  
Install roots: **`/opt/starship`**, **`/etc/starship`**, **`/var/lib/starship`**  
(legacy `/opt/agnetic` symlinks for Alpha 2.0 compatibility).

## Threat model (Alpha / Beta)

| Asset | Risk | Mitigations |
|-------|------|-------------|
| Shell / tool execution | Agent RCE, data wipe | Sandbox blocklists, C11 seccomp, path allowlists |
| Untrusted red-team agents | Lateral movement | Fleet ACL, tool allowlists, isolated plant-range |
| NATS bus | Spoofed commands | Accounts/nkeys, token auth, TLS+mTLS default (H-006), signed node enrollment + revocation list (H-002) |
| Secrets in logs/LLM context | Credential leak | Redaction patterns, gitignore, SecretsManager |
| Abliterated local models | Weaker refusal | Mandatory policy + sandbox + Droid Shield |

## Sandboxed tool execution

Agents run tools through `CommandExecutor` (`agents/tools.py`):

| Rule | Description |
|------|-------------|
| Blocked commands | `mount`, `mkfs`, `dd`, `shutdown`, `reboot`, destructive patterns |
| Privileged commands | `sudo`, `su`, `chmod 777`, `chown`, `passwd`, `useradd` |
| Path allowlists | Prefer `/opt/starship`, `/etc/starship`, `/tmp`, `/var/log/starship` |
| Max output | 50KB per tool call |
| Timeout | 30s default |

### Optional C11 isolation

```bash
# Native C11 gates are default-on since H-003; the exports below are no-ops
# and only needed to pin intent. Opt out (dev only, deprecated):
# export STARSHIP_SANDBOX_NATIVE=0   # sandbox_run (seccomp + NEWNS/NEWPID)
# export STARSHIP_POLICY_NATIVE=0    # policyexec shared JSON gate
export STARSHIP_POLICY=/etc/starship/policy.json
```

| Binary | Role |
|--------|------|
| `sandbox_run` | fork+exec, seccomp-bpf allowlist, best-effort namespaces |
| `policyexec` | `check-tool` / `check-command` against `policy.default.json` |

Shared policy contract: `config/policy.default.json` → packaged as `/etc/starship/policy.json`.

## Fleet red / blue policy

`agents/fleet_policy.py` + `config/fleet.yaml` ACL:

- **Red-team:** tools limited (`read_file`, `list_dir`, `search_files`, `http_get`, `delegate_to_agent`); never unrestricted OpenCode
- **Cross-plant:** fail-closed; `plant-range` isolation during exercises
- Identity: `/etc/starship/fleet-node.yaml` or `STARSHIP_FLEET_TEAM` / `STARSHIP_FLEET_ROLES`

## NATS authentication

| Mode | When | How |
|------|------|-----|
| **accounts** (default) | all profiles, H-001 | Multi-tenant `STARSHIP_OPS` / `EDGE` / `RANGE` / `TELEM` + nkeys |
| **token** | explicit trusted-LAN opt-in (`STARSHIP_NATS_MODE=fleet`) | `STARSHIP_NATS_TOKEN` + `fleet-bus.conf` |
| **TLS + mTLS** (default in new deployments) | firstboot auto-runs `gen-nats-tls.sh` (H-006) | server rejects non-TLS; clients present fleet-CA certs (`--node <name>`) |
| **Node enrollment** | remote nodes, H-002 (`fleet-enroll.sh`) | CSR signed only against a fleet-CA-signed enrollment token; revocation list enforced at sign/connect/peer layers |

The legacy no-auth **agent-bus** mode was removed (H-001 / threat model F-001):
the bus always authenticates. Clients in accounts mode must present
user/password or an nkey — bare-token and anonymous connects fail closed
(`agents/nats_connect.py`).

```bash
# Generate multi-tenant accounts + optional nkeys
bash scripts/gen-nats-accounts.sh --out /etc/starship/nats
# Clients: source /etc/starship/nats.env  (or creds/ops.env)
```

### Single-node dev migration

Local development uses the same accounts mode on localhost — no special
no-auth config exists anymore:

```bash
bash scripts/gen-nats-accounts.sh --out nats          # writes conf + creds/ (gitignored)
nats-server -c nats/fleet-accounts.conf &
set -a; source nats/nats.env; set +a                  # ops-role client env
```

`scripts/start-agents.sh` and `make dev` perform this generation automatically
when no authenticated conf is present.

Dual-publish subjects: `starship.*` (primary) + `agnetic.*` (legacy).  
Python helper: `agents/nats_connect.py` (user/pass, token, nkey, TLS).

### H-017 — no live NATS secrets in git

`nats/server.conf` is **placeholder-only / deprecated**. It must never carry
real tokens or account passwords. Production and lab buses are generated under
`/etc/starship/nats/` (or gitignored `nats/creds/`, `nats/fleet-accounts.conf`,
`nats/nats.env`).

| Path | Role |
|------|------|
| `nats/fleet-accounts.conf.tmpl` | Committed template (`__OPS_PASS__`, …) |
| `scripts/gen-nats-accounts.sh` | Materializes conf + per-role env (chmod 600) |
| `scripts/setup-nats-auth.sh` | Dev helper: generate → start → smoke pub |
| `scripts/starship-firstboot.sh` | Ops path: `_enable_accounts_bus` + TLS |
| `nats/server.conf` | Deprecated stub with `__STARSHIP_NATS_TOKEN__` / `__SYS_PASS__` markers only |

Packaging installs the stub as `/etc/starship/nats/server.conf.deprecated` so it
cannot be mistaken for `active.conf`.

### NATS secret rotation (historically committed lab values)

The following **lab** strings were previously committed in `nats/server.conf` and
are **revoked**. Do not reuse them on any node, CI runner, or golden image:

- token formerly named in threat model F-016 / H-017 (plain token auth)
- account passwords formerly used for `admin` / `agnetic` users

**Operator action on any host that ever ran the old conf:**

```bash
# 1) Stop the bus
sudo systemctl stop agnetic-nats 2>/dev/null || pkill -x nats-server || true

# 2) Regenerate accounts + client env (new random secrets)
sudo bash /opt/starship/lib/starship/scripts/gen-nats-accounts.sh \
  --out /etc/starship/nats --host 127.0.0.1

# 3) Point active conf + reload unit env
sudo ln -sfn /etc/starship/nats/fleet-accounts.conf /etc/starship/nats/active.conf
sudo cp /etc/starship/nats/nats.env /etc/starship/nats.env
sudo systemctl daemon-reload
sudo systemctl restart agnetic-nats starship-fleet 'agnetic-agent@*' 2>/dev/null || true
```

Edge nodes must re-enroll / pull fresh role env (`creds/edge.env` or fleet
installer token path). Treat git history as public for those lab values.

### Subject permission sketch (accounts mode)

| Role | Account | Publish (examples) |
|------|---------|-------------------|
| ops | STARSHIP_OPS | `starship.>`, `agnetic.>` |
| edge | STARSHIP_EDGE | fleet heartbeat/register, proxy, telemetry |
| red | STARSHIP_RANGE | proxy + fleet heartbeat only |
| telem | STARSHIP_TELEM | `starship.telemetry.>` only |

## AppArmor

Profiles under `security/apparmor/` (install: `sudo bash scripts/install-apparmor.sh`):

| Profile | Scope |
|---------|-------|
| agent | Denies raw sockets, mount, ptrace; limits writes outside starship trees |
| ollama | GPU + model dirs; restricted FS |
| nats | Conf + JetStream store + logs only |

Paths should be updated to `/etc/starship` / `/opt/starship` when loading on 2.1 hosts.

## Encrypted configuration & secrets

```python
from agents.security import SecretsManager
sm = SecretsManager(password="master-password")
sm.set("api-key", "…")
```

- AES-256-GCM + PBKDF2
- Never commit: `*.key`, `*.pem`, `.env`, `credentials/`, `nats/creds/`, `nats/tls/`

## Secret redaction

Tool output redacts before LLM context:

```
password=***REDACTED***
ghp_***REDACTED***
sk-***REDACTED***
```

## Systemd hardening

Units under `systemd/` use:

```ini
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
# plus ProtectKernel*, RestrictSUIDSGID where applicable
EnvironmentFile=-/etc/starship/nats.env
User=agnetic   # nats user for message bus
```

## Packaging trust boundary

```bash
make deb
sudo dpkg -i dist/starship-os_*.deb
```

- Layout: `/opt/starship`, `/etc/starship` (validated in `scripts/build-deb.sh`)
- postinst creates users `agnetic` / `nats`, venv, enables units
- Firstboot (ops): multi-tenant NATS accounts + optional native sandbox

## Legacy `nats/server.conf` (H-017)

`nats/server.conf` is a **placeholder-only** legacy template. It must never contain
live tokens/passwords. Installers may copy it under `/etc/starship/nats/` but
**must not** point `active.conf` at it — active bus remains `fleet-accounts.conf`
(default) or firstboot-materialized `fleet-bus.conf`.

Lab hosts that once used the historically committed lab tokens must **rotate**
those credentials (treat them as burned). Prefer:

```bash
bash scripts/gen-nats-accounts.sh --out /etc/starship/nats
# + TLS: bash scripts/gen-nats-tls.sh --out /etc/starship/nats/tls --host <cn>
```

## Paperclip C2 control plane (H-019 / F-019)

Org agent mesh C2 (Paperclip `:3100`, board keys, multi-company blast radius) is
documented separately — do not conflate with plant NATS safety:

- Runbook: [`docs/security/PAPERCLIP_C2_HARDENING.md`](security/PAPERCLIP_C2_HARDENING.md)

## Biweekly threat-model checklist

Use during ASP-298/ASP-431-style reviews (see full model at [`SECURITY_THREAT_MODEL_v2.2.md`](SECURITY_THREAT_MODEL_v2.2.md)):

- [ ] NATS: no live secrets in git (`nats/*.conf`); accounts + TLS defaults held (H-001/H-006/H-017)
- [ ] Paperclip C2: F-019 items in [`docs/security/PAPERCLIP_C2_HARDENING.md`](security/PAPERCLIP_C2_HARDENING.md)
- [x] Dual-human `propose_act`→`act` path wired (H-016 / ASP-364): `aspen_edge.gate.DualHumanGate` in EdgeRRM; contract [`docs/security/ACT_GATE_CONTRACT.md`](security/ACT_GATE_CONTRACT.md); sim-only until G9
- [ ] Host baseline SSH/UFW draft vs apply gate (H-HOST-01) — human approval required
- [ ] Sandbox/policyexec mandatory (H-003); ops tool allowlist (H-005)
- [ ] Physical cell prerequisites: OT network segmentation (H-025), HITL vault approval gate (H-022), hardware estop watchdog (H-023)
- [ ] Backlog hardening: H-020 (software data-diode) and H-021 (directional ACL) still open
- [ ] IEC 62443-4-2 mapping gap items: identity role model (F-015), OT transport segmentation (F-017)
- [ ] Budgets non-zero where zero=unlimited; fiscal freeze caps if still active
- [ ] No secrets in issue/Linear bodies; key files mode 600

## Recommendations

1. **Ops / multi-node:** accounts mode + TLS; never share red-team credentials with ops
2. **Native gates are mandatory by default (H-003):** startup fails closed if `sandbox_run`/`policyexec` are missing (`python3 -m native_check` runs as `ExecStartPre`)
3. **Ops role tool allowlist (H-005):** fleet team `ops` (the default identity) is restricted to a minimum-necessary tool set in `config/policy.default.json`; unlisted tools are denied fail-closed, HITL vault approvals (`vault_approve`/`vault_deny`) and expansion tools (`opencode`/`opendesign`) are explicitly denied. Add new tools to the ops allowlist deliberately when a workflow needs them.
4. **G9 prerequisite: OT network segmentation (H-025):** cell NATS must not share transport with plant agents. Dedicated loop or VLAN + drop-and-forward bridge.
5. **G9 prerequisite: HITL vault approval gate (H-022):** physical cell act requires vault approval path, not just dual-human NATS authorize.
6. **Install AppArmor** on bare metal
7. **Run agents as non-root** (`User=agnetic`)
8. **Rotate** NATS tokens/passwords after firstboot; store only under `/etc/starship/nats/creds` (mode 600)
9. **Abliterated models:** treat as untrusted reasoners — policy + sandbox mandatory
10. **Paperclip board keys:** mode 600 + rotation SLA per C2 runbook (H-019)

## Reporting

See root [`SECURITY.md`](../SECURITY.md) for supported versions and vulnerability reporting.
