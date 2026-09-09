# ASP-537: Wire `aspen.sentinel.audit.event` publisher

## Problem

ADR-0007 defined `aspen.sentinel.audit.event` as the durable audit-trail subject,
and the threat model's H-015 / CR 4.2 / §8 P1#4 required recorded agent actions
with `{event_id, actor, action, target, result, ts}` — but nothing published them.
The gatekeeper shim's `log_audit` only appended to an in-memory buffer and tried
best-effort NATS via `NATSGateClient` (no durability, no replay, no query path).

## Solution

New `src/python/sentinel/` package + `AuditEventPublisher` (JSONL + JetStream)
and a wired gatekeeper shim:

1. **Durable local write-path (unconditional):** every event is fsync'd onto an
   append-only JSONL journal (`/var/lib/aspen/sentinel/audit.jsonl`, overridable
   via `ASPEN_AUDIT_LOG`). A failed/absent broker never drops an event.
2. **Best-effort JetStream mirror:** when online, the same event is published to
   `aspen.sentinel.audit.event` with a `Nats-Msg-Id` header for dedup. Offline
   events queue in memory and are drained by `replay_pending()` on reconnect.
3. **Idempotent replay:** a `.marker` sidecar records published `event_id`s;
   `replay_pending()` publishes in-memory backlog + journal events not yet
   marked, then merges markers (10-min JetStream `duplicate_window` makes the
   server-side dedup effective).
4. **Wiring:** `gatekeeper/minimal_shim.py` gains `set_audit_publisher()`;
   `log_audit()` fans events via `record_event_sync()`; `run_daemon()` constructs
   the publisher, streams a reconnect drain every 5s, and closes it on shutdown.
5. **Read paths:** `tail()`/`query()` over the journal; `js-last`/`check` over
   the stream; CLI `scripts/sentinel-audit.py` exposes
   `emit / tail / query / replay / js-last / check`.

## Key gotchas

- **nats-py `add_stream` lives on the JetStream manager** (`JetStreamContext`
  inherits `JetStreamManager`, so `js.add_stream(...)` still exists). Params are
  plain float seconds for `max_age` / `duplicate_window` — no `timedelta`
  coercion needed.
- **`js.publish()` accepts a plain dict `headers`** and a `stream=` kwarg — the
  `Nats-Msg-Id` header must be passed inline in `headers=`, not via msg.
- **Sync callers without a loop:** `record_sync()` / `record_event_sync()` always
  write JSONL; they schedule the JS publish via `asyncio.ensure_future` when a
  loop is running, else buffer for replay. Never block the gatekeeper on the broker.
- **Legacy field mapping:** `from_event()` maps gatekeeper fields
  (`type`→`action`, `agent_id`→`actor`, `resource`→`target`, `decision`→`result`)
  and passes through all extra fields = post-schema audits normalize cleanly.
- **No live broker in CI:** tests mock `nats` via `patch.dict("sys.modules", ...)`;
  broker-dependent branches are marked `pragma: no cover`.
- Stream name is `ASPEN_SENTINEL` covering `["aspen.sentinel.>"]` so the whole
  sentinel namespace lands on one stream; `add_stream` is idempotent (a pre-existing
  stream is a non-fatal log line).