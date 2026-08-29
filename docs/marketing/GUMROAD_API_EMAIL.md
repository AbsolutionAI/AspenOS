# Gumroad API — email / subscribers (live check 2026-08-06)

**Shop subscribe page:** https://absolutionstudios.gumroad.com/subscribe

## What our token can do today
| Endpoint | Result |
|----------|--------|
| `GET /v2/user` | OK |
| `GET /v2/products` | OK |
| `GET /v2/sales` | OK (empty until sales; sales payloads include buyer email when present) |
| `GET /v2/products/{product_id}/subscribers` | OK — membership/subscription product subscribers |
| `GET /v2/subscribers` (global) | **404** — no global audience dump on this path |

## What that means
- **Yes (limited):** We can read **product subscribers** (by product id) and **sale buyer emails** after purchases via Sales API.
- **No (not found with current token/routes):** A single “export entire Gumroad audience / follow list emails” endpoint did not respond on `/subscribers`.
- **Sending email campaigns** is **not** via public product API — use Gumroad Workflows / dashboard (or Zapier → ESP).
- OAuth scope **edit_emails** (if granted on a new app token) may unlock more audience features — current token was not verified for that scope.

## Ops recommendation
1. Drive traffic to **https://absolutionstudios.gumroad.com/subscribe** for free list.
2. Use Gumroad Workflows for welcome sequence (dashboard).
3. After first sales: `GET /sales` for buyer emails if needed for support (not marketing spam).
4. Optional later: create token with `edit_emails` and re-probe audience APIs.

## X copy snippets
**Soft footer:**
```
Free drops + build notes → https://absolutionstudios.gumroad.com/subscribe
```

**Reply under hard CTA:**
```
Want the free list only? → https://absolutionstudios.gumroad.com/subscribe
```
