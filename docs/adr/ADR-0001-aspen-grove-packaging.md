# ADR-0001: Aspen Grove GitHub packaging

## Status
Accepted — 2026-08-05

## Context
The live stack (Paperclip multi-company, Hermes multi-profile, Matrix, Gumroad products, OSINT/security trees) must be reviewable by third parties as **standalone tools** and composable as **C2**. Secrets and family/Leonardo surfaces cannot be public.

## Decision
1. **Grove architecture:** packages by layer (contracts → runtime → products → compose).  
2. **Meta-repo name:** `aspen-grove`.  
3. **Licenses:** MIT products; Apache-2.0 runtime/control/contracts.  
4. **Org:** Prefer public/private org split; until available, use **AbsolutionAI** with private repos / `aspen-private-*` names.  
5. **Matrix homeserver:** documentation package only (no live DB/certs).  
6. **Leonardo + Family:** private.  
7. **Order:** map → contracts → products → runtime → compose.  
8. **SoR:** Linear for work; PACKAGE_MAP for repo identity; no secrets in git.

## Consequences
- Extract work is documentation-heavy first, then thin public blueprints.  
- Product repos get CI/third-party smoke before deep runtime splits.  
- Private org migration is a later rename, not a blocker.

## Alternatives rejected
- Single monorepo dump of `~` (secret risk, unusable).  
- Public Matrix production image (abuse + data risk).  
- Delaying all packaging until private org exists.
