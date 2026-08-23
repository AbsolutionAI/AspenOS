# Aspen Mesh → GitHub Package Mesh Implementation Plan

> **For Hermes:** Use `plan` + CE gates + `paperclip-board-ops` + OpenCode/Aider workers. Prefer subagent-per-package after inventory lock.  
> **Mode:** Plan only until captain says `execute package mesh`.

**Goal:** Parse the entire BellahTech/Aspen production+dev environment and all Linear-backed projects into **standalone, well-documented GitHub packages** that third parties can clone, review, and run alone — then compose into a full **command-and-control (C2) back/front end**.

**Architecture:** **Grove model** — each package is a tree (usable tool); the grove is the mesh (compose via contracts). Linear remains SoR for work; GitHub is distribution + review surface; Paperclip/Hermes remain runtime control planes (not fully public).

**Tech stack:** GitHub (AbsolutionAI), Linear (bellahtech/BEL), Paperclip, Hermes, Docker Compose, NATS contracts, OpenAPI/JSON Schema for inter-package APIs, CE plan→implement→QA→compound.

---

## 1. Goal detail

### Outcomes
1. **Inventory map:** every runtime surface + Linear project → package candidate  
2. **Repo-per-capability** (or thin monorepo groups where coupling is unavoidable)  
3. **Each repo ships:**
   - README (purpose, standalone use, compose use)
   - ARCHITECTURE.md / package contract
   - `.env.example` (no secrets)
   - `docker-compose.yml` or install script where applicable
   - `docs/THIRD_PARTY.md` (how to test/review)
   - `Makefile` or `justfile` with `make test` / `make up`
   - LICENSE
   - CI (GitHub Actions) smoke  
4. **Compose layer:** meta-repo `aspen-grove` (or `aspen-c2`) that pulls packages as submodules/subtrees or compose includes  
5. **Skills:** Hermes + Paperclip planning/docs skills installed and assigned so agents can keep extracting/documenting  

### Non-goals (v1)
- Publishing private production secrets  
- Making Paperclip board keys or Matrix homeserver public  
- Full rewrite of Aspen OS while packaging  
- Family (FAM) data in public repos  

---

## 2. Current context (inventory snapshot 2026-08-05)

### Already on GitHub (AbsolutionAI)
| Repo | Role today |
|------|------------|
| AspenOS | Main OS / starship lineage |
| agnetic-os | Prior OS lineage |
| gumroad-assets | ZIP mirrors |
| saas-starter-kit, cli-scaffold-tool, api-boilerplate, react-admin-template, tailwind-component-pack, web-game-template, pygame-platformer, godot-rpg-template, social-automation | Product packages |
| worldmonitor, fleetmdm | Forks / upstream work |

### Local git (not all cleanly published as standalone tools)
| Path | Notes |
|------|--------|
| `/home/tech/aspen-dev/repos/aspen-os` | Primary docs + OS worktree |
| `/home/tech/Gumroad-dev/gumroad-products/*` | Products (many already have remotes) |
| `/home/tech/aspen-dev/scripts` | Paperclip workers — **not** a repo |
| `/home/tech/aspen-dev/agent-zero` | Runtime support |
| Hermes profiles `~/.hermes/profiles/*` | **Do not publish raw** — extract skills/config templates only |
| Paperclip `~/.paperclip` | **Do not publish** — export compose + schema docs only |
| Matrix / NATS / Ollama host services | Package as **infra blueprints**, not live data |

### Linear projects (all must appear in the map)
**In Progress:** Aspen OS Development · Paperclip Agent Stack · Multi-Company Alignment · Gumroad Product Launch · OSINT Global Dashboard  

**Backlog:** Leonardo Influencer · NIST security (Ship-Wide + Andromeda) · eXo Family Hub · World Monitor Upstream · Affiliate · OpenManus · Digital Products · Local Family AI  

---

## 3. Package taxonomy (grove layers)

```
L0  contracts     — schemas, NATS subjects, event envelopes, auth Zanzibar-ish notes
L1  runtime       — agent runtime, adapters, process workers
L2  control       — Paperclip blueprints, Hermes profile templates, gateway patterns
L3  edge          — Matrix bridge patterns, dashboards, telemetry agents
L4  domain        — manufacturing/robotics adapters (OPC-UA/MQTT/ROS2 stubs)
L5  products      — Gumroad kits (already mostly split)
L6  verticals     — OpenSINT, World Monitor contrib, Leonardo, Affiliate, Family (private)
L7  compose-c2    — meta compose + UI shell that wires L1–L5
```

**Rule:** A third party can run **any single L5 product** with Docker/Node only.  
**Rule:** A third party can run **L7 compose** only after accepting multi-service resource needs.  
**Rule:** L6 Family stays **private org** or redacted samples.

---

## 4. Target GitHub repo set (proposed)

