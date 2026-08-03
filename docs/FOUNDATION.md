# Aspen OS / Paperclip Foundation Snapshot

**Linear:** BEL-132  
**Paperclip proof tickets:** ASP-2 (foundation), ASP-5 (Aider), ASP-6 (Agent Zero)  
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

## Known follow-ups
- [x] Aider process worker online (BEL-134 / ASP-5)
- [ ] Agent Zero docker image pull + UI config (ASP-6)
- [ ] GitHub auth for push/PR
- [ ] Google Workspace OAuth
- [ ] BEL-135+ stack items
