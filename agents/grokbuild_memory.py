#!/usr/bin/env python3
"""Starship OS — Grok Build memory ingestion hook (BEL-154 Component 1).

Mirrors OpenCode/Aider/Paperclip hooks: best-effort JSONL ingest + holographic
dual-write via ``scripts/memory_ingest.ingest_record``. Failure-isolated.

CLI::

    python3 agents/grokbuild_memory.py --source-id CHG-0005 \\
        --content \"Task summary …\" --files docs/x --tools terminal \\
        --linear-refs BEL-154 --paperclip-refs ASP-XXX
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = Path(os.getenv(
    "STARSHIP_ROOT", os.getenv("AGNETIC_ROOT", str(_SCRIPT_DIR.parent)),
))
_DEFAULT_AGENT = "grokbuild"
_DEFAULT_CONTENT_CAP = 20000


def ingest_grokbuild_record(
    content: str,
    *,
    source_id: str = "",
    agent: str = _DEFAULT_AGENT,
    company: str = "asp",
    project: str = "aspen-os",
    files: list[str] | None = None,
    tools: list[str] | None = None,
    linear_refs: list[str] | None = None,
    paperclip_refs: list[str] | None = None,
    ingest_dir: Path | None = None,
    max_content_chars: int = _DEFAULT_CONTENT_CAP,
) -> Path | None:
    """Write a BEL-154 raw ingest record (source=\"grokbuild\"). Never raises."""
    try:
        if str(_PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(_PROJECT_ROOT))
        from scripts.memory_ingest import DEFAULT_INGEST_DIR, ingest_record

        effective_content = (content or "")[:max_content_chars]
        effective_source_id = source_id or f"{agent}:{datetime.now().isoformat()}"

        return ingest_record(
            "grokbuild",
            effective_source_id,
            effective_content,
            agent=agent,
            company=company,
            project=project,
            tools=tools,
            files=files,
            linear_refs=linear_refs,
            paperclip_refs=paperclip_refs,
            ingest_dir=ingest_dir or DEFAULT_INGEST_DIR,
        )
    except Exception as exc:
        print(f"grokbuild-memory: ingest skipped: {exc}", file=sys.stderr)
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="grokbuild-memory",
        description="Append a BEL-154 raw ingest record (source='grokbuild')",
    )
    parser.add_argument("--source-id", default="")
    parser.add_argument("--content", default="")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--agent", default=_DEFAULT_AGENT)
    parser.add_argument("--company", default="asp")
    parser.add_argument("--project", default="aspen-os")
    parser.add_argument("--files", default=None)
    parser.add_argument("--tools", default=None)
    parser.add_argument("--linear-refs", default=None)
    parser.add_argument("--paperclip-refs", default=None)
    parser.add_argument("--ingest-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    def _split(value: str | None) -> list[str] | None:
        return [p.strip() for p in value.split(",") if p.strip()] if value else None

    content = args.content
    if args.stdin or not content:
        content = sys.stdin.read().strip()

    path = ingest_grokbuild_record(
        content,
        source_id=args.source_id,
        agent=args.agent,
        company=args.company,
        project=args.project,
        files=_split(args.files),
        tools=_split(args.tools),
        linear_refs=_split(args.linear_refs),
        paperclip_refs=_split(args.paperclip_refs),
        ingest_dir=args.ingest_dir,
    )
    if path is None:
        print("error: failed to write grokbuild ingest record", file=sys.stderr)
        return 2

    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
