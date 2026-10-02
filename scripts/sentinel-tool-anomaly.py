#!/usr/bin/env python3
"""Aspen Sentinel tool-anomaly consumer CLI (ADR-0007 / ASP-687).

Subscribes to the tool-audit subject, feeds every event through
``ToolAnomalyDetector``, and publishes findings to ``aspen.sentinel.tools.anomaly``
so ops can page on R1 (high) and template on R2-R4.

Subcommands:
    daemon   subscribe aspen.sentinel.audit.event, journal + publish findings
    scan     run the detector over an audit journal once (no broker needed)
    tail     [-n N] [--json]          newest findings from the findings journal
    check    [--online]               journal + stream + counters

`scan` / `tail` / `check` work fully offline. `daemon` needs a broker at
$ASPEN_NATS_URL (or --nats-url); without one it reports journal-only and stays up.

Exit codes: 0 ok, 1 error, 2 usage.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_PYTHON = SCRIPT_DIR.parent / "src" / "python"
if str(SRC_PYTHON) not in sys.path:
    sys.path.insert(0, str(SRC_PYTHON))

DEFAULT_TAIL = 20


def _print_findings(findings: list[dict], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(findings, indent=2, default=str))
        return
    if not findings:
        print("(no anomaly findings)")
        return
    for f in findings:
        print(
            f"{str(f.get('severity', '')).upper():<7} "
            f"{str(f.get('rule', '')):<32} "
            f"actor={str(f.get('actor', '')):<24} "
            f"{(f.get('ts') or '').replace('T', ' ').replace('Z', '')}"
        )
        print(f"        {f.get('message', '')}")


async def cmd_daemon(args: argparse.Namespace) -> int:
    from sentinel.anomaly_consumer import AnomalyConsumer

    consumer = AnomalyConsumer(
        nats_url=args.nats_url,
        anomaly_log=args.log or None,
        audit_log=args.audit_log or None,
    )
    connected = await consumer.start()
    print(
        f"tool-anomaly daemon: nats={'online' if connected else 'offline (journal-only)'} "
        f"findings_journal={consumer.anomaly_log_path} "
        f"publish_subject=aspen.sentinel.tools.anomaly",
        flush=True,
    )
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await consumer.close()
    print(consumer.stats)
    return 0


async def cmd_scan(args: argparse.Namespace) -> int:
    from sentinel.anomaly_consumer import AnomalyConsumer

    consumer = AnomalyConsumer(
        anomaly_log=args.log or None,
        audit_log=args.audit_log or None,
    )
    envelopes = consumer.scan_journal(limit=args.limit)
    if args.json:
        print(json.dumps(envelopes, indent=2, default=str))
    else:
        source = args.audit_log or os.environ.get(
            "ASPEN_AUDIT_LOG", "/var/lib/aspen/sentinel/audit.jsonl"
        )
        print(
            f"Scanned {consumer.stats['events_seen']} audit event(s) from {source}; "
            f"{len(envelopes)} finding(s) journaled to {consumer.anomaly_log_path}"
        )
        _print_findings(envelopes)
    return 0


async def cmd_tail(args: argparse.Namespace) -> int:
    from sentinel.anomaly_consumer import AnomalyConsumer

    consumer = AnomalyConsumer(anomaly_log=args.log or None)
    _print_findings(consumer.tail(args.n), as_json=args.json)
    return 0


async def cmd_check(args: argparse.Namespace) -> int:
    from sentinel.anomaly_consumer import AnomalyConsumer

    consumer = AnomalyConsumer(
        nats_url=args.nats_url, anomaly_log=args.log or None
    )
    if args.online:
        await consumer.start()
    report = await consumer.check()
    print(json.dumps(report, indent=2, default=str))
    await consumer.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel-tool-anomaly",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--nats-url", help="NATS broker URL (default: $ASPEN_NATS_URL)")
    parser.add_argument(
        "--log", help="findings JSONL journal (default: $ASPEN_ANOMALY_LOG)"
    )
    parser.add_argument(
        "--audit-log", help="audit JSONL journal (default: $ASPEN_AUDIT_LOG)"
    )

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("daemon", help="subscribe audit events, journal + publish findings")

    scan = sub.add_parser("scan", help="one-shot detector run over the audit journal")
    scan.add_argument("--limit", type=int, default=100000, help="max audit events to read")
    scan.add_argument("--json", action="store_true", help="raw JSON findings output")

    tail = sub.add_parser("tail", help="newest findings from the findings journal")
    tail.add_argument("-n", type=int, default=DEFAULT_TAIL, help=f"count (default {DEFAULT_TAIL})")
    tail.add_argument("--json", action="store_true", help="raw JSON output")

    check = sub.add_parser("check", help="journal + stream + counter state")
    check.add_argument(
        "--online", action="store_true", help="attempt broker connection for stream info"
    )

    return parser


async def main_async(args: argparse.Namespace) -> int:
    handlers = {
        "daemon": cmd_daemon,
        "scan": cmd_scan,
        "tail": cmd_tail,
        "check": cmd_check,
    }
    return await handlers[args.command](args)


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())