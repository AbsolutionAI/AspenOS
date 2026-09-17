#!/usr/bin/env python3
"""Aspen Sentinel fleet overview CLI (ADR-0007 / ASP-597).

Publishes the aggregate plants/nodes/status overview (``degraded[]``) on
``aspen.sentinel.fleet.overview``, fanning in from the existing fleet
heartbeat / register / ops.status subjects, backed by an append-only JSONL
journal and mirrored into JetStream when a broker is reachable.

Subcommands:
    emit     publish one overview now (journals + best-effort JetStream)
    daemon   subscribe fan-in subjects + publish every interval
    tail     [-n N] [--json]          newest overviews from the JSONL journal
    check    [--online]               journal + registry + stream state

Works fully offline for journal commands. ``daemon`` / ``check --online`` need
a broker at $ASPEN_NATS_URL (or ``--nats-url``).

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


def _print_overviews(overviews: list[dict], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(overviews, indent=2, default=str))
        return
    if not overviews:
        print("(no fleet overviews)")
        return
    for overview in overviews:
        print(
            f"{overview.get('ts', '').replace('T', ' ').replace('Z', '')}  "
            f"{overview.get('overview_id', '')[:8]}  "
            f"status={overview.get('status', '?'):<9}  "
            f"nodes={overview.get('total_nodes', 0):<3}  "
            f"degraded={overview.get('degraded', [])}"
        )


async def cmd_emit(args: argparse.Namespace) -> int:
    from sentinel import FleetOverviewProducer

    producer = FleetOverviewProducer(
        nats_url=args.nats_url, overview_log=args.log or None,
    )
    await producer.start()
    overview = await producer.publish_now()
    print(json.dumps(overview, indent=2, default=str))
    await producer.close()
    return 0


async def cmd_daemon(args: argparse.Namespace) -> int:
    from sentinel import FleetOverviewProducer

    producer = FleetOverviewProducer(
        nats_url=args.nats_url, overview_log=args.log or None,
        interval_seconds=args.interval,
    )
    connected = await producer.start()
    print(
        f"fleet-overview daemon: interval={producer._interval_seconds}s "
        f"nats={'online' if connected else 'offline (journal-only)'} "
        f"journal={producer.overview_log_path}"
    )
    try:
        await producer.run_loop()
    except KeyboardInterrupt:
        print("stopped")
    await producer.close()
    return 0


async def cmd_tail(args: argparse.Namespace) -> int:
    from sentinel import FleetOverviewProducer

    producer = FleetOverviewProducer(overview_log=args.log or None)
    _print_overviews(producer.tail(args.n), as_json=args.json)
    return 0


async def cmd_check(args: argparse.Namespace) -> int:
    from sentinel import FleetOverviewProducer

    producer = FleetOverviewProducer(nats_url=args.nats_url, overview_log=args.log or None)
    if args.online:
        await producer.start()
    report = await producer.check()
    print(json.dumps(report, indent=2, default=str))
    await producer.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel-fleet-overview",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--nats-url", help="NATS broker URL (default: $ASPEN_NATS_URL)")
    parser.add_argument("--log", help="JSONL journal path (default: $ASPEN_FLEET_OVERVIEW_LOG)")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("emit", help="publish one overview now")

    daemon = sub.add_parser("daemon", help="subscribe fan-in + periodic publish")
    daemon.add_argument(
        "--interval", type=int, default=None,
        help="publish interval seconds (default 30 / $ASPEN_FLEET_OVERVIEW_INTERVAL)",
    )

    tail = sub.add_parser("tail", help="newest overviews from the JSONL journal")
    tail.add_argument("-n", type=int, default=DEFAULT_TAIL, help=f"count (default {DEFAULT_TAIL})")
    tail.add_argument("--json", action="store_true", help="raw JSON output")

    check = sub.add_parser("check", help="journal + registry + stream state")
    check.add_argument("--online", action="store_true", help="attempt broker connection for stream info")

    return parser


async def main_async(args: argparse.Namespace) -> int:
    handlers = {
        "emit": cmd_emit,
        "daemon": cmd_daemon,
        "tail": cmd_tail,
        "check": cmd_check,
    }
    handler = handlers[args.command]
    return await handler(args)


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())