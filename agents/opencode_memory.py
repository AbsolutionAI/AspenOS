#!/usr/bin/env python3
"""Starship OS — OpenCode memory ingestion hook (BEL-154 Component 1).

Agent-side wiring so an OpenCode session/task completion can append a raw
BEL-154 ingest record (``source="opencode"``) that the promotion pipeline
(``scripts/memory_promote.py``) consumes. Mirrors the Hermes hook
(``agents/agent_daemon.py::ingest_memory_record``): best-effort and
failure-isolated — a memory hiccup can never break the caller.

CLI (usable as an OpenCode hook / wrapper / one-off)::

    python3 agents/opencode_memory.py --source-id ASP-60 \\
        --content "Task summary …" --files docs/x,agents/y --tools bash,edit \\
        --linear-refs BEL-154 --paperclip-refs ASP-60
    cat summary.txt | python3 agents/opencode_memory.py --source-id ASP-60 --stdin

The CLI never raises and exits 0 on success (2 on a hard error, matching
``scripts/memory_ingest.py``); hook callers may wrap with ``|| true``.
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
_DEFAULT_AGENT = "opencode"
_DEFAULT_CONTENT_CAP = 20000


def ingest_opencode_record(
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
    """Write a BEL-154 raw ingest record (``source="opencode"``).

    Best-effort and failure-isolated: any error (missing import, bad write,
    oversized content) is logged at debug and never propagates to the caller,
    per the memory layer's "ingestion failure ≠ promotion failure ≠ access
    failure" principle. Returns the written path, or ``None`` on failure.
    """
    try:
        if str(_PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(_PROJECT_ROOT))
        from scripts.memory_ingest import ingest_record

        effective_content = (content or "")[:max_content_chars]
        effective_source_id = source_id or f"{agent}:{datetime.now().isoformat()}"

        return ingest_record(
            "opencode",
            effective_source_id,
            effective_content,
            agent=agent,
            company=company,
            project=project,
            tools=tools,
            files=files,
            linear_refs=linear_refs,
            paperclip_refs=paperclip_refs,
            ingest_dir=ingest_dir,
        )
    except Exception as exc:  # failure isolation — never raise
        print(f"opencode-memory: ingest skipped: {exc}", file=sys.stderr)
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="opencode-memory",
        description="Append a BEL-154 raw ingest record (source='opencode') "
                    "for the promotion pipeline",
    )
    parser.add_argument("--source-id", default="",
                        help="session-id / task-id / run-id (default: opencode:<ts>)")
    parser.add_argument("--content", default="",
                        help="task summary / response content (else read stdin)")
    parser.add_argument("--stdin", action="store_true",
                        help="read --content from stdin")
    parser.add_argument("--agent", default=_DEFAULT_AGENT)
    parser.add_argument("--company", default="asp")
    parser.add_argument("--project", default="aspen-os")
    parser.add_argument("--files", default=None,
                        help="comma-separated files_touched list")
    parser.add_argument("--tools", default=None,
                        help="comma-separated tools_used list")
    parser.add_argument("--linear-refs", default=None,
                        help="comma-separated Linear ticket ids (BEL-123)")
    parser.add_argument("--paperclip-refs", default=None,
                        help="comma-separated Paperclip issue ids (ASP-60)")
    parser.add_argument("--ingest-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    def _split(value: str | None) -> list[str] | None:
        return [p.strip() for p in value.split(",") if p.strip()] if value else None

    content = args.content
    if args.stdin or not content:
        content = sys.stdin.read().strip()

    path = ingest_opencode_record(
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
        print("error: failed to write opencode ingest record", file=sys.stderr)
        return 2

    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
