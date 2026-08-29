---
slot: wed-2026w34
pillar: manufacturing-aspen-thesis
theme: week-3-plant-first-software
cta: soft
status: draft
created: 2026-08-19
---

# Wed Aug 19 — Plant-first software: the 5-minute operator status principle

## Draft post

A design rule from building Aspen OS's industrial dashboard:

**Every machine/process/agent on a plant floor must be readable within 5 minutes by someone who has never seen your UI.**

Not 5 minutes to understand the whole system. 5 minutes to answer one question: "Is anything wrong right now?"

We built three things to satisfy this:

1. A health raster — color-coded grid of every subsystem, readable at a glance. Green means "no news." Red means "open this."
2. An incidents panel that surfaces the last actionable event per node — not every log line.
3. A telemetry view that shows the current reading and the 5-minute delta. Not the 30-day trend, not the raw feed — just "was it stable in the last 5 minutes?"

The hardest part was removing information. Every engineer wanted to show their subsystem's full state. The 5-minute rule forced us to decide what an operator actually acts on versus what they use for debugging.

We now apply the same filter to agent fleet dashboards and eval summary views. If it takes more than 5 minutes to find the red node, the UI failed — not the operator.

Free kit drops + notes → https://absolutionstudios.gumroad.com/subscribe

## Rationale

- **Wednesday slot:** Manufacturing/Aspen pillar — the Aspen OS industrial dashboard is the first-party proof
- **Week 3 theme (Plant-First Software):** local-first design pattern, operator-oriented status model, integration honesty (we removed data, didn't add it)
- **Operator note format:** 7 substantive lines, concrete design rule with implementation detail
- **First-party proof:** built from actual Aspen OS dashboard architecture — health raster, incidents panel, telemetry view
- **No hard CTA:** Wednesday rule — only soft subscribe link (standing permission per calendar)
- **Voice:** calm, precise, systems-minded — no hashtags, no emoji chains, no empty promises
- **Bridge to agent fleets:** last paragraph connects the plant-floor rule back to the Monday audience (agent operators), keeping the feed coherent pillar-to-pillar

## Approve protocol
Human: reply `post it`, `skip`, or `revise: …`
