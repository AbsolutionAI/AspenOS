#!/usr/bin/env python3
"""Starship OS — BEL-154 Memory Promotion Pipeline.

Reads raw ingest JSONL files, extracts fact-worthy content, scores confidence
per the BEL-154 design table, and promotes facts with confidence >= threshold
into the canonical MemoryManager store (single source of truth).

Schema (raw ingest JSONL, one JSON object per line):
    {
      "source": "hermes|paperclip|opencode|aider|appflowy",
      "source_id": "session-uuid|run-id|task-id|commit-sha|page-id",
      "timestamp": "2026-08-04T21:00:00Z",
      "agent": "ergo|proxy|romi|opencode|aider|human",
      "company": "asp|abs|absa|content",
      "project": "aspen-os|...",
      "content": "raw conversation / code / output / page content",
      "metadata": {
        "tools_used": [...],
        "files_touched": [...],
        "linear_refs": ["BEL-153"],
        "paperclip_refs": ["ABS-9"]
      }
    }

Confidence scoring (BEL-154 design table):
    explicit declaration            -> 1.0
    cross-referenced (L+P+code)     -> 0.9
    repeated across records         -> 0.8
    agent-authored / human-authored -> 0.7 / 0.9
    recency (last 30 days)          -> 1.0, else 0.6

Threshold (default): confidence >= 0.7 promotes to the unified store.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))

from memory import MemoryManager, MemoryType  # noqa: E402

DEFAULT_INGEST_DIR = Path("/home/tech/.aspen/memory/ingest")
DEFAULT_FACTS_DIR = Path("/home/tech/.aspen/memory/facts")
DEFAULT_FACTS_LOG = DEFAULT_FACTS_DIR / "facts.jsonl"

_THRESHOLD = 0.7
_RECENT_WINDOW_DAYS = 30

_DECLARATION_CUES = [
    "decision:", "we decided", "we will use", "approach:", "rationale:",
    "chosen", "recommendation:", "conclusion:",
]
_CONFIG_CUES = [
    "export ", "config:", "env var", "set ", "flag", "install ",
    "apt install", "pip install", "systemctl", "docker run",
]


@dataclass
class FactCandidate:
    content: str
    fact_type: str = "reference"
    tags: list[str] = field(default_factory=list)
    linear_refs: list[str] = field(default_factory=list)
    paperclip_refs: list[str] = field(default_factory=list)
    source: str = ""
    source_id: str = ""
    agent: str = ""
    timestamp: str = ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def fact_id(content: str) -> str:
    """Deterministic content hash used as the promoted fact id."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _is_recent(timestamp: str) -> bool:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        parsed = _now()
    cutoff = _now() - timedelta(days=_RECENT_WINDOW_DAYS)
    return parsed >= cutoff


def _candidate_type(content: str) -> str:
    lower = content.lower()
    if any(c in lower for c in _DECLARATION_CUES):
        return "decision"
    if any(c in lower for c in _CONFIG_CUES):
        return "config"
    return "pattern"


