# Package mesh reference review — 2026-08-22

**Paperclip:** ASP-46  
**Linear epic:** [BEL-164](https://linear.app/bellahtech/issue/BEL-164/epic-github-package-mesh-aspen-grove) (Done)  
**Reviewer:** aspen (heartbeat)  
**SoR map:** `docs/PACKAGE_MAP.md`  
**Meta index:** https://github.com/AbsolutionAI/aspen-grove/blob/master/PACKAGES.md

## Verdict

**v1 public mesh remains COMPLETE and third-party-cloneable for control packages.**  
Epic BEL-164 children BEL-165–176 + BEL-178 are Done; BEL-177 private lane stays Backlog (cash-flow defer).  
This pass was a **reference audit + drift repair**, not a new packaging program.

## Inventory reconciliation

| Source | Count | Notes |
|--------|------:|-------|
| AbsolutionAI public repos (gh) | 35 | includes forks + products |
| PACKAGE_MAP named packages | 34 → 35 | added **aspen-dev** |
| grove `PACKAGES.md` | 28 → synced | was missing boundary + OS forks + self |

### Gaps closed this pass

1. **PACKAGE_MAP / ADRs / plan were untracked** on aspen-os working trees — committed into git SoR.
2. **grove PACKAGES.md drift** vs map: missing `aspen-agent-runtime`, `aspen-dashboard`, `aspen-grove` (self), `agnetic-os`, `worldmonitor`, `fleetmdm`.
3. **aspen-dev** public but absent from PACKAGE_MAP control inventory.
4. **api-boilerplate `make smoke`** failed when host `npx prisma` resolved Prisma 7 (schema uses Prisma 5 `url = env(...)`). Smoke now installs local deps and uses package-local Prisma 5.

### Sample audit (12 repos)

| Repo | License | Standard docs | `make smoke` | Secrets rg |
|------|---------|---------------|--------------|------------|
| aspen-contracts | Apache-2.0 | missing root CONTRACTS.md (fixed) | pass | clean |
| aspen-grove | Apache-2.0 | missing root CONTRACTS.md (fixed) | pass | clean |
| aspen-matrix-ops | Apache-2.0 | OK | pass | clean |
| api-boilerplate | MIT | OK | **fail→fixed** | clean |
| aspen-langgraph-worker | Apache-2.0 | OK | pass | clean |
| aspen-agent-runtime | Apache-2.0 | OK | pass | clean |
| aspen-dashboard | Apache-2.0 | OK | pass | clean |
| aspen-process-workers | Apache-2.0 | OK | pass | clean |
| aspen-swarm-manager | Apache-2.0 | OK | pass | clean |
| saas-starter-kit | MIT | OK | pass | clean |
| aspen-dev | (none) | incomplete | n/a → minimal standard added | clean |
| aspen-pcake | Apache-2.0 | partial (ARCHITECTURE/CONTRACTS/THIRD_PARTY/SECURITY/linear-map) | pass | clean |

## Residual / follow-ups (non-blocking v1)

| Item | Owner | Priority |
|------|-------|----------|
| aspen-pcake full doc-standard files | packndeploy / aspen | low |
| Slim runtime/dashboard extract beyond pointer | aspen | future (PACKAGE_MAP) |
| BEL-177 private Leonardo/Family lane | human + aspen | deferred (cash flow) |
| Product compose auto-vendoring | aspen | future |

## Agent rules (unchanged)

1. Read PACKAGE_MAP before new repos  
2. Use `repo-documentation-standard` / skill `aspen-package-mesh`  
3. No secrets in git  
4. Comment Linear BEL-164 children when packaging  

## Evidence

- Org list: `gh repo list AbsolutionAI --limit 100`  
- Sample clones + smoke under Paperclip run scratch  
- Skills: `aspen-package-mesh`, `repo-documentation-standard`
