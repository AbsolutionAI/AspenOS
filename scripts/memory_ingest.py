#!/usr/bin/env python3
"""Starship OS — BEL-154 Memory Ingestion Layer (Component 1).

Appends raw ingest JSONL records for the promotion pipeline
(``scripts/memory_promote.py``) to consume. One JSON object per line, written
to per-source daily files:

    {ingest_dir}/{source}/{YYYY-MM-DD}.jsonl

Schema (matches the BEL-154 design doc Component 1 and what
``memory_promote._iter_ingest_records`` reads back):
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
        "linear_refs": [...],
        "paperclip_refs": [...]
      }
    }
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_INGEST_DIR = Path(os.environ.get(
    "AGNETIC_MEMORY_INGEST_DIR",
    "/home/tech/.aspen/memory/ingest",
))

VALID_SOURCES = {"hermes", "paperclip", "opencode", "aider", "appflowy", "grokbuild"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def daily_path(source: str, ingest_dir: Path, when: datetime) -> Path:
    """Return the daily JSONL file for a source, e.g. …/opencode/2026-08-06.jsonl."""
    return ingest_dir / source / when.strftime("%Y-%m-%d.jsonl")


def ingest_record(
    source: str,
    source_id: str,
    content: str,
    *,
    agent: str = "opencode",
    company: str = "asp",
    project: str | None = None,
    tools: list[str] | None = None,
    files: list[str] | None = None,
    linear_refs: list[str] | None = None,
    paperclip_refs: list[str] | None = None,
    timestamp: str | None = None,
    ingest_dir: Path = DEFAULT_INGEST_DIR,
) -> Path:
    """Validate and append a BEL-154 raw ingest record. Returns the file path.

    Raises ``ValueError`` for an unknown ``source``.
    """
    if source not in VALID_SOURCES:
        raise ValueError(
            f"invalid source {source!r}; valid sources: {', '.join(sorted(VALID_SOURCES))}"
        )

    record = {
        "source": source,
        "source_id": source_id,
        "timestamp": timestamp or _now_utc(),
        "agent": agent,
        "company": company,
        "content": content,
    }
    if project:
        record["project"] = project

    metadata: dict = {}
    if tools:
        metadata["tools_used"] = tools
    if files:
        metadata["files_touched"] = files
    if linear_refs:
        metadata["linear_refs"] = linear_refs
    if paperclip_refs:
        metadata["paperclip_refs"] = paperclip_refs
    if metadata:
        record["metadata"] = metadata

    path = daily_path(source, ingest_dir, datetime.now(timezone.utc))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")

    # Dual-write to shared holographic SQLite (best-effort; never fail ingest).
    try:
        try:
            from holographic_ingest import write_holographic
        except ImportError:
            from scripts.holographic_ingest import write_holographic

        write_holographic(
            content,
            source=source,
            source_id=source_id,
            agent=agent,
            project=project,
            linear_refs=linear_refs,
            paperclip_refs=paperclip_refs,
            ingest_dir=ingest_dir,
            default_ingest_dir=DEFAULT_INGEST_DIR,
        )
    except Exception:
        pass

    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="memory-ingest",
        description="Append a BEL-154 raw ingest record for the promotion pipeline",
    )
    parser.add_argument("--source", required=True,
                        help="one of: " + ", ".join(sorted(VALID_SOURCES)))
    parser.add_argument("--source-id", required=True,
                        help="run-id / task-id / session-uuid / commit-sha")
    parser.add_argument("--content", default="",
                        help="raw content (else read from stdin)")
    parser.add_argument("--stdin", action="store_true",
                        help="read --content from stdin")
    parser.add_argument("--agent", default="opencode")
    parser.add_argument("--company", default="asp")
    parser.add_argument("--project", default=None)
    parser.add_argument("--tools", default=None,
                        help="comma-separated tools_used list")
    parser.add_argument("--files", default=None,
                        help="comma-separated files_touched list")
    parser.add_argument("--linear-refs", default=None,
                        help="comma-separated Linear ticket ids (BEL-123)")
    parser.add_argument("--paperclip-refs", default=None,
                        help="comma-separated Paperclip issue ids (ABS-9)")
    parser.add_argument("--timestamp", default=None,
                        help="ISO timestamp (default: now UTC)")
    parser.add_argument("--ingest-dir", type=Path, default=DEFAULT_INGEST_DIR)
    args = parser.parse_args(argv)

    def _split(value: str | None) -> list[str] | None:
        return [p.strip() for p in value.split(",") if p.strip()] if value else None

    content = args.content
    if args.stdin or not content:
        content = sys.stdin.read().strip()

    try:
        path = ingest_record(
            args.source,
            args.source_id,
            content,
            agent=args.agent,
            company=args.company,
            project=args.project,
            tools=_split(args.tools),
            files=_split(args.files),
            linear_refs=_split(args.linear_refs),
            paperclip_refs=_split(args.paperclip_refs),
            timestamp=args.timestamp,
            ingest_dir=args.ingest_dir,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
