# Product analysis — epos-human + pcake stack

**Date:** 2026-08-10  
**Sources:** `docs/sor/products/epos-human/`, `docs/sor/products/pcake-stack/`  
**Grove SoR:** Master Spec v4.0 still wins on organ naming.

---

## 1. epos-human (working brand: Epichuman)

### What it is
MV3 **Chrome extension** — AI productivity hub: bookmarks/tabs, multi-LLM assist, sidebar live help, workspace hooks, **Hermes / agent mesh** interaction. Positioned as broader than Superhuman (email-only).

### Pillars
| Pillar | Detail |
|--------|--------|
| Bookmark & tab AI | Organize, search, group with LLM |
| Multi-LLM | OpenAI, Claude, Grok, Gemini, local |
| NL search | Bookmarks, tabs, later mail/docs |
| Sidebar widgets | Contextual help, troubleshooting |
| Agent bridge | Hermes, Grok CLI, Agent Zero, etc. |
| Workspace (later) | Calendar, email, Drive |

### Architecture (from source)
- **UI:** popup + side panel (React)
- **Background:** activity monitor, LLM router, prefs
- **Content scripts:** page context
- **Storage:** `chrome.storage.local` / IndexedDB
- **Manifest V3**

### Phased delivery (source roadmap)
1. Bookmark/tab AI + multi-LLM  
2. Activity monitoring + contextual assist + agent hooks  
3. Workspace integrations  
4. Widgets / polish  
5. OSS + Chrome Web Store  

### Fork / extend candidates (source)
SmartTab, bookmark-ai-organizer / MarkMind-class projects, modular LLM backends.

### Grove fit
- **Sellable product lane** (Gumroad / CWS) — not AspenOS edge runtime  
- Agent bridge should call **Hermes gateway** / Matrix, not embed plant actuators  
- Privacy-first: local storage default; cloud LLM opt-in  

### Risks
- Scope creep (full Superhuman+workspace)  
- Chrome permission review / store policy  
- Cost if default cloud LLM without freeze-aware routing  
- Branding: “Epichuman” vs Superhuman — keep distinct  

### Suggested MVP (for Linear)
Ship **MV3 shell + bookmark/tab list + one LLM provider + side panel chat stub + Hermes webhook optional**. No full workspace.

---

## 2. pcake stack (source working name: “Sentinel”)

### Naming collision
Master Spec **Aspen Sentinel** = HITL C2 / OSINT ops workspace.  
Source doc’s “Sentinel” = **credential vault + intent-gated agent gateway**.  

**Canonical product name here: `pcake` / package `aspen-pcake`.**  
Do not rename Aspen Sentinel. In docs, call the gateway **pcake** (or “P-Cake gateway”).

### What it is
Four pillars in one portable daemon:

1. **Encrypted credential vault** (agents never see secrets)  
2. **Transparent HTTPS proxy** credential injection (no SDK)  
3. **Intent-based access control** — use-case scoped (not only agent→API)  
4. **Portability** — binary/daemon any machine; optional MCP server face  

Inspired by OneCLI, Agentgateway, Portkey, AgentLair, Cerbos/Oso/IBAC.

### Core request path
```
Agent HTTPS → pcake proxy
  → auth agent token
  → intent match (method/host/path/body shape)
  → policy check (RBAC/ABAC)
  → vault retrieve allowed credential
  → inject + forward
  → audit log
```

### Major components (from source)
| Component | Role | Tech lean (source) |
|-----------|------|---------------------|
| Vault core | AES-GCM entries, argon2 master | Rust |
| Intent matcher | Declarative rules | Deterministic (no LLM at request time) |
| Policy engine | Cedar / OPA-class | Rust crate |
| HTTPS proxy | Local :7331-style | Tokio/Hyper |
| MCP server | Optional tool face | MCP Rust SDK |
| Admin CLI | Vault/policy mgmt | clap |
| Audit store | SQLite WAL | |
| Federation | Root vault + leaf cache | Later |

### Grove fit
- Complements **aspen-dev** / Paperclip: secrets out of agent env  
- Complements **Hermes MCP**: gateway can front tools with intent scopes  
- Aligns with Master Spec **propose_act / dual-auth** culture — pcake is *network/credential* gate, not plant safety  
- Distinct from Aspen Sentinel UI  

### Risks
- MITM proxy trust UX on every machine  
- Rust scope vs freeze — start with **thin Go/Python MVP** or stub policy if Rust timeline long  
- Overlap with existing hermes secrets / Paperclip env — need one SoR for secrets  
- Source includes large generated Rust sketches — treat as **design ref**, not drop-in prod  

### Suggested MVP (for Linear)
1. Vault encrypt/decrypt CLI (file-based)  
2. Intent YAML rules  
3. Local reverse-proxy inject for one host (e.g. api.github.com)  
4. Audit JSONL  
5. Doc: how Hermes points `HTTPS_PROXY` at pcake  

---

## 3. Relationship map

```
epos-human (browser UX)
    │  optional
    ▼
Hermes / Matrix gateway ──► Paperclip (aspen-dev work)
    │
    ▼
pcake (credential + intent gateway) ──► external APIs
    │
AspenOS / swarm / RRM  (separate safety bus; not through browser ext)
```

### Shared principles
- Local-first / privacy  
- Agents don’t hold long-lived raw secrets  
- Modular LLM backends  
- OSS core + optional commercial  

### Priority under freeze
| Product | Priority | Why |
|---------|----------|-----|
| **pcake** MVP | Medium-high for aspen-dev security | Unblocks clean agent API use without secret sprawl |
| **epos-human** MVP | Medium | Revenue/CWS potential; larger UX surface |
| Full pcake federation / epos workspace | Low until cash flow | |

---

## 4. Repo plan
| Repo | License lean | Contents |
|------|--------------|----------|
| `epos-human` | MIT (product) | MV3 scaffold, docs, ANALYSIS pointer |
| `aspen-pcake` | Apache-2.0 (runtime/security) | Vault/proxy MVP scaffold, policies examples, SoR links |

Sources remain under `aspen-os/docs/sor/products/`.
