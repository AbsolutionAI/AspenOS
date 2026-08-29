# Absolution Studios — X Marketing Pack (@sonofabsolution)

**Date:** 2026-08-03  
**Shop:** https://absolutionstudios.gumroad.com  
**Account:** @sonofabsolution  
**Status:** Drafts ready — post only after `xurl` OAuth for @sonofabsolution

## Gumroad live snapshot
- **6 published** for sale (0 sales so far)
- **3 held** unpublished (quality blockers / verification)
- Local ZIPs present for 7 products under `gumroad-zips/` (small packages)

### Live
- **Tailwind Component Pack** — $29 — https://absolutionstudios.gumroad.com/l/tailwind-component-pack
- **API Boilerplate** — $39 — https://absolutionstudios.gumroad.com/l/api-boilerplate
- **Pygame Platformer Template** — $39 — https://absolutionstudios.gumroad.com/l/pygame-platformer
- **React Admin Dashboard** — $49 — https://absolutionstudios.gumroad.com/l/react-admin-template
- **Web Game Template (Phaser 3)** — $49 — https://absolutionstudios.gumroad.com/l/web-game-template
- **Godot 4 RPG Template** — $79 — https://absolutionstudios.gumroad.com/l/godot-rpg-template

### Hold (do not promote yet)
- **Social Automation** — $39 — draft/unpublished — verify LLM/posting paths — https://absolutionstudios.gumroad.com/l/social-automation
- **SaaS Starter Kit** — $79 — BLOCKER — empty frontend — https://absolutionstudios.gumroad.com/l/saas-starter-kit
- **create-turbo-stack** — $19 — BLOCKER — incomplete scaffold — https://absolutionstudios.gumroad.com/l/cli-scaffold-tool

---
## Posting cadence (recommended)
1. **Day 0 — Brand intro** (1 post)
2. **Days 1–6 — One product spotlight/day** (6 posts)
3. **Day 7 — Bundle / shop pin** (1 post)
4. Optional: reply-thread under each spotlight with feature bullets

Stay under X free/API rate limits. Prefer quality over volume.

---
## Post 0 — Intro (pin candidate)

```
Building tools for makers who ship.

Absolution Studios just dropped a suite of production-ready templates on Gumroad — games, APIs, dashboards, UI packs.

No fluff. Clone, customize, launch.

Shop → https://absolutionstudios.gumroad.com

#buildinpublic #indiedev #webdev #gamedev
```

Chars: 280 / 280

---
## Post 1 — Tailwind Component Pack

```
30 production-ready Tailwind components — dark mode, responsive, copy-paste fast.

$29 on Gumroad → https://absolutionstudios.gumroad.com/l/tailwind-component-pack

From @sonofabsolution / Absolution Studios

#TailwindCSS #webdev #frontend #buildinpublic
```

Chars: 254 / 280

---
## Post 2 — API Boilerplate

```
Express + Prisma + JWT + rate limits + tests. Ship your API without the weekend of setup.

$39 on Gumroad → https://absolutionstudios.gumroad.com/l/api-boilerplate

From @sonofabsolution / Absolution Studios

#nodejs #API #backend #buildinpublic
```

Chars: 245 / 280

---
## Post 3 — Pygame Platformer Template

```
2D platformer foundation: enemies, coins, particles. Jump into game logic, not boilerplate.

$39 on Gumroad → https://absolutionstudios.gumroad.com/l/pygame-platformer

From @sonofabsolution / Absolution Studios

#pygame #gamedev #python #indiedev
```

Chars: 247 / 280

---
## Post 4 — React Admin Dashboard

```
TypeScript + Tailwind admin dashboard with dark mode and charts. Start your SaaS UI today.

$49 on Gumroad → https://absolutionstudios.gumroad.com/l/react-admin-template

From @sonofabsolution / Absolution Studios

#ReactJS #TypeScript #SaaS #webdev
```

Chars: 249 / 280

---
## Post 5 — Web Game Template (Phaser 3)

```
Endless runner in TypeScript + Phaser 3. Browser game scaffold you can actually ship.

$49 on Gumroad → https://absolutionstudios.gumroad.com/l/web-game-template

From @sonofabsolution / Absolution Studios

#gamedev #TypeScript #Phaser #indiedev
```

Chars: 245 / 280

---
## Post 6 — Godot 4 RPG Template

```
Action RPG foundation with state-machine AI. Skip months of Godot architecture pain.

$79 on Gumroad → https://absolutionstudios.gumroad.com/l/godot-rpg-template

From @sonofabsolution / Absolution Studios

#Godot4 #gamedev #RPG #indiedev
```

Chars: 238 / 280

---
## Post 7 — Shop roundup

```
All live Absolution Studios templates:

• Tailwind components — $29
• API boilerplate — $39
• Pygame platformer — $39
• React admin — $49
• Phaser runner — $49
• Godot 4 RPG — $79

https://absolutionstudios.gumroad.com

#buildinpublic
```

Chars: 234 / 280

---
## X auth setup (you run once on the server)

```bash
export PATH="$HOME/.local/bin:$PATH"
# 1) Create app at https://developer.x.com — type: Web app / bot
# 2) Redirect URI: http://localhost:8080/callback
xurl auth apps add sonofabsolution --client-id 'YOUR_CLIENT_ID' --client-secret 'YOUR_CLIENT_SECRET'
xurl auth oauth2 --app sonofabsolution sonofabsolution
xurl auth default sonofabsolution sonofabsolution
xurl auth status
xurl whoami
```

Then tell Aspen: **post the marketing pack** — we will fire Post 0 + schedule/product posts.

---
## Safety

- Human approval already granted for marketing direction; still confirm before first live post if desired.
- Do not promote held/blocker products.
- Never put API secrets in tweets or Paperclip comments.
