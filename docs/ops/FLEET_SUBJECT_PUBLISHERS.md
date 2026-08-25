# Fleet subject publishers inventory (ASP-362)

**Paperclip:** ASP-362 (parent ASP-166 Weekly Architecture Review)  
**Date:** 2026-08-22  
**Scope:** Inventory only — **no subject deletions**  
**Purpose:** Support future **ADR-0007** dual-publish deprecation window  
**Canonical contracts:** [ADR-0003](../adr/ADR-0003-fleet-edge-safety-contracts.md) · `docs/FLEET.md`

## Naming trees

| Prefix tree | Role today |
|-------------|------------|
| `aspen.fleet.*` / `aspen.edge.*` / `aspen.safety.*` | **ADR-0003 canonical** — plant packages (edge-rrm, swarm-manager) |
| `starship.fleet.*` | **Monorepo primary** (Starship/AspenOS C2 mesh) |
| `agnetic.fleet.*` | **Legacy dual** of `starship.fleet.*` (Alpha 2.0 clients) |

**Important:** `agents/nats_subjects.py` `dual_publish` maps **only** `starship.*` ↔ `agnetic.*`. It does **not** bridge to `aspen.*`.

Subject shape mismatch (not just prefix):

| ADR-0003 (aspen) | Monorepo dual (starship/agnetic) |
|------------------|----------------------------------|
| `aspen.fleet.node.register` | `*.fleet.register` |
| `aspen.fleet.node.heartbeat` | `*.fleet.heartbeat` |
| `aspen.fleet.ops.status` | `*.fleet.ops.status` (name aligned) |
| `aspen.fleet.mission.*` | *(no monorepo equivalent)* |
| *(none)* | `*.fleet.status` (node snapshot) |
| *(none)* | `*.fleet.exercise` (red/blue) |

---

## A. Publishers — monorepo (`aspen-os`)

| Code path | Direction | Subjects emitted | Mechanism | Notes |
|-----------|-----------|------------------|-----------|-------|
| `services/fleet.py` `_nats_register` | **PUB** | `starship.fleet.register`, `agnetic.fleet.register`, `starship.fleet.status`, `agnetic.fleet.status` | `dual_publish` | CLI `register` / dashboard register subprocess |
| `services/fleet.py` `daemon_loop` | **PUB** | `starship.fleet.heartbeat`, `agnetic.fleet.heartbeat` | `dual_publish` every `STARSHIP_FLEET_HB` (default 30s) | Always on when daemon runs |
| `services/fleet.py` `daemon_loop` (ops) | **PUB** | `starship.fleet.ops.status`, `agnetic.fleet.ops.status` | `dual_publish` when `fleet.ops_manager.enabled` | Aggregate summary JSON (not event-envelope) |
| `services/fleet.py` `_nats_exercise` | **PUB** | `starship.fleet.exercise`, `agnetic.fleet.exercise` | `dual_publish` | start/stop exercise |
| `dashboard/server.py` `handle_api_fleet_exercise` | **PUB** | `starship.fleet.exercise`, `agnetic.fleet.exercise` | explicit dual loop | Mirrors state file; NATS optional |
| `src/python/lib/dashboard/server.py` | **PUB** | same exercise pair | same | Install/layout twin of dashboard |
| `dashboard/server.py` `handle_api_fleet_register` | **PUB** (indirect) | register + status via fleet.py | subprocess → `services/fleet.py register` | |
| `starshipctl/cmd/fleet.go` | **PUB** (indirect) | whatever fleet.py emits | exec `python3 services/fleet.py …` | No direct NATS |
| `agents/nats_subjects.py` | helper | any subject under starship/agnetic | `dual` / `dual_publish` / `dual_subscribe` | Env: `STARSHIP_NATS_PREFIX`, `STARSHIP_NATS_LEGACY_PREFIX` |
| `starshipctl/cmd/subjects.go` | helper | dual helpers in Go | library | Not fleet-specific publishers |
| StarAgent Rust (`agent/`) | — | **no** `*.fleet.*` | telemetry only | `starship.telemetry.*` (out of fleet scope) |
| `src/c/starshipd` | — | dual-publish map print | not a live fleet publisher | |
| `src/python/lib/tools.py` | **PUB** (unrelated) | `agnetic.flamingo.fleet` | one-off tool | **Not** the fleet control plane |

**Monorepo does not publish any `aspen.fleet.*` subjects today.**

### Config / ACL surface (not publishers)

| Path | Role |
|------|------|
| `nats/subjects.yaml` | Declares starship + agnetic fleet names only |
| `nats/fleet-auth.yaml` | Account allowlists for starship/agnetic fleet subjects; `subject_primary` / `subject_legacy` heartbeat |
| `nats/fleet-accounts.conf.tmpl` | Stream exports `starship.fleet.>` / `agnetic.fleet.>` |
| `config/fleet.yaml` | Ops subject patterns: `starship.fleet.ops.command.>`, `.status`, `.event.>` (command/event mostly unused in code) |

---

## B. Subscribers — monorepo

| Code path | Direction | Subjects | Notes |
|-----------|-----------|----------|-------|
| `services/fleet.py` `daemon_loop` | **SUB** | dual(`*.fleet.register`), dual(`*.fleet.heartbeat`) | Peer cache → `fleet-state.json` |
| Dashboard Fleet Map APIs | **read file** | — | `GET /api/fleet` reads local state / config; **no** NATS subscribe on fleet subjects |
| TelemetryAggregator | **SUB** | `starship.telemetry.>` only | Not fleet |

