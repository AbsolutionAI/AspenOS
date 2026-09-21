#!/usr/bin/env python3
"""Aspen Sentinel tool-anomaly detector CLI (F-015 / ASP-379).

Runs the fail-open behavioral detector over tool-audit events (ADR-0007,
source = sentinel JSONL journal by default). Log-only by design: findings are
never a hard gate on ``propose_act``.

Sources, in priority order for ``scan``:
    1. ``--jsonl PATH``       JSONL audit journal (``-`` = stdin)
    2. ``--from-audit-db``    legacy services.audit SQLite trail
    3. default                $ASPEN_AUDIT_LOG / /var/lib/aspen/sentinel/audit.jsonl

Exit codes: 0 ok (findings are informational), 2 usage.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_PYTHON = SCRIPT_DIR.parent / "src" / "python"
if str(SRC_PYTHON) not in sys.path:
    sys.path.insert(0, str(SRC_PYTHON))


def _print_findings(findings) -> None:
    if not findings:
        print("(no anomalies detected — fail-open, log-only)")
        return
    for f in findings:
        print(
            f"{f.severity.upper():<7} {f.rule:<32} actor={f.actor:<24} "
            f"window={f.window_s:g}s  fail_open={f.fail_open}"
        )
        print(f"        {f.message}")


def cmd_scan(args: argparse.Namespace) -> int:
    from sentinel.tool_anomaly import (
        ToolAnomalyDetector,
        default_journal,
        read_audit_logger,
        read_jsonl,
    )

    if args.jsonl:
        source = read_jsonl(args.jsonl)
        src_label = args.jsonl if args.jsonl != "-" else "<stdin>"
    elif args.from_audit_db:
        source = read_audit_logger()
        src_label = "services.audit"
    else:
        journal = args.journal or default_journal()
        if not os.path.exists(journal):
            print(f"ERROR: journal not found: {journal}", file=sys.stderr)
            return 1
        source = read_jsonl(journal)
        src_label = journal

    detector = ToolAnomalyDetector(window_s=args.window)
    findings = detector.scan(source)

    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2, default=str))
    else:
        print(f"Scanned {len(source)} event(s) from {src_label}; "
              f"{len(findings)} finding(s).")
        _print_findings(findings)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tool-anomaly",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="run the detector over audit events")
    scan.add_argument("--jsonl", help="JSONL audit journal path ('-' for stdin)")
    scan.add_argument("--journal", help="default JSONL journal path (overrides $ASPEN_AUDIT_LOG)")
    scan.add_argument("--from-audit-db", action="store_true",
                      help="scan the legacy services.audit SQLite trail instead of a journal")
    scan.add_argument("--window", type=float, default=120.0,
                      help="sliding window seconds (default 120)")
    scan.add_argument("--json", action="store_true", help="raw JSON findings output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return cmd_scan(args)


if __name__ == "__main__":
    sys.exit(main())