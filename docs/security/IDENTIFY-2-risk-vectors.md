# IDENTIFY-2 — Risk vectors by exposed service

**Date:** 2026-08-04  
**Depends on:** IDENTIFY-1 inventory

## High
- **Paperclip :3100** — board/agent control plane; must stay private/tailnet-only; board key = full admin
- **Hermes secrets on disk** — `.env` mode 600; backup exposure risk
- **SSH** — standard internet/tailnet attack surface

## Medium
- **Agent Zero :50080** — bound localhost historically; confirm not public
- **Matrix stack** — federation/auth config
- **Ollama :11434** — if bound beyond localhost, model/API abuse

## Lower (with freeze)
- Paused ABSA agents (until budget override)
- Public GitHub gumroad-assets ZIPs (intentional; no secrets)

## Recommended next PROTECT order
1. PROTECT-1 UFW default-deny + allow SSH/tailnet  
2. PROTECT-4 Ollama localhost-only  
3. PROTECT-3 fail2ban on SSH  
4. PROTECT-5 nginx/Matrix review  
