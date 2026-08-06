# ASP-54 — BEL-154 memory promotion pipeline

## Problem

BEL-154's design (`docs/architecture/MEMORY_LAYER.md`) Component 2 (Promotion
Pipeline) existed only as a design: extraction targets, a confidence table, and
a threshold, but no implementation. ASP-52 landed the semantic layer and ASP-53
the access layer; promotion was the flagged next-cycle candidate.

## Root cause

No `scripts/memory_promote.py` existed. Raw ingest JSONL files had no consumer,
so nothing flowed from ingestion → unified store. The design's `facts.sqlite`
(FTS5 + triggers) layout was aspirational and diverged from the canonical
`MemoryManager` SQLite schema already in place.

## Fix

Added `scripts/memory_promote.py` — a zero-dependency CLI that:

- Reads raw ingest JSONL (`/home/tech/.aspen/memory/ingest/{source}/*.jsonl`).
- `extract_facts()` targets the design's extraction list: decisions
  (declaration cues), configs, patterns, and Linear/Paperclip cross-references
  (both from metadata and bare mentions in content). Secret-bearing content is
  never extracted.
- `score_confidence()` implements the BEL-154 table deterministically:
  - Base signal: decision 1.0, cross-referenced (L+P) 0.9, single ref 0.8,
    config 0.75/0.9, generic 0.5.
  - Additive authorship nudge (±0.05 human/agent) and repetition (+0.05);
    recency multiplies stale content by 0.6.
  - Threshold 0.7 promotes into `MemoryManager.ingest()` (DECISION/SEMANTIC)
    with the design's fact metadata (tags, refs, source, confidence).
- Dedupes by `sha256(content)[:16]`, persisted in an append-only
  `facts.jsonl` audit log so re-runs are idempotent.
- `--dry-run` and `--source` filters for safe review.

Also updated `docs/ARCHITECTURE_COMPLETE.md` (memory section) and added
`tests/test_memory_promote.py` (12 tests).

## Lessons

- **Promote into the canonical store, don't clone the design's schema.** The
  design doc's `facts.sqlite` would have meant a second, parallel fact store.
  Reusing `MemoryManager` kept one source of truth and zero schema drift — the
  pattern established by ASP-52/53.
- **Multiplicative authorship weighting breaks the threshold.** Applying
  `agent-authored → 0.7` as a multiplier to an already-0.9 cross-referenced fact
  gives 0.63 — below the 0.7 promote threshold, so almost nothing would ever
  promote. Additive nudges keep strong signals above the bar while preserving
  the human>agent ordering.
- **Audit-log dedup beats in-memory dedup.** Persisting promoted `fact_id`s to
  `facts.jsonl` makes re-runs idempotent across process boundaries and gives an
  immutable promotion record.
- **Secret hygiene at the extractor.** Skipping content with `secret=`/`token=`
  etc. at extraction is cheaper and safer than relying on downstream redaction.
- **Stale tests predate this change.** `tests/test_server.py` fails on
  `handle_marketplace_installed`, which no tracked server code exposes —
  independent of this cycle.

## Verification

- `python3 -m py_compile scripts/memory_promote.py services/memory.py`
- `tests/test_memory_promote.py`: 12/12 pass.
- Full tracked suite: 79 pass; 5 `test_server.py` failures are pre-existing
  (confirmed identical without this change).
- Real ingest dir (empty): exits cleanly, reports nothing to promote.
- Demo fixture: decision (0.95) + reference (0.85) + config (0.7) promoted into
  a temp DB; `retrieve()` round-trips them; second run promotes 0 new (dedup).

## Follow-ups

- `ProspectiveMemoryManager` — architect decision pending (escalated ASP-53).
- AppFlowy bidirectional sync — larger scope, future cycle.
- Cron/systemd timer to run `memory_promote.py` once ingest hooks exist.
