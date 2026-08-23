# Security Architecture — Starship OS 2.1

Defense-in-depth across tools, policy, message bus, packaging, and OS confinement.  
Install roots: **`/opt/starship`**, **`/etc/starship`**, **`/var/lib/starship`**  
(legacy `/opt/agnetic` symlinks for Alpha 2.0 compatibility).

## Threat model (Alpha / Beta)

| Asset | Risk | Mitigations |
|-------|------|-------------|
| Shell / tool execution | Agent RCE, data wipe | Sandbox blocklists, C11 seccomp, path allowlists |
| Untrusted red-team agents | Lateral movement | Fleet ACL, tool allowlists, isolated plant-range |
| NATS bus | Spoofed commands | Accounts/nkeys, token auth, TLS+mTLS default (H-006) |
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

## Recommendations

1. **Ops / multi-node:** accounts mode + TLS; never share red-team credentials with ops
2. **Native gates are mandatory by default (H-003):** startup fails closed if `sandbox_run`/`policyexec` are missing (`python3 -m native_check` runs as `ExecStartPre`)
3. **Ops role tool allowlist (H-005):** fleet team `ops` (the default identity) is restricted to a minimum-necessary tool set in `config/policy.default.json`; unlisted tools are denied fail-closed, HITL vault approvals (`vault_approve`/`vault_deny`) and expansion tools (`opencode`/`opendesign`) are explicitly denied. Add new tools to the ops allowlist deliberately when a workflow needs them.
4. **Install AppArmor** on bare metal
5. **Run agents as non-root** (`User=agnetic`)
6. **Rotate** NATS tokens/passwords after firstboot; store only under `/etc/starship/nats/creds` (mode 600)
7. **Abliterated models:** treat as untrusted reasoners — policy + sandbox mandatory

## Reporting

See root [`SECURITY.md`](../SECURITY.md) for supported versions and vulnerability reporting.
