# Model routing — Aspen OS / Paperclip (2026-08-03)

## FISCAL FREEZE (active)
**Hard company ceiling: $100/mo** until Gumroad cash flow is verified.
Priority order: (1) profitable marketing/Gumroad ship (2) sustain ops (3) Aspen OS build only when it unblocks revenue.
- Prefer **free** OpenCode DeepSeek Flash path and OpenRouter Flash.
- **Grok 4.5 only** for aspen architecture gates / failed CE — not default volume.
- **No scheduled heartbeats** — wake-on-demand only (timers disabled).
- Per-agent caps sum to ~$79; ~$21 company reserve for spikes/marketing agents.

## GPU policy
Local Ollama on Quadro P2000 (5 GB) is **not** used for Paperclip heartbeats or coding agent loops.
Local models remain optional for offline experiments only.

## Defaults
- **Primary volume model:** DeepSeek V4-Flash (`deepseek/deepseek-v4-flash` via OpenRouter; OpenCode `opencode/deepseek-v4-flash-free`)
- **Aspen Paperclip / architect:** Grok 4.5 (`xai-oauth`)
- **Escalate to Grok 4.5** when: architecture, hard review, brand voice, or cheap model fails CE acceptance
- **Escalate to Claude Sonnet** only for rare high-stakes curriculum/brand work (future agents)

## Live routing table

| Agent | Path | Primary model | Monthly budget |
|-------|------|---------------|----------------|
| aspen | hermes `-p aspen` | grok-4.5 | ~$15–25 (gates only) |
| Runtime | hermes `-p runtime` | deepseek/deepseek-v4-flash | lean / on-demand |
| robotics | hermes `-p robotics` | deepseek/deepseek-v4-flash | lean / on-demand |
| Auditor | hermes `-p auditor` | deepseek/deepseek-v4-flash | lean / on-demand |
| packndeploy | hermes `-p packndeploy` | deepseek/deepseek-v4-flash | lean / on-demand |
| Dashboard | hermes `-p dashboard` | deepseek/deepseek-v4-flash | lean / on-demand |
| Compliance | hermes `-p compliance` | deepseek/deepseek-v4-flash | lean / on-demand |
| Opencode | opencode_local | opencode/deepseek-v4-flash-free | prefer free path |
| Aspen Fast Coder | opencode_local | opencode/deepseek-v4-flash-free | prefer free path |
| Aider | process | openrouter/deepseek/deepseek-v4-flash | on-demand |
| Agent Zero | process + Docker UI | configure Flash in A0 UI | on-demand |
| Summarizer | claude_local | claude-haiku-4-5 | rare |
| Reflection Coach | claude_local | (profile default) | rare |

**Company monthly budget:** **$100 hard ceiling** (fiscal freeze). Per-agent figures above are **soft guidance under the company cap**, not a sum of unlimited envelopes. Prefer wake-on-demand; no timer heartbeats.

## Escalate ladder (Compound Engineering)
1. Run on Flash (or role default).
2. If CE-GATE / review fails on quality → re-run with Grok 4.5 (aspen or coding escalate).
3. Brand-critical / curriculum → Sonnet (hire/explicit override).
4. Never silently burn Opus.

## Secrets
- OpenRouter: `OPENROUTER_API_KEY` in Hermes profile `.env` files
- Grok: aspen profile `xai-oauth` tokens in `auth.json`
- Do not put keys in Paperclip issue comments

## Agent Zero UI (manual once)
Open http://127.0.0.1:50080 → set chat model provider to OpenRouter / DeepSeek V4-Flash (or Grok if preferred for that session).