def extract_facts(record: dict) -> list[FactCandidate]:
    """Extract fact-worthy candidates from a raw ingest record.

    Targets per the BEL-154 design: decisions, patterns, configurations,
    credential references (names/paths only, never secret values), and
    Linear/Paperclip cross-references.
    """
    content = (record.get("content") or "").strip()
    if not content:
        return []

    lower = content.lower()
    # Never promote secret values — only names/paths that look like references.
    if any(s in lower for s in ["secret=", "password=", "api_key=", "token="]):
        return []

    metadata = record.get("metadata") or {}
    linear_refs = list(metadata.get("linear_refs", []) or [])
    paperclip_refs = list(metadata.get("paperclip_refs", []) or [])
    if not linear_refs and not paperclip_refs:
        # Bare mentions in content (e.g. "BEL-153" / "ABS-9")
        import re
        linear_refs = re.findall(r"\bBEL-\d+\b", content)
        paperclip_refs = re.findall(r"\b(?:ABS|ASP|PAP)-\d+\b", content)

    tags = list(metadata.get("tags", []) or [])

    candidates: list[FactCandidate] = []

    # 1. The content itself, if it looks decision/config/pattern-worthy.
    content_type = _candidate_type(content)
    candidates.append(
        FactCandidate(
            content=content,
            fact_type=content_type,
            tags=tags,
            linear_refs=linear_refs,
            paperclip_refs=paperclip_refs,
            source=record.get("source", ""),
            source_id=record.get("source_id", ""),
            agent=record.get("agent", ""),
            timestamp=record.get("timestamp", ""),
        )
    )

    # 2. Each linear/paperclip ref as a standalone reference fact.
    for ref in linear_refs:
        candidates.append(
            FactCandidate(
                content=f"Reference: {ref} — {content[:200]}",
                fact_type="reference",
                tags=tags,
                linear_refs=[ref],
                paperclip_refs=paperclip_refs,
                source=record.get("source", ""),
                source_id=record.get("source_id", ""),
                agent=record.get("agent", ""),
                timestamp=record.get("timestamp", ""),
            )
        )
    for ref in paperclip_refs:
        candidates.append(
            FactCandidate(
                content=f"Reference: {ref} — {content[:200]}",
                fact_type="reference",
                tags=tags,
                linear_refs=linear_refs,
                paperclip_refs=[ref],
                source=record.get("source", ""),
                source_id=record.get("source_id", ""),
                agent=record.get("agent", ""),
                timestamp=record.get("timestamp", ""),
            )
        )

    return candidates


def score_confidence(candidate: FactCandidate, authored_by_human: bool = False,
                     seen_count: int = 1) -> float:
    """Score a candidate per the BEL-154 confidence table (deterministic).

    Base signal comes from the fact class / cross-references; authorship and
    repetition nudge it additively; recency scales it multiplicatively so
    strong cross-referenced facts still clear the 0.7 threshold.
    """
    if candidate.fact_type == "decision":
        score = 1.0
    elif candidate.fact_type == "config":
        score = 0.9 if (candidate.linear_refs or candidate.paperclip_refs) else 0.75
    elif candidate.linear_refs and candidate.paperclip_refs:
        score = 0.9
    elif candidate.linear_refs or candidate.paperclip_refs:
        score = 0.8
    else:
        score = 0.5

    # Human-authored content is trusted slightly more than agent-authored.
    score += 0.05 if authored_by_human else -0.05

    # Cross-referenced across records (repetition).
    if seen_count > 1:
        score = min(score + 0.05, 0.95)

    # Recency (last 30 days) scales confidence down for stale content.
    if not _is_recent(candidate.timestamp):
        score *= 0.6

    return max(0.0, min(1.0, score))


def load_facts_log(facts_log: Path) -> set[str]:
    """Return fact_ids already promoted (append-only log dedup)."""
    if not facts_log.exists():
        return set()
    seen: set[str] = set()
    for line in facts_log.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            seen.add(json.loads(line)["fact_id"])
        except (json.JSONDecodeError, KeyError):
            continue
    return seen


def promote(manager: MemoryManager, candidate: FactCandidate,
            min_confidence: float = _THRESHOLD) -> str | None:
    """Promote a candidate into the unified store. Returns memory id or None."""
    confidence = score_confidence(candidate)
    if confidence < min_confidence:
        return None

    fid = fact_id(candidate.content)
    mem_type = (
        MemoryType.DECISION
        if candidate.fact_type == "decision"
        else MemoryType.SEMANTIC
    )
    metadata = {
        "fact_type": candidate.fact_type,
        "fact_id": fid,
        "tags": candidate.tags,
        "linear_refs": candidate.linear_refs,
        "paperclip_refs": candidate.paperclip_refs,
        "source": candidate.source,
        "source_id": candidate.source_id,
        "timestamp": candidate.timestamp,
        "confidence": round(confidence, 3),
    }
    return manager.ingest(
        agent=candidate.agent or "unknown",
        content=candidate.content,
        mem_type=mem_type,
        importance=confidence,
        metadata=metadata,
    )