### A. Control & runtime (public, secrets stripped)
| Repo | Source | Standalone tool |
|------|--------|-----------------|
| `aspen-contracts` | New extract | JSON Schema + NATS subject catalog + OpenAPI stubs |
| `aspen-agent-runtime` | aspen-os / agnetic runtime slices | Run one agent loop against mock bus |
| `aspen-paperclip-blueprints` | Export from live Paperclip (sanitized) | `docker compose` Paperclip-like lab + seed companies |
| `aspen-hermes-profile-template` | Sanitized aspen profile | `hermes`-ready profile skeleton + skill pins |
| `aspen-process-workers` | `aspen-dev/scripts/paperclip-*-worker.py` | Aider/A0 adapters as CLI |
| `aspen-ce-gates` | CE docs + opencode config | Drop-in CE checklist + CI gate scripts |
| `aspen-model-routing` | MODEL_ROUTING.md + examples | Policy library for Flash/Grok freeze |

### B. Edge & C2
| Repo | Source | Standalone tool |
|------|--------|-----------------|
| `aspen-dashboard` | dashboard/ static+API slices | Local C2 UI against mock APIs |
| `aspen-telemetry-agent` | StarAgent / osquery patterns | Single-host telemetry shipper |
| `aspen-matrix-ops` | Matrix runbooks only | Deploy notes + danger checklist (no homeserver dump) |
| `aspen-grove-compose` | **NEW meta** | Compose file including optional profiles: `products`, `runtime`, `full-c2` |

### C. Products (already exist — standardize docs/CI)
All 9 Gumroad repos: enforce identical `THIRD_PARTY.md` + CI smoke + version tags matching Gumroad.

### D. Linear vertical packages
| Linear project | Package approach |
|----------------|------------------|
| Aspen OS Development | `AspenOS` + contracts/runtime extracts |
| Paperclip Agent Stack / Multi-Company | blueprints + workers + CE gates |
| Gumroad Template Suite | product repos + `gumroad-assets` |
| OSINT / World Monitor | `worldmonitor` fork hygiene + `aspen-osint-layers` (new) for custom layers |
| Leonardo pipeline | `aspen-influencer-pipeline` (**private** until policy clear) — n8n export + stubs |
| Andromeda / NIST security | `aspen-security-baseline` — playbooks + audit scripts (no host dumps) |
| Affiliate / Digital Products | docs+templates already under `docs/commerce` → `aspen-commerce-playbooks` |
| eXo / Local Family AI | **private** `aspen-family-*` or withhold |
| OpenManus | thin wrapper repo or document-only |

---

## 5. Per-repo documentation standard (mandatory)

Every public package root:

```
README.md           # 5-minute start + what it is / isn't
ARCHITECTURE.md     # boundaries, deps, compose ports
CONTRACTS.md        # events/APIs this package speaks (link aspen-contracts)
THIRD_PARTY.md      # review guide, threat model lite, how to test
SECURITY.md         # secrets handling, what was redacted
CHANGELOG.md
LICENSE
.env.example
Makefile            # make test | make up | make smoke
docs/
  screenshots/      # optional
  linear-map.md     # which BEL projects this serves
.github/workflows/ci.yml
```

### README sections (template)
1. One-sentence purpose  
2. Standalone quickstart  
3. Compose-with-grove  
4. Config surface  
5. Tests  
6. Linear project links  
7. Related packages  

---

## 6. Skills to maximize planning (Hermes + Paperclip)

### Already present (use heavily)
| Skill | Use |
|-------|-----|
| `plan` | Write/execute bite-sized package plans under `.hermes/plans/` |
| `paperclip-board-ops` | Companies, agents, skills/sync, Linear mirror, CE |
| `absolution-commerce-ops` | Product repos + Gumroad/X |
| `test-driven-development` | Per-package smoke tests first |
| `requesting-code-review` | Pre-publish review gates |
| `simplify-code` | After extract cleanups |
| `spike` | Validate extract boundaries before big moves |
| `systematic-debugging` | CI/third-party clone failures |
| `github-pr-workflow` (Paperclip catalog) | PR hygiene |
| `task-planning` / `issue-triage` (Paperclip) | Package epic breakdown |
| `doc-maintenance` (Paperclip) | Keep READMEs aligned |
| Compound Engineering | plan → implement → QA → compound per package |

### Add / author next (priority order)
1. **`aspen-package-extract`** (new Hermes skill)  
   - Trigger: “package repo”, “extract for GitHub”, “third-party ready”  
   - Steps: inventory → redact → scaffold docs → CI → push → Linear comment  
2. **`repo-documentation-standard`** (new) — enforce template above via checklist script  
3. **`linear-project-to-repo-map`** (new) — maintain `PACKAGE_MAP.md` from Linear project list  
4. **Paperclip catalog:** ensure all coding agents have `task-planning`, `doc-maintenance`, `github-pr-workflow`, `qa-acceptance` (already partially assigned)  
5. **Hermes:** pin `plan` + package-extract on Aspen profile; Content/Marketer keep commerce skills only  

