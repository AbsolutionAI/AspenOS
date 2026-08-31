#!/usr/bin/env python3
"""Best-effort write of a BEL-154 ingest record into shared holographic SQLite.

Failure isolation: never raise to the caller. Tests using a temp ``ingest_dir``
do not touch production unless ``ASPEN_HOLOGRAPHIC_DB`` is set.

DB default: /home/tech/.aspen/memory/holographic.db
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

DEFAULT_HOLOGRAPHIC_DB = Path("/home/tech/.aspen/memory/holographic.db")
_HERMES_AGENT = Path(
    os.environ.get("HERMES_AGENT_ROOT", "/home/tech/.hermes/hermes-agent")
)
_MAX_FACT_CHARS = 2000
_MIN_FACT_CHARS = 8


def _should_write(ingest_dir: Path | None, default_ingest_dir: Path | None) -> bool:
    if os.environ.get("ASPEN_HOLOGRAPHIC_DISABLE") == "1":
        return False
    if os.environ.get("ASPEN_HOLOGRAPHIC_DB"):
        return True
    if ingest_dir is None or default_ingest_dir is None:
        return True
    try:
        return Path(ingest_dir).resolve() == Path(default_ingest_dir).resolve()
    except OSError:
        return False


def _compose_fact(
    content: str,
    *,
    source: str,
    source_id: str,
    agent: str,
    project: str | None,
) -> str:
    head = f"[{source}/{source_id} agent={agent}"
    if project:
        head += f" project={project}"
    head += "] "
    body = (content or "").strip()
    fact = (head + body)[:_MAX_FACT_CHARS]
    return fact


def _tags(
    source: str,
    agent: str,
    project: str | None,
    linear_refs: list[str] | None,
    paperclip_refs: list[str] | None,
) -> str:
    parts = [source, agent]
    if project:
        parts.append(project)
    for ref in (linear_refs or []) + (paperclip_refs or []):
        if ref:
            parts.append(ref)
    # FTS5 hyphen split — also keep unhyphenated tokens
    extra = []
    for p in list(parts):
        extra.extend(tok for tok in p.replace("-", " ").split() if tok and tok not in parts)
    return ",".join(dict.fromkeys(parts + extra))


def _category(content: str) -> str:
    c = (content or "").lstrip().lower()
    if c.startswith("decision"):
        return "decision"
    if c.startswith("reference"):
        return "reference"
    return "ingest"


def write_holographic(
    content: str,
    *,
    source: str,
    source_id: str = "",
    agent: str = "",
    project: str | None = None,
    linear_refs: list[str] | None = None,
    paperclip_refs: list[str] | None = None,
    ingest_dir: Path | None = None,
    default_ingest_dir: Path | None = None,
    db_path: Path | None = None,
) -> int | None:
    """Insert a fact. Returns fact_id or None. Never raises."""
    try:
        if not _should_write(ingest_dir, default_ingest_dir):
            return None
        body = (content or "").strip()
        if len(body) < _MIN_FACT_CHARS:
            return None
        fact = _compose_fact(
            body, source=source, source_id=source_id or "unknown",
            agent=agent or source, project=project,
        )
        tags = _tags(source, agent or source, project, linear_refs, paperclip_refs)
        category = _category(body)
        db = Path(db_path) if db_path else Path(
            os.environ.get("ASPEN_HOLOGRAPHIC_DB", str(DEFAULT_HOLOGRAPHIC_DB))
        )

        if str(_HERMES_AGENT) not in sys.path:
            sys.path.insert(0, str(_HERMES_AGENT))
        from plugins.memory.holographic.store import MemoryStore  # type: ignore

        store = MemoryStore(db_path=str(db))
        return int(store.add_fact(fact, category=category, tags=tags))
    except Exception as exc:  # isolation
        print(f"holographic-ingest: skipped: {exc}", file=sys.stderr)
        return None
