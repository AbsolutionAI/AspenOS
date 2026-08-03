# Aspen OS / Paperclip Foundation Snapshot

**Linear:** [BEL-132](https://linear.app/bellahtech/issue/BEL-132/foundation-verify-and-harden-paperclip-hermes-integration)  
**Paperclip proof ticket:** ASP-2  
**Captured by:** Aspen Hermes (board-assisted foundation harden)

## Versions
| Component | Version / path |
|-----------|----------------|
| Paperclip | 2026.722.0 (API health ok, authenticated/private) |
| hermes-paperclip-adapter | @paperclipai/hermes-paperclip-adapter@2026.722.0 |
| Hermes Agent | v0.19.0 (2026.7.20) |
| OpenCode | 1.18.11 @ `/home/tech/.opencode/bin/opencode` (symlink `/home/tech/opencode`) |
| Aider | present @ `/home/tech/.local/bin/aider` |
| Workspace git root | `/home/tech/aspen-dev/repos/aspen-os` |
| Remote | `https://github.com/AbsolutionAI/starship-os.git` |

## Company
- **Name:** Aspen OS Development Company
- **ID:** `7103d435-1e70-44ad-bdc5-1df876629c1a`
- **Prefix:** ASP
- **Budget:** $1000/mo (`budgetMonthlyCents=100000`)
- **Hire approval:** `requireBoardApprovalForNewAgents=true`
- **Project:** AspenOS (`in_progress`), primary workspace cwd = git root above

## Agent roster & routing
| Agent | Adapter | Notes |
|-------|---------|-------|
| aspen | hermes_local | Architect / CEO-equivalent; Hermes profile `aspen` |
| Opencode | opencode_local | Implementation; cmd OpenCode binary |
| Aspen Fast Coder | opencode_local | Fast coding |
| Runtime | hermes_local | Core runtime |
| robotics | hermes_local | ROS2 |
| packndeploy | hermes_local | Packaging |
| Dashboard | hermes_local | HMI |
| Auditor | hermes_local | Security |
| Compliance | hermes_local | QA/compliance |
| Reflection Coach | claude_local | Built-in |
| Summarizer | claude_local | Built-in |

Hermes profiles on disk: aspen, runtime, robotics, auditor, packndeploy, dashboard, compliance, ergo, romi, proxy.

## Linear integration
- OAuth MCP on aspen profile → `https://mcp.linear.app/mcp` (62 tools)
- Workspace: bellahtech · Team BEL (dev SoR) · FAM (family)
- Mirror rule: Paperclip issues carry `BEL-N` + Linear URL; Linear remains human-facing SoR

## Hardening applied (2026-08-03)
1. Fixed project workspace cwd from non-git `repos/` → `repos/aspen-os`
2. Fixed OpenCode agent command path to real binary; added `/home/tech/opencode` symlink
3. Cleared agent errors on aspen + Opencode (were `workspace_validation_failed`)
4. Set company budget + hire approval gate
5. Updated aspen `AGENTS.md` with company mission, org, stack priorities, values
6. Linear MCP authenticated for BEL read/write

## Session / memory
- Hermes profile memory + skills under `~/.hermes/profiles/<name>/`
- Paperclip heartbeats inject run JWT + issue context; agents must comment before exit
- Linear MCP tokens: `~/.hermes/profiles/aspen/mcp-tokens/linear.json`

## Known follow-ups
- BEL-133 Compound Engineering plugin (no Paperclip plugins installed yet)
- GitHub auth for push/PR (gh + token not yet configured)
- Google Workspace OAuth not yet configured
- Orphan company dir `9b183445-…` not accessible to board key
- ASP-1 hourly sweep still blocked historically — cancel or retarget after workspace fix
### Verified at 2026-08-03T19:46:47Z
- paperclipai: 2026.722.0
- opencode: 1.18.11
- git root: /home/tech/aspen-dev/repos/aspen-os
- git head: efd480b
- adapter pkg: 2026.722.0
