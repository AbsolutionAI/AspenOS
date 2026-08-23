# Security Policy

**Product:** Starship OS  
**Canonical docs:** [`docs/SECURITY.md`](docs/SECURITY.md)

## Supported versions

| Version | Support |
|---------|---------|
| **2.1.0** | Current GA — security fixes applied here |
| 2.1.0-beta.x / alpha.x | Superseded; upgrade recommended |
| 0.2.x (agnetic-os) | Legacy archive — no new features |

## Reporting a vulnerability

1. **Do not** open a public GitHub issue for exploitable vulnerabilities.
2. Prefer a private report via GitHub Security Advisories on  
   [AbsolutionAI/AspenOS](https://github.com/AbsolutionAI/AspenOS/security/advisories/new)
   or contact the maintainers listed in the repo.
3. Include: affected version, component path, reproduction steps, impact.

We aim to acknowledge reports within **7 days**.

## Security model (summary)

| Layer | Controls |
|-------|----------|
| **Tool sandbox** | Python `CommandExecutor` + optional C11 `sandbox_run` (seccomp, namespaces) |
| **Policy** | Shared JSON (`config/policy.default.json`) + C11 `policyexec` + fleet red/blue ACL |
| **NATS** | Dual-prefix subjects; multi-tenant accounts + nkeys; mTLS by default (H-006); per-node enrollment tokens + revocation list (H-002) |
| **Secrets** | Gitignored credentials; AES-256-GCM secrets helper; output redaction |
| **Runtime** | systemd `NoNewPrivileges`, `ProtectSystem=strict`; AppArmor profiles |
| **Models** | Local Ollama only by default; abliterated models require policy + sandbox |

## Hardening checklist

```bash
# Multi-tenant NATS (ops)
bash scripts/gen-nats-accounts.sh --out /etc/starship/nats
# TLS+mTLS default-on since H-006 (firstboot auto-runs; opt out: STARSHIP_NATS_TLS=0)
bash scripts/gen-nats-tls.sh --out /etc/starship/nats/tls
# Native isolation
# Native enforcement is default-on since H-003; opt out ONLY for dev:
# export STARSHIP_SANDBOX_NATIVE=0 STARSHIP_POLICY_NATIVE=0
# AppArmor
sudo bash scripts/install-apparmor.sh
```

See **[docs/SECURITY.md](docs/SECURITY.md)** for full architecture.
