---
slot: wed-2026w35
pillar: practical-tool-use
theme: week-4-tools-with-scars
cta: soft
status: draft
created: 2026-08-26
---

# Wed Aug 26 — The routing decision you learn to make

## Draft post

An operator note from four months of agent fleet bills:

We route agent requests across three model tiers — a fast model for most calls, a heavy model for synthesis, and a specialized one for structured tool output. The routing config is 8 lines of YAML. The routing rules took four months of invoices to learn.

Three heuristics that survived:

1. **Fast model for anything that loops.** Agents that retry, poll, or cascade don't get expensive inference. The cost of one heavy evaluation on a retry path can exceed a week of fast-model calls.

2. **Heavy model for the merge point.** When multiple agents' outputs converge into a single decision — board review, incident summary, release note — that's where the expensive route earns its keep. One correct synthesis is worth ten correct drafts that never got combined.

3. **Tool calls run on the cheapest tier that reliably returns structured JSON.** We learned this one the hard way: paying for philosophical depth on a `{"status":"ok"}` response.

The config file is still 8 lines. The scars are in the deployment notes.

Free kit drops + notes → https://absolutionstudios.gumroad.com/subscribe

## Rationale

- **Wednesday slot:** Practical tool use pillar — model routing is a concrete tool workflow with a failure arc
- **Week 4 theme (Tools With Scars):** the routing rules were forged by four months of invoices; the scar (overpaying for structured JSON) is the core of the third heuristic
- **Operator note format:** 7 substantive lines, three actionable heuristics, one hard-learned lesson per bullet
- **First-party proof:** real multi-tier model routing on this fleet (Flash → heavy → tool-specialist), real billing scars
- **Soft CTA:** Wednesday rule — soft subscribe link, matching the Aug 19 Wednesday pattern
- **Voice:** calm, precise, systems-minded — no hashtags, no emoji chains, no hype
- **Pillar health check:** This is pillar 5 (practical tool use) at 10% target; pillars 1–3 combined remain above 50% across the 4-week rolling window per strategy section 4

## Approve protocol
Human: reply `post it`, `skip`, or `revise: …`