def _iter_ingest_records(ingest_dir: Path, source_filter: str | None):
    sources = [source_filter] if source_filter else sorted(
        d for d in ingest_dir.iterdir() if d.is_dir()
    )
    for source in sources:
        source_dir = ingest_dir / source
        if not source_dir.is_dir():
            continue
        for f in sorted(source_dir.glob("*.jsonl")):
            for line_no, line in enumerate(f.read_text().splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    print(f"  [warn] {f}:{line_no}: skipping malformed JSON")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="memory-promote",
        description="BEL-154 memory promotion pipeline",
    )
    parser.add_argument("--ingest-dir", type=Path, default=DEFAULT_INGEST_DIR)
    parser.add_argument("--facts-log", type=Path, default=DEFAULT_FACTS_LOG)
    parser.add_argument("--db", default=os.environ.get(
        "AGNETIC_MEMORY_DB", "/tmp/agnetic-data/memory.db"))
    parser.add_argument("--min-confidence", type=float, default=_THRESHOLD)
    parser.add_argument("--source", default=None, help="Filter by ingest source dir")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report candidates without writing anything")
    args = parser.parse_args(argv)

    if not args.ingest_dir.is_dir():
        print(f"No ingest dir at {args.ingest_dir}; nothing to promote.")
        return 0

    already = load_facts_log(args.facts_log)
    print(f"Ingest dir: {args.ingest_dir}")
    print(f"Min confidence: {args.min_confidence}  Dry run: {args.dry_run}")

    candidates: list[FactCandidate] = []
    seen_counts: dict[str, int] = {}
    for record in _iter_ingest_records(args.ingest_dir, args.source):
        for cand in extract_facts(record):
            seen_counts[cand.content] = seen_counts.get(cand.content, 0) + 1
            candidates.append(cand)

    if not candidates:
        print("No candidates extracted.")
        return 0

    # Deterministic: stable by content, no positional bias.
    deduped: dict[str, FactCandidate] = {}
    for cand in candidates:
        fid = fact_id(cand.content)
        if fid not in already and fid not in deduped:
            deduped[fid] = cand

    print(f"Candidates: {len(candidates)}  New (not already promoted): {len(deduped)}")

    manager = MemoryManager(db_path=args.db)
    promoted = 0
    skipped = 0
    try:
        for cand in deduped.values():
            authored_by_human = cand.agent == "human"
            conf = score_confidence(cand, authored_by_human=authored_by_human,
                                    seen_count=seen_counts[cand.content])
            if conf < args.min_confidence:
                skipped += 1
                if args.dry_run:
                    print(f"  [skip] {conf:.2f} {cand.fact_type}: "
                          f"{cand.content[:80]!r}")
                continue
            fid = fact_id(cand.content)
            if args.dry_run:
                print(f"  [would promote] {conf:.2f} {cand.fact_type} "
                      f"{fid}: {cand.content[:80]!r}")
                promoted += 1
                continue
            mid = promote(manager, cand, min_confidence=args.min_confidence)
            if mid is None:
                skipped += 1
                continue
            promoted += 1
            # Append to the audit log.
            args.facts_log.parent.mkdir(parents=True, exist_ok=True)
            with open(args.facts_log, "a") as log:
                log.write(json.dumps({
                    "fact_id": fid,
                    "memory_id": mid,
                    "type": cand.fact_type,
                    "content": cand.content,
                    "confidence": round(conf, 3),
                    "sources": [{
                        "source": cand.source,
                        "source_id": cand.source_id,
                        "agent": cand.agent,
                        "timestamp": cand.timestamp,
                    }],
                    "tags": cand.tags,
                    "linear_refs": cand.linear_refs,
                    "paperclip_refs": cand.paperclip_refs,
                    "created_at": _now().isoformat(),
                }) + "\n")
    finally:
        manager.close()

    print(f"Promoted: {promoted}  Skipped (below threshold/already): {skipped}")
    if not args.dry_run:
        print(f"Facts log: {args.facts_log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
