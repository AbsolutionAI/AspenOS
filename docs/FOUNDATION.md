## Aspen OS / Paperclip Foundation Snapshot

**Linear:** BEL-132, BEL-153, BEL-113, BEL-114, BEL-154  
**Paperclip proof tickets:** ASP-2 (foundation), ASP-5 (Aider), ASP-6 (Agent Zero), ABS-7, ABS-8, ABS-9, ABS-10  
**Captured by:** Aspen Hermes (board-assisted foundation harden)

## Versions
| Component | Version / path |
|-----------|----------------|
| Paperclip | 2026.722.0 (API health ok, authenticated/private) |
| hermes-paperclip-adapter | @paperclipai/hermes-paperclip-adapter@2026.722.0 |
| Hermes Agent | v0.19.0 (2026.7.20) |
| OpenCode | 1.18.11 at /home/tech/.opencode/bin/opencode (symlink /home/tech/opencode) |
| Aider | 0.86.2 at /home/tech/.local/bin/aider (process worker hired BEL-134) |
| Workspace git root | /home/tech/aspen-dev/repos/aspen-os |
| Remote | AbsolutionAI/starship-os |

## Company
- Name: Aspen OS Development Company
- ID: 7103d435-1e70-44ad-bdc5-1df876629c1a
- Prefix: ASP
- Budget: $1000/mo (budgetMonthlyCents=100000)
- Hire approval: requireBoardApprovalForNewAgents=true
- Project: AspenOS (in_progress), primary workspace cwd = git root above

## Agent roster and routing
| Agent | Adapter | Notes |
|-------|---------|-------|
| aspen | hermes_local | Architect / CEO-equivalent |
| Opencode | opencode_local | Implementation |
| Aspen Fast Coder | opencode_local | Fast coding |
| Aider | process | Aider CLI worker (BEL-134) |
| Agent Zero | process | Docker A0 lifecycle (BEL-134) |
| Runtime | hermes_local | Core runtime |
| robotics | hermes_local | ROS2 |
| packndeploy | hermes_local | Packaging |
| Dashboard | hermes_local | HMI |
| Auditor | hermes_local | Security |
| Compliance | hermes_local | QA/compliance |
| Reflection Coach / Summarizer | claude_local | Built-ins |

## ABS Company (Absolution Studios)
- Name: Absolution Studios
- ID: 9b183445-abef-48b2-a45f-52950b04da49
- Prefix: ABS
- Budget: $40/mo (budgetMonthlyCents=4000)
- Hire approval: requireBoardApprovalForNewAgents=false
- Project: Aspen OS Development vertical

## ABS Agent roster
| Agent | Adapter | Model | Notes |
|-------|---------|-------|-------|
| Ergo | hermes_local | Nemotron 3 Ultra | CEO / Orchestration |
| Proxy | hermes_local | DeepSeek V4-Flash | Execution Specialist |
| Romi | hermes_local | DeepSeek V4-Flash | Creative Director |
| OpenCode | opencode_local | DeepSeek V4-Flash | Code Runner |
| OpenDesign | opencode_local | DeepSeek V4-Flash | Prototype Builder |

## Linear integration
- OAuth MCP on aspen profile
- Workspace: bellahtech · Team BEL (dev SoR)
- Mirror rule: Paperclip issues carry BEL-N plus Linear URL

## Hardening applied (2026-08-03)
1. Fixed project workspace cwd to repos/aspen-os
2. Fixed OpenCode agent command path
3. Cleared agent errors; budget plus hire approval
4. Updated aspen AGENTS.md
5. Compound Engineering gates (BEL-133)
6. Aider + Agent Zero process workers (BEL-134)

## ABS Hardening applied (2026-08-04) — foundation-harden checklist
1. ✅ Workspace git roots validated (all agents)
2. ✅ Adapter binaries resolve (Ergo, Proxy, Romi, OpenCode, Aspen)
3. ✅ Sticky errors cleared (no adapter_failed, no workspace_validation_failed)
4. ✅ Budget gates enforced ($40 ABS, $40 ASP, $35 ABSA, $15 Content; wake-on-demand)
5. ✅ CE gates wired in AGENTS.md (Discovery → Plan → Implement → QA → Compound)
6. ✅ Proof tickets: ABS-7, ABS-8, ABS-9, ABS-10 (this doc + docs/ops/FOUNDATION.md)

## Known follow-ups
- [x] Aider process worker online (BEL-134 / ASP-5)
- [x] Agent Zero docker image pull + UI config (ASP-6)
- [ ] GitHub auth for push/PR
- [ ] Google Workspace OAuth
- [ ] BEL-135+ stack items
- [ ] docs/ops/FOUNDATION.md proof ticket for ABS-7
- [ ] COMPANY_MAP.md updated with ABS mirror mappings

## ABS Mirror issues (Aspen OS Development vertical)
| Linear | ABS | Title | Status |
|--------|-----|-------|--------|
| BEL-153 | ABS-7 | Core agent mesh hardening | ✅ done |
| BEL-113 | ABS-8 | Compound Engineering gates | ✅ done |
| BEL-114 | ABS-9 | Security Auditor baseline | ✅ done |
| BEL-154 | ABS-10 | Shared Local Memory & Conversation Caching Layer | ✅ done |

Mirror convention: Paperclip issues include `Linear: BEL-N` + URL in description.

## ABS mirror deliverable routing (ASP-36)

**Decision:** keep ABS/ASP shared proof in this monorepo (ABS agents share this git cwd; ABS company paused $0). Do **not** move trees to a non-existent ABS product repo. Path ownership + `.gitignore` protect the public AspenOS remote.

Full table (ASP product vs shared proof vs local-only ABSA/Content/OSINT): **`docs/ops/ABS_MIRROR_ROUTING.md`**.

## Model routing (2026-08-03)
- Local Ollama **retired** for Paperclip heartbeats (P2000 5GB too slow/small).
- **aspen (Paperclip)** → Grok 4.5 (`xai-oauth`)
- **Domain Hermes agents** → DeepSeek V4-Flash via OpenRouter
- **OpenCode / Aider** → DeepSeek V4-Flash
- Full table + budgets: `docs/MODEL_ROUTING.md`

## Fiscal freeze (2026-08-03)
Company model budget **$100/mo** until Gumroad revenue is verified. Wake-on-demand only. Prefer free/Flash models; Grok sparingly for aspen gates. Marketing/Gumroad outranks greenfield Aspen OS spend.
