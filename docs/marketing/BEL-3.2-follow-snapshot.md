# BEL-3.2 follow expansion — progress snapshot
## Blocked: OAuth2 follows.write scope required

**Created:** 2026-08-04 | **By:** Content Lead (agent 603c13cd)
**Issue:** BEL-5 → BEL-3.2
**Status:** BLOCKED — awaiting human re-auth

---

## What's done

- FOLLOW_LIST.md v2 reviewed and validated — 26 target accounts across 6 categories
- Follow list expansion strategy agreed: agent infra first, then industrial AI, robotics, builders
- Current follow state captured: **35 game publishers** (all off-ICP — leftover from Gumroad-first strategy)
- Root cause of 403 Forbidden isolated: OAuth2 scope gap

## What's blocked (all of it)

All follow/unfollow operations return **403 Forbidden** because the `sonofabsolution-market` app's OAuth2 user context token lacks the `follows.write` scope. The X API v2 `/2/users/:id/following` endpoint requires this scope for both follow and unfollow.

Two apps authenticated as `@sonofabsolution`:
| App | Read | Follow/Unfollow | Issue |
|-----|------|----------------|-------|
| `sonofabsolution-market` | ✓ OAuth2 | ✗ 403 Forbidden | Missing `follows.write` scope |
| `sonofabsolution` | ✓ OAuth2 | ✗ 402 Credits Depleted | No X API credits |

## To unblock

Human must re-authenticate the `sonofabsolution-market` app with `follows.write`:

```bash
HOME=/home/tech xurl auth oauth2 --app sonofabsolution-market --headless
```

When the OAuth consent screen appears, the authorization URL must include `follows.write` in the `scope` parameter. If the X Developer Portal app doesn't have this permission enabled, the human must:
1. Go to https://developer.x.com/en/portal/dashboard
2. Find the `sonofabsolution-market` app
3. Under "User authentication settings" → "App permissions" → check **Follows Read and Write**
4. Save, then re-run the OAuth2 flow

## Ready to execute once unblocked

### Unfollow (35 accounts — all stale game publishers)
MrBeast, InfinityWard, idSoftware, Bungie, Steam, XBOX, Activision, FinalFantasy, NoMansSky, 007GameIOI, CallofDuty, bethesda, geoffkeighley, TeamNINJAStudio, Ubisoft, Naughty_Dog, Metalgear, HIDEO_KOJIMA_EN, Konami, platinumgames, PlayStation, EmbarkStudios, FortniteGame, RE_Games, NintendoAmerica, EA, RockstarGames, tombraider, Pixar, animationguild, adultswim, CartoonNonStop, Dreamworks, itzazfar, devvitorrs

### Follow (26 accounts — prioritized)
1. **Agent infra (PRIORITY):** karpathy, swyx, simonw, hwchase17, LangChainAI, llama_index, ollama, OpenRouterAI, vllm_project, huggingface
2. **Evaluation:** eugeneyan, chipro
3. **Manufacturing:** ISA_Interchange, RockwellAuto, Siemens
4. **Robotics:** BostonDynamics, OpenRoboticsOrg, IntrinsicAI
5. **Builders:** levelsio, marc_louvion, t3dotgg, shadcn, gumroad, sahil
6. **Games (light):** godotengine, pygame

### Expected result
After successful follow: 26 new ICP-aligned follows, 0 stale game publisher follows.
Total follows: ~26 (down from 35 — healthy pruning)