No monorepo subscriber for `aspen.fleet.*`, `aspen.edge.*`, or `aspen.safety.*`.

---

## C. Publishers / subscribers — plant packages (sibling repos)

Paths on this host: `/home/tech/repos/{aspen-edge-rrm,aspen-swarm-manager,aspen-langgraph-worker}`.

### aspen-edge-rrm

| Code path | Dir | Subject(s) |
|-----------|-----|------------|
| `aspen_edge/rrm.py` `start` | **PUB** | `aspen.fleet.node.register` |
| `aspen_edge/rrm.py` `heartbeat` | **PUB** | `aspen.fleet.node.heartbeat` |
| `aspen_edge/rrm.py` `handle_propose` | **PUB** | `aspen.edge.<node_id>.propose_act` |
| `aspen_edge/rrm.py` | **SUB** | `aspen.safety.estop`, `aspen.safety.clear` |
| `aspen_edge/fleet_bus.py` `OpsManager` | **SUB** | `aspen.fleet.node.register`, `aspen.fleet.node.heartbeat` |
| `aspen_edge/fleet_bus.py` `OpsManager.publish_status` | **PUB** | `aspen.fleet.ops.status` |
| `aspen_edge/status_cli.py` / `examples/fleet_e2e.py` / tests | **PUB/SUB** | demo estop/clear + ops.status observe |
| `aspen_edge/nats_bus.py` `NatsFleetBus` | transport | Publishes **exact** subject string — **no** starship/agnetic dual |
| Default `FleetBus` | in-process | Lab/CI; no NATS required |

### aspen-swarm-manager

| Code path | Dir | Subject(s) |
|-----------|-----|------------|
| `aspen_swarm/mission.py` `_emit` | **PUB** | `aspen.fleet.mission.{event}` (e.g. failed, planned→… lifecycle) |
| `aspen_swarm/bus.py` | transport | In-process envelope bus (ADR-0003 style) |

### aspen-langgraph-worker

| Finding | Detail |
|---------|--------|
| Fleet subjects | **None** in code (docs mention contracts epic only) |
| Related | Worker subjects `aspen.worker.langgraph.*` + still may emit `aspen.edge.<node>.propose_act` per ADR-0005 (out of fleet.* inventory) |

---

## D. Gaps vs ADR-0003

| ADR-0003 expectation | Status | Gap |
|----------------------|--------|-----|
| Prefer `aspen.` for new work | Packages OK; monorepo still starship/agnetic | No monorepo → aspen bridge |
| `aspen.fleet.node.register` | edge-rrm only | Monorepo uses `*.fleet.register` (no `.node.`) |
| `aspen.fleet.node.heartbeat` | edge-rrm only | Monorepo uses `*.fleet.heartbeat` |
| `aspen.fleet.ops.status` | both trees, **disjoint buses** | Same leaf name; different prefix + payload shape; no shared consumer |
| `aspen.fleet.mission.*` | swarm-manager only | Monorepo has no mission graph subjects |
| `aspen.edge.<node>.*` | edge-rrm | Not in monorepo NATS ACL/subjects.yaml |
| `aspen.safety.estop\|clear` | edge-rrm | Not in monorepo fleet daemon |
| Event envelope (`id, source, type, time, data`) | packages ~yes | `services/fleet.py` publishes raw node/summary JSON |
| Dual-publish only when bridging Alpha | monorepo dual always on for fleet | No `aspen` dual; starship↔agnetic always |
| JetStream streams FLEET / EDGE / SAFETY | lab packages | Monorepo accounts stream `starship.fleet.>` / `agnetic.fleet.>` only |
| `*.fleet.status` / `*.fleet.exercise` | monorepo only | **Extra** vs ADR-0003 — keep until ADR-0007 maps or retires them |
| `config/fleet.yaml` ops.command / ops.event | declared | **No code publishers found** in this pass |
| Single mesh visibility | broken | Starship C2 and plant packages do not share subjects without a future bridge |

---

## E. Implications for ADR-0007 (deprecation window) — notes only

Not implementing deprecation here. Suggested inventory-backed options for a future ADR:

1. **Bridge dual-publish** (monorepo or gateway): map  
   `starship.fleet.register` → `aspen.fleet.node.register` (and heartbeat/ops) during a window, with envelope wrap.
2. **Freeze new `agnetic.fleet.*` publishers**; keep subscribe dual until Alpha clients gone.
3. **Document monorepo-only subjects** (`status`, `exercise`) as Starship C2 extensions or fold into `aspen.fleet.ops.*` / mission.
4. **Update** `nats/subjects.yaml` + `fleet-auth.yaml` to allow `aspen.fleet.>` / `aspen.safety.>` before any cutover.
5. **Do not delete** subjects in code until ADR-0007 acceptance + consumer audit.

---

## F. Quick verification commands

```bash
# Monorepo string inventory
rg -n 'starship\.fleet\.|agnetic\.fleet\.|aspen\.fleet\.' \
  services/fleet.py agents/nats_subjects.py dashboard/server.py \
  nats/subjects.yaml nats/fleet-auth.yaml config/fleet.yaml

# Package inventory (sibling checkouts)
rg -n 'aspen\.fleet\.|aspen\.safety\.|aspen\.edge\.' \
  /home/tech/repos/aspen-edge-rrm /home/tech/repos/aspen-swarm-manager
```

---

## Acceptance (ASP-362)

- [x] Table of code paths publishing `starship.fleet.*` / `agnetic.fleet.*` / `aspen.fleet.*`
- [x] Note gaps vs ADR-0003
- [x] Doc under `docs/ops/` (this file)
- [x] No subject deletions