### Paperclip agent assignment (planning mesh)
| Agent | Extra skills for this program |
|-------|-------------------------------|
| aspen | plan, task-planning, doc-maintenance, github-pr, qa |
| Opencode / Fast Coder | github-pr, qa, doc-maintenance |
| Digital Packager | doc-maintenance, github-pr (when ABSA unpaused) |
| Auditor | qa-acceptance, doc-maintenance |
| Content Lead | out of scope except marketing packages |

---

## 7. Redaction & security rules (non-negotiable)

**Never publish:**
- `~/.xurl`, MCP tokens, Gumroad tokens, board.key  
- Paperclip DB dumps, Matrix media, family data  
- Real OPENROUTER/X/GitHub PATs  

**Publish instead:**
- `.env.example` with dummy values  
- `secrets.template.env`  
- Architecture diagrams of auth flows  

**Scan before every push:**
```bash
# example gate
rg -n "ghp_|xoxb-|sk-|OPENROUTER|board\.key|BEGIN RSA" -g '!*.md' || true
```

Add CI secret scan (gitleaks) on all public packages.

---

## 8. Phased execution plan

### Phase 0 — Lock the map (1–2 days)
**Objective:** Single source map Linear ↔ path ↔ repo ↔ layer  

**Deliverables:**
- `aspen-os/docs/PACKAGE_MAP.md`  
- Linear epic: **GitHub Package Mesh**  
- ADR: grove packaging principles  

**Tasks:**
1. Enumerate Linear projects → package IDs  
2. Enumerate local paths + existing remotes  
3. Mark public vs private vs internal-only  
4. Captain approves map  

### Phase 1 — Contracts + standards (2–3 days)
**Objective:** `aspen-contracts` + doc template + CI template  

**Tasks:**
1. Create `aspen-contracts` repo with event envelope schema  
2. Author `repo-documentation-standard` skill + cookiecutter/`copier` template  
3. Add gitleaks + basic CI workflow template  
4. Document NATS subject naming from live/intended mesh  

### Phase 2 — Product repo normalization (2–4 days)
**Objective:** All 9 Gumroad repos pass third-party clone test  

**Tasks per product:**
1. Ensure remote AbsolutionAI/<slug>  
2. Apply doc standard  
3. `make smoke` green on clean machine (or document GPU/desktop needs for games)  
4. Tag `v1.0.0-thirdparty`  
5. Link from PACKAGE_MAP  

### Phase 3 — Runtime & control extracts (1–2 weeks)
**Objective:** Public blueprints for Hermes/Paperclip/workers without secrets  

**Order:**
1. `aspen-process-workers`  
2. `aspen-hermes-profile-template`  
3. `aspen-ce-gates` + `aspen-model-routing`  
4. `aspen-paperclip-blueprints` (compose + seed JSON, no keys)  
5. `aspen-agent-runtime` (largest — spike boundary first)  

### Phase 4 — C2 compose shell (1 week)
**Objective:** `aspen-grove-compose` brings up lab C2  

**Profiles:**
- `products` — static product demos  
- `agents` — hermes template + mock LLM  
- `full` — blueprints + dashboard + mock bus  

**Acceptance:** third party follows README and gets health endpoints green in ≤30 minutes on 16GB RAM machine (document if more required).

### Phase 5 — Vertical packages (ongoing)
**Objective:** One Linear project → one package wave  

**Priority under fiscal freeze:**  
1) Security baseline docs/scripts  
2) OpenSINT/worldmonitor hygiene  
3) Commerce playbooks  
4) Leonardo **private**  
5) Family **withhold/private**  

### Phase 6 — Third-party review program
**Objective:** External testers  

**Tasks:**
1. `THIRD_PARTY_REVIEW.md` scorecard  
2. Invite process (issues with label `third-party-review`)  
3. Dogfood skill runs against each package  
4. Public roadmap project on GitHub mirroring Linear epic  

---

## 9. Linear epic structure (create on execute)

**Epic:** GitHub Package Mesh / Grove packaging  

| Issue | Title |
|-------|--------|
| P0 | Approve PACKAGE_MAP + public/private matrix |
| P0 | ADR grove packaging |
| P1 | aspen-contracts v0 |
| P1 | doc standard + cookiecutter |
| P1 | gitleaks CI template |
| P2 | Normalize 9 product repos |
| P3 | process-workers package |
| P3 | hermes-profile-template |
| P3 | paperclip-blueprints |
| P3 | agent-runtime extract spike |
| P4 | aspen-grove-compose |
| P5 | security-baseline package |
| P5 | osint/worldmonitor package plan |
| P6 | third-party review scorecard |

