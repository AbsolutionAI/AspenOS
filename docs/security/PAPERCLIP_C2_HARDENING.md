# Paperclip C2 surface hardening runbook

**Finding:** F-019 / H-019 · **Ticket:** ASP-367 · **Parent:** ASP-298  
**Scope:** Paperclip control plane (API/UI `:3100`, board keys, multi-company blast radius)  
**Audience:** Aspen (board), Runtime, Auditor  
**Secrets policy:** never paste API keys, board keys, or JWT secrets into issues, Linear, or git.

---

## Why this matters

Paperclip is the **org command-and-control plane** for agent hire, checkout, heartbeats, budgets, and company membership. Compromise of board keys or an exposed `:3100` listener is full mesh takeover across companies the key can reach (ASP + ABSA + Content + ABS when memberships allow).

Aspen OS plant safety (propose_act dual-human, NATS mTLS) is a **separate** control plane — this runbook does not replace Master Spec dual-auth (ASP-364 / H-016).

---

## Threat surface (checklist)

| Asset | Risk | Required control |
|-------|------|------------------|
| HTTP API/UI `:3100` | LAN/WAN agent takeover | Tailnet-only reachability; no public ingress; `deploymentMode=authenticated` |
| Board / agent API keys | Impersonation, mass checkout | Files mode `600`, directory not world-readable; rotation SLA |
| Workspace `cwd` | `workspace_validation_failed` or wrong-tree edits | Must be a **git root** (e.g. `…/repos/aspen-os`), never parent `repos/` |
| Budgets `$0` | Unbounded LLM spend | Non-zero `budgetMonthlyCents` per company + per Grok-class agent |
| Multi-company membership | Cross-company blast radius | Least privilege memberships; ABS paused at $0 under freeze |
| Secrets master key | Decrypt Paperclip secrets store | Local encrypted provider key file mode `600`; backups access controlled |
| Issue / comment bodies | Credential leak into SoR | No secrets in ASP/BEL text; use env + `~/.hermes/profiles/*/`.env |
| Agent adapters | Sticky error loops / wrong binary | Resolved `hermesCommand`/`opencode` paths; clear-error after path fixes |

---

## Bind and network expectations

**Target posture (this host):**

- Paperclip `server.exposure`: `private`
- `server.deploymentMode`: `authenticated`
- Listen: LAN bind is acceptable **only** when the host is not internet-facing and traffic is Tailscale/mesh-trusted
- UI hostnames limited to `allowedHostnames` (tailnet DNS + localhost + known mesh IPs)
- **Do not** put `:3100` on a public cloud security group or home-router port-forward

**Verify (operator):**

```bash
# Process listen (expect private/mesh interfaces, not a public WAN bind you do not control)
ss -lntp | grep -E ':3100\b' || true

# Health without key should not grant board powers
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3100/api/health

# Authenticated board
export PAPERCLIP_API_KEY="$(cat ~/.paperclip/keys/board.key)"
curl -sS -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  "${PAPERCLIP_API_URL:-http://127.0.0.1:3100}/api/health" | jq .status
```

**If exposure must tighten further:** re-run `paperclipai configure` (or edit instance `config.json`) toward loopback-only bind and restart the unit — schedule a maintenance window; agents need the advertised `PAPERCLIP_API_URL`.

---

## Board and agent key hygiene

| Control | Standard |
|---------|----------|
| Path | `~/.paperclip/keys/board.key` (and per-agent keys under instance data) |
| Mode | **`600`** file, directory not `o+rx` if it only holds secrets |
| Shell | `export PAPERCLIP_API_KEY="$(cat …)"` — never `echo`/log the value |
| Rotation SLA | **≤ 7 days** after suspected leak; **immediate** after paste into chat/issue/git |
| CI / agents | Inject via env or Paperclip secrets provider — not committed `.env` in product repos |
| Scratch | Hermes/Paperclip run scratch may snapshot env — treat run tmp as secret-bearing; do not archive to git |

**Verify:**

```bash
stat -c '%a %n' ~/.paperclip/keys/board.key
# expect 600
```

