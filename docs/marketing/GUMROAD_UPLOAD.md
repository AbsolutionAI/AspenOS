# Gumroad upload — SaaS + CLI + Social (manual, ~3 minutes)

Gumroad’s public API **cannot attach product binaries**. Files must be uploaded in the seller dashboard. ZIPs are ready on disk and mirrored on GitHub.

## ZIP locations (server)

`/home/tech/Gumroad-dev/gumroad-products/gumroad-zips/`

- `saas-starter-kit.zip` (26K)
- `cli-scaffold-tool.zip` (26K)
- `social-automation.zip` (551K)
- `pygame-platformer.zip` (321K) — optional re-upload (strengthened levels)
- `api-boilerplate.zip` (48K) — optional refresh

## GitHub mirror (download anywhere)

Release: https://github.com/AbsolutionAI/gumroad-assets/releases/tag/v20260803-1

- https://github.com/AbsolutionAI/gumroad-assets/releases/download/v20260803-1/saas-starter-kit.zip
- https://github.com/AbsolutionAI/gumroad-assets/releases/download/v20260803-1/cli-scaffold-tool.zip
- https://github.com/AbsolutionAI/gumroad-assets/releases/download/v20260803-1/social-automation.zip
- https://github.com/AbsolutionAI/gumroad-assets/releases/download/v20260803-1/pygame-platformer.zip
- https://github.com/AbsolutionAI/gumroad-assets/releases/download/v20260803-1/api-boilerplate.zip

## Dashboard steps (per product)

1. Open product edit page:
   - SaaS: https://absolutionstudios.gumroad.com/l/saas-starter-kit  
   - CLI: https://absolutionstudios.gumroad.com/l/cli-scaffold-tool  
   - Social: https://absolutionstudios.gumroad.com/l/social-automation  
2. **Content** → remove old tiny/placeholder file if any  
3. Upload the matching ZIP from the release or server path  
4. Toggle **Published** ON  
5. Save  

After publish, tell Aspen **“gumroad published”** to verify via API and extend the X pack.

## Verified product quality (this pass)

| Product | Status |
|---------|--------|
| saas-starter-kit | Built + smoke (API tests, web build) |
| cli-scaffold-tool | Built + scaffold smoke (React/Vue/Svelte) |
| social-automation | Offline research, dry-run posts, xurl poster, tests path |
| pygame-platformer | 2 levels, pause, lives, win state |
