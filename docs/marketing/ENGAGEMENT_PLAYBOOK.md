# Engagement playbook (BEL-150 / 158)

## API blocker
OAuth2 token on `sonofabsolution-market` can **post** but **follow returns 403 Forbidden**.
Likely missing `follows.write` (token was issued with a reduced scope set during OAuth debugging).

### Fix (human, ~2 min)
1. Developer portal → User auth settings → enable **follows.write** (+ like.write if you want auto-likes)
2. Re-authorize / regenerate user token with full scopes
3. Hand tokens to Aspen → retry follow batch

## Manual weekly habit (until API works)
- Follow **5–10**/week from `FOLLOW_LIST.md` v2
- Engage-then-follow; no mass-follow
- 5 substantive replies/week

## First follows (manual checklist)
- [ ] @simonw
- [ ] @swyx
- [ ] @karpathy
- [ ] @ollama
- [ ] @huggingface
- [ ] @vllm_project
- [ ] @shadcn
- [ ] @t3dotgg
- [ ] @gumroad
- [ ] @godotengine
- [ ] @levelsio
- [ ] @IntrinsicAI
- [ ] @OpenRoboticsOrg

## Reply starters
- Agents: “We gate model calls behind budget + start checks — how do you kill runaway loops?”
- Mfg: “Same idea as shift handoff checklists — written beats tribal knowledge.”
- Tools: “What’s the failure mode when the vendor API is down?”
- Eval: “Merge gated on golden-path eval, or vibes?”
