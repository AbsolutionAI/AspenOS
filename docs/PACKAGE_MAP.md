# PACKAGE_MAP — Aspen Grove (GitHub package mesh)

> **Authority note:** Product/architecture SoR is **Master Spec v4.0** — `docs/sor/ASPENGROVE_MASTER_SPEC_v4.0.md`. This map is the GitHub packaging inventory under that spec.

**Status:** COMPLETE for v1 public mesh — 2026-08-06  
**Linear project:** [Aspen Grove — GitHub Package Mesh](https://linear.app/bellahtech/project/aspen-grove-github-package-mesh-6c079ac99473)  
**Epic:** BEL-164  
**Agent doc:** [Aspen Grove Package Mesh — Agent Reference](https://linear.app/bellahtech/document/aspen-grove-package-mesh-agent-reference-8d2a85c20144)  
**Meta-repo:** https://github.com/AbsolutionAI/aspen-grove  

---

## Locked decisions

| Decision | Choice |
|----------|--------|
| Org | AbsolutionAI (private org later) |
| Meta-repo | **aspen-grove** |
| License | **MIT** products · **Apache-2.0** runtime/control |
| Matrix | **docs-only** homeserver ops |
| Leonardo/Family | **private** (indexed in aspen-private-lane) |
| Order | map → contracts → products → runtime → compose |

---

## Public packages (v1 complete)

### Meta / contracts
| Repo | License | Notes |
|------|---------|-------|
| [aspen-grove](https://github.com/AbsolutionAI/aspen-grove) | Apache-2.0 | Compose profiles + PACKAGES.md index |
| [aspen-contracts](https://github.com/AbsolutionAI/aspen-contracts) | Apache-2.0 | Event envelope schema |
| [aspen-private-lane](https://github.com/AbsolutionAI/aspen-private-lane) | Apache-2.0 | Public names-only private inventory |

### Control / runtime
| Repo | License |
|------|---------|
| [aspen-process-workers](https://github.com/AbsolutionAI/aspen-process-workers) | Apache-2.0 |
| [aspen-hermes-profile-template](https://github.com/AbsolutionAI/aspen-hermes-profile-template) | Apache-2.0 |
| [aspen-paperclip-blueprints](https://github.com/AbsolutionAI/aspen-paperclip-blueprints) | Apache-2.0 |
| [aspen-ce-gates](https://github.com/AbsolutionAI/aspen-ce-gates) | Apache-2.0 |
| [aspen-model-routing](https://github.com/AbsolutionAI/aspen-model-routing) | Apache-2.0 |
| [aspen-agent-runtime](https://github.com/AbsolutionAI/aspen-agent-runtime) | Apache-2.0 (boundary/pointer) |
| [aspen-dashboard](https://github.com/AbsolutionAI/aspen-dashboard) | Apache-2.0 (boundary/pointer) |
| [aspen-matrix-ops](https://github.com/AbsolutionAI/aspen-matrix-ops) | Apache-2.0 docs-only |
| [aspen-security-baseline](https://github.com/AbsolutionAI/aspen-security-baseline) | Apache-2.0 |
| [aspen-agent-personas](https://github.com/AbsolutionAI/aspen-agent-personas) | Apache-2.0 |
| [aspen-sherlock-tool](https://github.com/AbsolutionAI/aspen-sherlock-tool) | MIT wrapper notes |

### Products (MIT) — all normalized `make smoke`
| Repo |
|------|
| [api-boilerplate](https://github.com/AbsolutionAI/api-boilerplate) |
| [saas-starter-kit](https://github.com/AbsolutionAI/saas-starter-kit) |
| [cli-scaffold-tool](https://github.com/AbsolutionAI/cli-scaffold-tool) |
| [react-admin-template](https://github.com/AbsolutionAI/react-admin-template) |
| [tailwind-component-pack](https://github.com/AbsolutionAI/tailwind-component-pack) |
| [web-game-template](https://github.com/AbsolutionAI/web-game-template) |
| [pygame-platformer](https://github.com/AbsolutionAI/pygame-platformer) |
| [godot-rpg-template](https://github.com/AbsolutionAI/godot-rpg-template) |
| [social-automation](https://github.com/AbsolutionAI/social-automation) |
| [gumroad-assets](https://github.com/AbsolutionAI/gumroad-assets) |

### Commerce / OS
| Repo | Notes |
|------|-------|
| [aspen-commerce-playbooks](https://github.com/AbsolutionAI/aspen-commerce-playbooks) | Marketing docs |
| [AspenOS](https://github.com/AbsolutionAI/AspenOS) | Full OS tree |
| [agnetic-os](https://github.com/AbsolutionAI/agnetic-os) | Prior lineage |
| [worldmonitor](https://github.com/AbsolutionAI/worldmonitor) | Fork |
| [fleetmdm](https://github.com/AbsolutionAI/fleetmdm) | Fork |

---

## Hermes skill
`repo-documentation-standard` — packaging checklist for third-party repos.

---

## Future (not blocking v1)
- Slim extract of full agent runtime code into aspen-agent-runtime (beyond pointer)
- Full dashboard source extract into aspen-dashboard
- Private org migration for Leonardo/Family/abs-wm-mcp
- Product compose that vendors clones automatically

---

## Paperclip cos covered
ASP · ABSA · ABS · BEL Content — see aspen-paperclip-blueprints seed.

### Fleet / swarm / edge (BEL-179)
| Repo | Notes |
|------|-------|
| [aspen-swarm-manager](https://github.com/AbsolutionAI/aspen-swarm-manager) | Mission graph + arm gate |
| [aspen-edge-rrm](https://github.com/AbsolutionAI/aspen-edge-rrm) | Edge RRM + micro-agents + fleet E2E |

### Cognitive plugin (ADR-0005)
| Repo | Notes |
|------|-------|
| [aspen-langgraph-worker](https://github.com/AbsolutionAI/aspen-langgraph-worker) | LangGraph-style graphs; propose_act only; Paperclip stays aspen-dev |

### Adjacent products (2026-08-10)
| Repo | Notes |
|------|-------|
| [epos-human](https://github.com/AbsolutionAI/epos-human) | Epichuman Chrome MV3 scaffold |
| [aspen-pcake](https://github.com/AbsolutionAI/aspen-pcake) | pcake vault+intent gateway MVP (≠ Aspen Sentinel) |
| Analysis | `docs/sor/products/ANALYSIS_epos_pcake.md` |
