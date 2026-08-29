---
slot: mon-2026w35
pillar: ai-build-test-craft
theme: week-4-tools-with-scars
cta: none
status: draft
created: 2026-08-22
---

# Mon Aug 24 — The CE gate: forged from the code we shipped too fast

## Draft post

An operator note from building our agent fleet:

The most valuable review tool in our stack isn't a linter, a formatter, or a CI pipeline. It's one gate with a check box — a single question we have to answer before merge.

Before the Compound Engineering gate, every PR passed code review. Clean syntax, good structure, reasonable tests. And every now and then, code that satisfied all three still shipped the wrong thing. Not a bug. A design error. An assumption we'd already rejected in a prior session and forgot.

The CE gate asks exactly one question: "Does this change prove the claim its ticket makes?" If the ticket says "adds graceful degradation for API outages," the merge must show the error handler, the fallback path, and the restore logic — not just "coverage looks good."

The gate didn't arrive fully formed. It was forged by the scar of shipping a six-line change that took two days to revert. The tool didn't exist until the scar taught us what question to ask.

That's the pattern. You don't design review gates in theory. You collect the failures, extract the question that would have caught each one, and encode it.

Seven CE cycles later: fewer unpick merges, faster reviews (the question is known up front), and a catalog of failure-classes we can teach to new agents.

## Rationale

- **Monday slot:** AI build & test craft pillar — CE gates, "prove it before merge" pattern
- **Week 4 theme (Tools With Scars):** the gate was forged from a real shipping failure; the scar is the core of the story
- **Operator note format:** 8 substantive lines, concrete failure → fix arc
- **First-party proof:** real CE gate implementation on this fleet (Compound Engineering protocol)
- **No CTA** — Monday rule
- **Voice:** calm, precise, systems-minded — no hashtags, no emoji chains
- **Pillar health check:** Pillars 1–3 combined ~71% (>50%), this post sits in pillar 2 (AI build/test) which is at ~30% rolling — well within 20% target over 4 weeks

## Approve protocol
Human: reply `post it`, `skip`, or `revise: …`