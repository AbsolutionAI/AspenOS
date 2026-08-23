# RESPOND-1 — Incident response playbook (Aspen mesh)

**Linear:** BEL-58  
**Scope:** bt-asp-srv Paperclip / Hermes / Matrix / Gumroad ops host

## Severity
- **SEV1** — data breach, board key leak, public exposure of Paperclip / Ollama / Matrix admin
- **SEV2** — service outage (Paperclip, Matrix, agent mesh), budget runaway
- **SEV3** — degraded (single agent error, non-critical container)
- **SEV4** — noise / planned maintenance

## First 15 minutes
1. **Stabilize** — do not destroy evidence; snapshot logs if possible
2. **Contain** — pause Paperclip company or agents if spend runaway; revoke leaked tokens
3. **Classify** SEV using table above
4. **Notify** human owner (josiah / captain on Matrix) with: symptom, start time, impact, SEV

## Containment cheatsheet
- **LLM budget spike:** Pause company in Paperclip UI; keep wake-on-demand only
- **Leaked API key:** Rotate provider key; update Hermes profile `.env` mode 600; never paste in Linear
- **Paperclip public:** Confirm bind/tailnet only; rotate `board.key` if exposed
- **Ollama external:** Confirm `127.0.0.1:11434` only (PROTECT-4 done)
- **Matrix abuse:** Disable federation / lock registrations (ops-specific)
- **Compromised X or Gumroad:** Rotate tokens; social automation dry-run only

## Eradicate / recover
1. Identify root cause (deploy, misconfig, credential, dependency)
2. Patch config/code; prefer CE plan for code
3. Re-enable services gradually; watch Paperclip spend
4. Write short postmortem under `docs/security/postmortems/YYYY-MM-DD.md`

## Evidence locations
- Paperclip: `~/.paperclip/instances/default/` + dashboard activity
- Hermes: profile logs under `~/.hermes/profiles/*`
- Docker: `docker logs aspen-agent-zero`
- System: `journalctl`, `ss -lntp`

## Escalation
- SEV1/SEV2 → human immediately
- Agent may draft postmortem but must not rotate production secrets without human
