# Paperclip ↔ Linear company map

**Linear project:** [Paperclip Multi-Company Alignment](https://linear.app/bellahtech/project/paperclip-multi-company-alignment-40e24c5102ed)  
**Fiscal freeze:** $100/mo **total across all Paperclip companies** until Gumroad cash flow verified.  
**Priority:** Gumroad/marketing profitability → sustain → Aspen OS greenfield.

## Linear → Paperclip mapping

| Linear project | Team | Status | Paperclip company | Notes |
|----------------|------|--------|-------------------|-------|
| Gumroad Product Launch – Template Suite | BEL | In Progress | **Absolution Digital Commerce** | Revenue #1 |
| Digital Products Business | BEL | Backlog | **Absolution Digital Commerce** | |
| Affiliate Marketing Platform | BEL | Backlog | **Absolution Digital Commerce** | |
| Aspen OS Development | BEL | In Progress | **Aspen OS Development Company** | Exists (ASP) |
| Paperclip Agent Stack – Full Build | BEL | In Progress | **Aspen OS Development Company** | Stack meta |
| Paperclip Multi-Company Alignment | BEL | In Progress | **Aspen OS Development Company** | This program |
| Ship-Wide Security Audit — NIST CSF | BEL | Backlog | **Aspen OS** (Auditor agent) | No separate co |
| Andromeda Security — Rolling Audit | BEL | Backlog | **Aspen OS** (Auditor) | |
| Leonardo Balloch — AI Influencer Pipeline | BEL | Backlog | **Bellah Content Studio** | |
| OSINT Global Dashboard (OpenSINT) | BEL | In Progress | **Absolution Studios** | ABS-11 active |
| World Monitor Upstream Contributions | BEL | Backlog | **Absolution Studios** | ABS-11 upstream sync |
| Sherlock Username Enumeration | BEL | In Progress | **Absolution Studios** | ABS-17 active |
| Cybersecurity OSINT Integration | BEL | In Progress | **Absolution Studios** | ABS-13 active |
| Flamingo-stack / OpenFrame Integration | BEL | In Progress | **Absolution Studios** | ABS-15 active |
| Unified Command & Control Platform | BEL | In Progress | **Absolution Studios** | ABS-16 active |
| eXo Platform - Family Data Hub | FAM | Backlog | DEFER | After cash flow |
| OpenManus Enhancements | FAM | Backlog | DEFER | |
| Local Family AI Engine | FAM | Backlog | DEFER | |
| Initiative: Clawbot - Romi LLM training | — | Active | DEFER / Content later | |

## Company budgets (sum = $100)

| Company | Prefix | Monthly | Role |
|---------|--------|---------|------|
| Aspen OS Development Company | ASP | $40 | Platform + stack + security |
| Absolution Digital Commerce | **ABSA** | $35 | Gumroad + digital products |
| Bellah Content Studio | **BEL** (Paperclip prefix; avoid confusion with Linear BEL team) | $15 | Influencer + content marketing |

## Mirror convention

- Linear = system of record (BEL-N)
- Paperclip issue title/body includes `BEL-N` + Linear URL
- Human assignee on Linear; agent assignee on Paperclip
- Wake-on-demand only (no timer heartbeats)

## Alignment issues

BEL-142 … BEL-147 under Multi-Company Alignment project.

## Orphan note

- **Absolution Studios** (ABS) exists on disk/DB with $0 budget and only paused built-ins — board membership restored; leave dormant until a Linear vertical needs it.
- **Workspace routing (ASP-36):** ABS has **no separate product git root**. Agents for ABS and ASP both use `/home/tech/aspen-dev/repos/aspen-os`. Deliverable ownership is path-scoped — see `docs/ops/ABS_MIRROR_ROUTING.md`. Commerce/marketing/credentials/OSINT drafts are **local-only** (gitignored) so they cannot land on public `AbsolutionAI/AspenOS`.

## ABS mirror issues (Aspen OS Development vertical)

| Linear | ABS | Title | Status |
|--------|-----|-------|--------|
| BEL-153 | ABS-7 | Core agent mesh hardening | ✅ done |
| BEL-113 | ABS-8 | Compound Engineering gates | ✅ done |
| BEL-114 | ABS-9 | Security Auditor baseline | ✅ done |
| BEL-154 | ABS-10 | Shared Local Memory & Conversation Caching Layer | ✅ done |
| BEL-DEFER | ABS-11 | OSINT Global Dashboard — WorldMonitor fork | ✅ done |
| BEL-DEFER | ABS-12 | abs-worldmonitor-mcp | 🔄 in_progress |
| BEL-DEFER | ABS-13 | Cybersecurity OSINT Integration (paulveillard/cybersecurity-osint) | 🔄 in_progress |
| BEL-154 | ABS-14 | Local AI / Jarvis Integration | ⏸️ paused |
| BEL-DEFER | ABS-15 | Flamingo-stack / OpenFrame Integration | 🔄 in_progress |
| BEL-DEFER | ABS-16 | Unified Command & Control Platform | 🔄 in_progress |
| BEL-DEFER | ABS-17 | Sherlock Username Enumeration | 🔄 in_progress |

Mirror convention applied: Paperclip issues include `Linear: BEL-N` + URL in description.