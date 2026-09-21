# ASP-628 — ADR-0009 residual: gatekeeper production packaging placement

**Status:** DECISION RECORDED (plan-only under freeze)  
**Issue:** ASP-628 · Parent ASP-627 · Linear BEL-215 residual (packaging only)  
**ADRs:** ADR-0009 (Accepted P1+P2) · ADR-0004 · ADR-0008  
**Author:** aspen · **Date:** 2026-09-21  
**Mode:** Architecture decision — **no production image change this ticket**

---

## 1. Question

Where does monorepo `src/python/gatekeeper/` land in **production** images?

| Option | Meaning |
|--------|---------|
| **A. Edge-adjacent plugin** | Optional package, loadable per plant profile |
| **B. Core-edge binary** | Always-on in every AspenOS / edge install |

Also note: durable token backend (in-memory → Redis/PG) is **later** — not DoD under freeze.

---

## 2. Decision (recorded)

**Primary package = Plugin (`aspen-gatekeeper`), classification = `plugin`.**  
**Default install profile = ON for any plant with actuators; OFF only for observation-only / Light-read profiles.**  
**Do not ship a second always-on core-edge gatekeeper binary.**

### Why not pure core-edge (B)

1. **ADR-0004 light core** — kernel stays agent loop, policy interfaces, envelopes, health, bus **interfaces**, safety estop path. Full capability-token / credential-strip / NATS grant stack is loadable capability, not kernel mass.
2. **ADR-0008** — Core = minimal runtime surface. Gatekeeper P1+P2 is ~2k LOC + NATS client surface; packing it into every image expands attack surface without Captain approval (ticket DoD forbids silent expand).
3. **G8 hard path already lives in edge-rrm** (`DualHumanGate`) — physical/sim act dual-human is **not** owned by the monorepo shim. Duplicating that as a second always-on binary creates two SPFs and confuses SoR.
4. **PACKAGES.md already lists** `aspen-safety` (estop, propose_act enforcement) as **Core** and `gatekeeper/minimal_shim.py` as **dev prototype**. Graduation path is prototype → **plugin**, not prototype → core fork.

### Why plugin-first (A), with profile default ON for actuators

1. **Modular profiles (ADR-0009 principle 4)** — Light Cell vs Full Plant activate caps via plant profile; plugin + profile matches that model.
2. **Optional per plant** — observation-only cells / lab dashboards can omit the full proxy stack; actuator plants **must** install it (profile default).
3. **Extraction path** — monorepo `src/python/gatekeeper/` remains the **source of truth** until `aspen-gatekeeper` is cut as its own package (same pattern as edge-rrm / swarm-manager). No Paperclip ownership.
4. **Attack surface** — plugin install is an explicit plant choice; core images stay smaller until packaging sprint + Captain sign-off on image matrix.

### Safety fail-closed residual (non-negotiable)

| Layer | Owner | Always present? |
|-------|-------|-----------------|
| E-stop + dual `authorize_clear` | **Core** `aspen-safety` + bus contract | Yes |
| G8 dual-human on edge command path | **Plugin** `aspen-edge-rrm` (already) | On any edge that can arm |
| Capability tokens, credential-strip proxy, authz gate, rate limits | **Plugin** `aspen-gatekeeper` (this decision) | Default ON if plant has actuators |
| Bare `propose_act` without dual-human on safety subjects | Refused by gatekeeper **when loaded**; edge-rrm G8 remains last line on command path | — |

**Rule:** A plant profile that enables actuation **requires** `aspen-gatekeeper` (or equivalent) in the image set. Packaging CI should eventually assert that (follow-up; not this ticket’s image change).

---

## 3. Classification row (PACKAGES.md)

| Name | Tier | Notes |
|------|------|-------|
| `aspen-gatekeeper` | **Plugin** | Production candidate for monorepo `src/python/gatekeeper/` (P1+P2 + ASP-607 rate limits) |
| `gatekeeper/minimal_shim.py` (path) | **Dev-only** (transitional) | Remains monorepo path until package extract; not a second product name |
| `aspen-safety` | **Core** | Unchanged — estop + propose_act **enforcement contracts**; not the full token/proxy stack |

Reclassify: remove “gatekeeper-shim (dev)” as the **only** long-term home; keep monorepo path as **source** until extract, document plugin name as the production target.

---

## 4. Out of scope (explicit)

- Redesign of propose_act / dual-human / token **semantics** (locked ADR-0009)
- Durable token backend Redis/PG (later eng ticket)
- Live Hermes credential strip on every profile (child later)
- Physical cell / ADR-0012
- Changing `scripts/build-deb.sh` / ISO / production Dockerfiles **this ticket**
- Live NATS restart or nkey rotate

---

## 5. Follow-up eng (not started here)

When packaging sprint is free (Captain / freeze lift for image work):

1. Cut `aspen-gatekeeper` package skeleton (`pyproject.toml` `classification = "plugin"`, manifest capabilities).
2. Wire plant-profile default: actuator profiles include plugin; observation-only omit.
3. H-019 / nightly: assert actuator profile images do not ship without gatekeeper; assert core image does not pull dev-only paths.
4. Optional child: durable token store design spike (still fail-closed on process restart under freeze = in-memory OK for sim).

---

## 6. Acceptance (this ticket)

- [x] Plan under `docs/plans/` with placement recommendation
- [x] `docs/PACKAGES.md` classification row for `aspen-gatekeeper` (plugin)
- [x] No production image change without Captain (none made)
- [x] ADR-0009 packaging residual line points at this decision

**Verdict:** **Edge-adjacent plugin (`aspen-gatekeeper`), profile-default ON for actuator plants. Core keeps safety contracts only. No image expand this heartbeat.**