**Rotate (outline):** generate/replace board key via Paperclip admin/CLI for your version → update operator shells and any systemd `EnvironmentFile` → revoke old key → smoke `paperclipai whoami`.

---

## Workspace git-root rule

| Bad | Good |
|-----|------|
| `/home/tech/aspen-dev/repos` | `/home/tech/aspen-dev/repos/aspen-os` |
| Random non-git packaging dir | Product repo with `.git` |

Broken cwd → `workspace_validation_failed` on hermes_local/opencode_local and silent “adapter broken” noise.

**Verify per project workspace:**

```bash
test -d /home/tech/aspen-dev/repos/aspen-os/.git && echo OK
```

Patch via API: `PATCH /api/projects/{id}/workspaces/{id}` `{"cwd":"…/aspen-os"}` (board).

---

## Budget and freeze caps

Fiscal freeze (until Gumroad cash flow verified): **≤ ~$100/mo LLM** across companies; timer heartbeats **off** (`wakeOnDemand: true`).

| Company | Guidance |
|---------|----------|
| Aspen OS (ASP) | ~$40 lean; aspen = Grok gates only |
| ABSA | ~$35; resolve hard_stop before wakes |
| Content Studio | ~$15 |
| ABS | **$0 paused** |

**Never leave company or Grok agent budget at `0` if `0` means unlimited in your Paperclip build** — set explicit cents.

**Verify:**

```bash
curl -sS -H "Authorization: Bearer $PAPERCLIP_API_KEY" \
  "$PAPERCLIP_API_URL/api/companies/$PAPERCLIP_COMPANY_ID/dashboard" \
  | jq '{costs, budgets, tasks}'
```

---

## Multi-company blast radius

- Board key membership is **per company** — still treat board as high privilege
- Human company-access PUT must pass the **full** desired company set (omitting ASP drops it)
- Do not staff deferred verticals (OSINT, Leonardo volume, Family private lane) under freeze
- Cross-company agent hire requires board approval when `requireBoardApprovalForNewAgents: true`

---

## Biweekly threat-model checklist (include F-019)

Add to every biweekly / ASP-298-style review:

- [ ] `:3100` not internet-exposed; authenticated mode on
- [ ] Board key mode `600`; no keys in issues/Linear/git since last review
- [ ] Rotation log: any leak → rotated within SLA
- [ ] All coding agent workspaces are git roots
- [ ] Company budgets non-zero where unlimited-zero is unsafe; freeze caps held
- [ ] ABS still paused unless cash-flow exception documented
- [ ] No new company memberships without least-privilege review
- [ ] Pending approvals queue empty or intentionally parked
- [ ] Dashboard `runActivity` free of mass `adapter_failed` / `workspace_validation_failed`
- [ ] Cross-check plant C2 separately: NATS accounts+TLS (H-001/H-006), dual-human propose_act (H-016)

---

## Incident quick actions

1. **Suspected board key leak:** rotate key → restart operator sessions → audit `activity` for unexpected checkouts/hires → comment ASP-367 parent without pasting secrets  
2. **Unexpected public bind:** drop ingress / rebind private → confirm `ss` → notify human owner  
3. **Budget runaway:** pause company or agents → resolve budget incident with amount **>** observed → set wake-on-demand only  
4. **Wrong workspace damage:** stop agent → fix cwd to git root → clear-error → reopen CE-gated issue  

---

## Related docs

- `docs/FOUNDATION.md` / `docs/ops/FOUNDATION.md` — mesh foundation gates  
- `docs/MODEL_ROUTING.md` — freeze + Flash/Grok routing  
- `docs/COMPANY_MAP.md` — company budget map  
- `docs/SECURITY.md` — product (Starship/Aspen OS) security architecture  
- `docs/ops/LINEAR_MCP_PAPERCLIP.md` — Linear tools inside Paperclip  
- Master Spec dual-human plant path — ASP-364 / H-016 (not covered here)

---

## Acceptance (ASP-367)

- [x] Runbook committed under `docs/security/`  
- [x] Biweekly checklist includes F-019 / C2 items  
- [x] No secrets in issue bodies (operators reminded here)  
