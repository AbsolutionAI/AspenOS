# IDENTIFY-1 — Asset inventory (server)

**Date:** 2026-08-04  
**Host:** bt-asp-srv (Paperclip/Hermes mesh)  
**Linear:** Andromeda Security / NIST IDENTIFY-1

## Purpose
Baseline inventory of services and data classes before PROTECT/DETECT work.

## Key application assets

**Paperclip**
- Port: 3100
- UI/API for ASP / ABSA / Content / ABS companies

**Hermes aspen profile**
- Path: `~/.hermes/profiles/aspen`
- Grok + Linear MCP + secrets

**Agent Zero**
- Port: 50080
- Container name: aspen-agent-zero

**Gumroad product tree**
- Path: `/home/tech/Gumroad-dev/gumroad-products`
- ZIP mirrors: `gumroad-zips/` + GitHub `AbsolutionAI/gumroad-assets`

**Aspen OS repo / docs**
- Path: `/home/tech/aspen-dev/repos/aspen-os`

**Ollama**
- Port: 11434
- Not default for Paperclip heartbeats (fiscal + GPU policy)

**Matrix**
- Local homeserver stack (historical Conduit/tuwunel images)

## Data sensitivity classes
1. **Secrets** — Hermes `.env`, Paperclip `board.key`, xurl auth, Gumroad tokens  
2. **Commerce** — Gumroad account, product ZIPs  
3. **Family** — FAM Linear projects (minimize agent exposure)  
4. **Public** — GitHub release assets  

## Snapshot commands (re-run anytime)
```bash
ss -lntp | head -80
docker ps --format '{{.Names}} {{.Image}} {{.Ports}}'
free -h; df -h / /home
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
```

## Follow-ons
- IDENTIFY-2: risk map by exposed port  
- PROTECT-1: UFW default-deny (human/sudo)  
- PROTECT-4: confirm Ollama bind localhost only  
