# Adjacent Agent Desktops: Jan and OpenWork

**Status:** Decision recorded  
**Date:** 2026-08-26  
**Linear:** BEL-244, BEL-245, BEL-246  

## Decision

Aspen OS will **not fork** [janhq/jan](https://github.com/janhq/jan) or [modelstudioai/openwork](https://github.com/modelstudioai/openwork).

They are **optional maintainer tools and pattern sources**. They are not the plant HMI and they do not replace Paperclip, Hermes, OpenCode, NATS, or AspenContext.

## Why

| Project | Job | Conflict with Aspen |
|---------|-----|---------------------|
| Jan | Local ChatGPT + model hub + MCP | General consumer/dev desktop; would dilute manufacturing C2 |
| OpenWork | Agent Cowork desktop (Qwen / ModelStudio / Bailian) | Cloud-ecosystem lock-in risk; coding-agent UX not SME-operator UX |
| Aspen | Plant command-and-control OS | Progressive AI (ADR-001), AspenContext (ADR-002), crash briefing (ADR-003) |

## What we will take

1. **Jan OpenAI-compatible API** (`localhost:1337`) as an optional inference sidecar next to Ollama (BEL-244).
2. **Permission-gated tool use** from OpenWork: confirm before file write, command execution, or external calls (BEL-245 → feeds crash briefing and invoke-agent safety).
3. **Maintainer session visibility**: tool calls, logs, artifacts — not a floor-operator chat wall (BEL-245).
4. **Named assistants / skills packs** as format inspiration for Hermes souls (BEL-241). Do not depend on Bailian first-party skills.
5. **Ichigo** as a later candidate for voice Invoke Preferred Agent (BEL-246, after BEL-239).

## What we will not take

- Jan Desktop or OpenWork as the operator dashboard
- Forks of llama.cpp / vllm / Cortex / Qwen Code as Aspen core
- Binding inference to Aliyun ModelStudio / Bailian
- Replacing AspenContext with OpenWork “external-context”

## Placement

- Laptop (RTX 4050): Jan / OpenWork may be installed as **personal maintainer clients**.
- Server (Ubuntu + Ollama + P2000): keep current stack; Jan API only if the BEL-244 spike is a go.
- Plant operators: ADR-001 Quiet default. No Cowork-style desktop.

## Related ADRs

- ADR-001 Progressive AI Assistance Policy
- ADR-002 AspenContext Propagation & Routing Contract
- ADR-003 Crash → Agent Briefing Runtime Pattern
