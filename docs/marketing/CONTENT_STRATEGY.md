# Absolution Studios — X growth & content strategy

**Owner:** Content Studio (lead) + Digital Marketer (ABSA when unpaused)  
**Brand account:** [@sonofabsolution](https://x.com/sonofabsolution)  
**Shop:** [absolutionstudios.gumroad.com](https://absolutionstudios.gumroad.com)  
**Updated:** 2026-08-04  
**Cadence:** **3 posts/week** (Mon / Wed / Fri) — draft automated, **human approve before post**

---

## 1. Market definition

### Primary ICP
**Indie builders who sell or ship software** — solo founders, small product studios, freelancers who:

- Rebuild the same admin/API/UI scaffold too often  
- Buy templates to skip weeks of setup  
- Live on X / Discord / Indie Hackers  
- Pay $29–$79 for a clear ZIP + README  

### Secondary ICP
- Game / creative coders (pygame, web game, Godot SKUs)  
- Automation-curious creators (social tooling — only when ON)  

### Not our market (yet)
- Enterprise procurement  
- Pure “AI hype” audiences with no ship intent  
- Follow-for-follow spam circles  

### Positioning
> Templates that ship. Stop scaffolding. Start selling.

**Category:** builder tools / digital products  
**Proof:** working ZIPs, MIT-friendly licenses, honest dry-run defaults  

---

## 2. Growth model (follower base + engagement)

### North-star metrics (90 days)
| Metric | Target |
|--------|--------|
| Followers | 500+ (quality over vanity) |
| Profile visits / week | trending up with each CTA week |
| Engagement rate | replies + bookmarks > empty likes |
| Gumroad visits from X | track UTM `?wanted=true` + referrer notes |
| Sales attributed | first $1 of verified revenue |

### Flywheel
1. **Value posts** (teach / show / contrast) → follows  
2. **Community replies** on builder accounts → profile clicks  
3. **Proof posts** (ship logs, template guts) → trust  
4. **Soft CTA** to live Gumroad SKU → visits  
5. **Hard CTA** 1×/week max → conversion  

### Engagement rules (daily 15–25 min or agent-drafted reply bank)
- Reply to 5–10 posts in ICP feeds (not “great post!” — add one concrete tip)  
- Quote-tweet rare; prefer original  
- Never buy followers / engagement pods  
- Soft block spam; mute crypto junk by default  

---

## 3. Accounts to follow (viability + adjacency)

Curate **~40–80** accounts max in the following bands. Re-audit monthly.

### A. Builder / indie (distribution + peers)
- Indie Hackers ecosystem voices, solo SaaS shippers  
- Template/boilerplate makers (peers, not copycats)  
- “Build in public” engineers with real product screenshots  

### B. Technical taste-makers (credibility)
- React / Node / DX educators  
- Game-dev educators (for game SKUs)  
- Open-source maintainers whose tools we compose with  

### C. Marketplace / monetization
- Gumroad operator voices  
- Creator-economy operators who talk packaging & pricing (not gurus)  

### D. Avoid following
- Mass-follow bots  
- Pure engagement bait  
- Off-ICP politics as primary content  

**Ops:** maintain live list in `FOLLOW_LIST.md` (handles only; refresh quarterly).

---

## 4. Content pillars (high value, authentic)

| Pillar | % | Examples |
|--------|---|----------|
| **Ship craft** | 35% | “What’s in a real SaaS admin ZIP”, folder trees, anti-patterns |
| **Builder pain** | 25% | “You don’t need another blank Vite repo”, time-cost math |
| **Proof / build log** | 20% | Screenshots, before/after, “we held SKU X until code existed” |
| **Product spotlight** | 15% | One **live** SKU only — benefit + price + link |
| **Funnel / shop** | 5% | Shop roundup, “start here” map |

### Formats
- Single punchy posts (most days)  
- 5-beat threads (1×/week max)  
- Reply-thread under our own CTA for FAQ  

### Never
- Fake MRR / fake social proof  
- CTA to **unpublished** SKUs (saas/cli/social until ON)  
- Unattended controversial posts  

---

## 5. Converting profile

### Bio (pick one; max ~160 chars)
**A:** `Templates that ship. React · API · games. Stop scaffolding → start selling. 👇`  
**B:** `Builder kits for indies. Admin, API, UI, game starters. Gumroad below.`  

### Profile setup checklist
- [ ] Display name: **Absolution Studios**  
- [ ] Handle: **@sonofabsolution**  
- [ ] Avatar: simple mark (not default egg)  
- [ ] Header: dark UI + “templates that ship”  
- [ ] Location / link: **https://absolutionstudios.gumroad.com**  
- [ ] Pinned post: best proof + shop link (update monthly)  

### Pinned post recipe
1. Who it’s for (one line)  
2. What we sell (3 bullets of live categories)  
3. Link shop  
4. “New drops announced here”  

---

## 6. Funnel

```
X content / replies
    → Profile (bio + pin)
        → Gumroad shop
            → Live SKU page
                → Purchase → email delivery
```

### CTA ladder
| Warmth | CTA |
|--------|-----|
| Cold | Follow + value; no link |
| Warm | “Full kit on Gumroad” + shop |
| Hot | Single SKU link + price |

### Default SKU priority (while 3 OFF)
1. **react-admin-template** ($49) — broad  
2. **api-boilerplate** ($39)  
3. **tailwind-component-pack** ($29) — impulse  
4. Game SKUs for game-content days  

UTM example:  
`https://absolutionstudios.gumroad.com/l/react-admin-template?wanted=true`

---

## 7. Cadence: 3× per week

| Day | Focus | CTA strength |
|-----|--------|--------------|
| **Mon** | Ship craft / pain | Soft or none |
| **Wed** | Proof / build log | Soft shop |
| **Fri** | Product spotlight (live SKU) | Hard SKU link |

### Automation
- Hermes cron **Mon/Wed/Fri 10:00 MDT** drafts 1 post (+ optional reply bank)  
- Delivers to Matrix for **human approve**  
- On approve: operator says `post it` → xurl `--app sonofabsolution-market`  
- **No auto-post** without explicit approve  

### Weekly human 20-min review
- Approve/reject 3 drafts  
- Spot-check follows  
- One metric glance (followers, profile visits if available)  

---

## 8. Team ownership

| Role | Company | Responsibility |
|------|---------|----------------|
| **Content Lead** | Content Studio | Strategy adherence, calendar, voice |
| **Digital Marketer** | ABSA (when unpaused) | SKU copy, CTA tests, pack updates |
| **Captain (human)** | — | Approve posts, profile visuals, budget |
| **Aspen** | ASP | Cron, xurl, Linear hygiene |

ABSA is **paused** on budget override — strategy + drafts run via **Content Studio + Hermes cron** until unpaused.

---

## 9. First 14 days (execute)

1. Apply bio + pin + header  
2. Follow list v1 (40 accounts)  
3. Mon/Wed/Fri drafts live via cron  
4. One hard CTA/week (Fri)  
5. Do not expand to IG/TikTok until X converts  

---

## 10. Success / kill criteria

**Continue if** week-4: engagement on value posts + any shop click-through  
**Adjust if** only vanity likes, zero profile clicks  
**Pause paid experiments** until organic CTA converts once  