Mirror each to Paperclip ASP issues with `Linear: BEL-N`.

---

## 10. Inter-package contract (so compose works)

Minimal shared rules (live in `aspen-contracts`):

1. **Health:** `GET /health` → `{status: ok|degraded, version}`  
2. **Events:** CloudEvents-ish JSON `{id, source, type, time, data}`  
3. **Auth for lab:** shared `ASPEN_LAB_TOKEN` in compose network only  
4. **Ports:** registry in CONTRACTS.md (no collisions)  
5. **Data dirs:** bind mounts under `./data/<package>`  

---

## 11. Validation / definition of done

### Per package
- [ ] Fresh clone on clean VM/container  
- [ ] `make smoke` or documented manual smoke  
- [ ] No secrets in git history (gitleaks)  
- [ ] README standalone path works without grove  
- [ ] CONTRACTS.md lists deps  

### Grove
- [ ] `docker compose --profile agents up` healthy  
- [ ] Dashboard shows mock agents  
- [ ] One product container reachable  

### Process
- [ ] Linear epic 100% mapped  
- [ ] Skills installed; aspen agent has package-extract  
- [ ] Captain sign-off on public/private matrix  

---

## 12. Risks & tradeoffs

| Risk | Mitigation |
|------|------------|
| Over-extraction freezes product work | Phase 2 products first (revenue); runtime later |
| Secret leakage | gitleaks + human review on control packages |
| Aspen-os monorepo too tangled | Spike boundaries; allow `aspen-os` to remain umbrella temporarily |
| Third parties lack GPU/VRAM | Document; provide CPU mock paths |
| Fiscal freeze / ABSA pause | Use Aspen+OpenCode Flash; no ABSA wakes |
| Family/Leonardo sensitivity | Private repos or stubs only |
| Duplicate sources of truth | PACKAGE_MAP is canonical; Linear links out |

---

## 13. Open questions (captain)

1. **Org visibility:** all under `AbsolutionAI` public, or `AbsolutionAI-labs` + private?  
2. **Meta-repo name:** `aspen-grove` vs `aspen-c2` vs `aspen-mesh`?  
3. **License default:** MIT for products (current) and Apache-2.0 for runtime?  
4. **Include Matrix** as deployable package or docs-only?  
5. **Leonardo / Family:** private org yes/no?  
6. **Priority override:** products polish first vs contracts/runtime first?  

---

## 14. Recommended default answers (if no reply)

- Public `AbsolutionAI` for L0–L5; private for Family/Leonardo  
- Meta-repo: **`aspen-grove`**  
- MIT products; Apache-2.0 control/runtime  
- Matrix: **docs-only** v1  
- Execute order: **P0 map → P1 contracts/standard → P2 products → P3 runtime → P4 compose**  

---

## 15. Skills install checklist (first execute hour)

```text
Hermes (aspen profile):
- ensure: plan, paperclip-board-ops, absolution-commerce-ops, tdd, requesting-code-review, spike
- create: aspen-package-extract, repo-documentation-standard, linear-project-to-repo-map

Paperclip (ASP agents):
- sync: task-planning, doc-maintenance, github-pr-workflow, qa-acceptance, issue-triage
- aspen: full architect set + package skills via instructions pointer
```

---

## 16. First concrete commands after approval

```bash
# 1) Write PACKAGE_MAP from this plan
# 2) gh repo create AbsolutionAI/aspen-contracts --public
# 3) copier/cookiecutter apply doc standard to api-boilerplate as pilot
# 4) Linear epic + P0–P1 issues
# 5) CE plan docs/plans/BEL-XXX-package-mesh.md
```

---

## 17. Success picture

A stranger can:

```bash
git clone https://github.com/AbsolutionAI/api-boilerplate && cd api-boilerplate && make smoke
```

and later:

```bash
git clone https://github.com/AbsolutionAI/aspen-grove && cd aspen-grove && make up-agents
```

and see a coherent lab C2 stitched from packages — without ever touching bt-asp-srv secrets.

---

**Plan status:** READY FOR APPROVAL  
**Reply:** `execute package mesh` · or `package mesh revise: …` · or answer open questions in §13

---

## LOCKED (2026-08-05 captain)

- Org: split if possible; **no second org access** → AbsolutionAI (+ private repos / aspen-private-* later)
- Meta: **aspen-grove**
- License: MIT products / Apache-2.0 runtime
- Matrix: **homeserver docs-only** (tuwunel/conduit stack — not chat product)
- Leonardo/Family: **private**
- Order: map → contracts → products → runtime → compose
- Map: `docs/PACKAGE_MAP.md` · ADR-0001
- Created: https://github.com/AbsolutionAI/aspen-contracts · https://github.com/AbsolutionAI/aspen-grove
- Linear epic: BEL-164
