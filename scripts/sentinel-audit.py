#!/usr/bin/env python3
"""Aspen Sentinel audit trail CLI (ADR-0007 / H-015 / ASP-537).

Emits and reads durable audit events on ``aspen.sentinel.audit.event``, backed
by an append-only JSONL journal and mirrored into JetStream.

Subcommands:
    emit     --actor A --action X [--target T --result R]   record one event
    tail     [-n N] [--json]                                 last N events (JSONL)
    query    [--actor A --action X --target T --result R --since ISO --limit N]
    replay                                 jsonl -> JetStream backfill (idempotent)
    js-last  [-n N]                      tail the JetStream stream
    check                                stream + journal state

Works fully offline for journal commands (emit/tail/query/replay-none).
``replay`` / ``js-last`` / ``check --online`` need a broker at $ASPEN_NATS_URL
(or ``--nats-url``).

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


def _print_events(events: list[dict], as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(events, indent=2, default=str))
        return
    if not events:
        print("(no audit events)")
        return
    for event in events:
        print(
            f"{event.get('ts', '').replace('T', ' ').replace('Z', '')}  "
            f"{event.get('event_id', '')[:8]}  "
            f"{event.get('actor', ''):<24}  "
            f"{event.get('action', ''):<36}  "
            f"{event.get('target', ''):<24}  "
            f"{event.get('result', '')}"
        )


async def cmd_emit(args: argparse.Namespace) -> int:
    from sentinel import AuditEventPublisher

    publisher = AuditEventPublisher(
        nats_url=args.nats_url, audit_log=args.log or None,
    )
    await publisher.start()
    event = await publisher.record(
        args.actor, args.action, target=args.target, result=args.result,
    )
    print(json.dumps(event, indent=2, default=str))
    await publisher.close()
    return 0


async def cmd_tail(args: argparse.Namespace) -> int:
    from sentinel import AuditEventPublisher

    publisher = AuditEventPublisher(audit_log=args.log or None)
    _print_events(publisher.tail(args.n), as_json=args.json)
    return 0


async def cmd_query(args: argparse.Namespace) -> int:
    from sentinel import AuditEventPublisher

    publisher = AuditEventPublisher(audit_log=args.log or None)
    events = publisher.query(
        actor=args.actor, action=args.action, target=args.target,
        result=args.result, since=args.since, limit=args.limit,
    )
    _print_events(events, as_json=args.json)
    return 0


async def cmd_replay(args: argparse.Namespace) -> int:
    from sentinel import AuditEventPublisher

    publisher = AuditEventPublisher(
        nats_url=args.nats_url, audit_log=args.log or None,
    )
    connected = await publisher.start()
    if not connected:
        print(f"ERROR: offline — cannot replay to JetStream ({args.nats_url or os.environ.get('ASPEN_NATS_URL') or 'no URL'})", file=sys.stderr)
        return 1
    count = await publisher.replay_pending()
    print(f"Replayed {count} pending audit event(s) to {publisher.SUBJECT_AUDIT_EVENT}")
    await publisher.close()
    return 0


async def cmd_js_last(args: argparse.Namespace) -> int:
    from sentinel import AuditEventPublisher

    publisher = AuditEventPublisher(
        nats_url=args.nats_url, audit_log=args.log or None,
    )
    connected = await publisher.start()
    if not connected:
        print(f"ERROR: offline — no JetStream access ({args.nats_url or os.environ.get('ASPEN_NATS_URL') or 'no URL'})", file=sys.stderr)
        return 1
    try:
        events = await publisher.js_last(args.n)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    _print_events(events)
    await publisher.close()
    return 0


async def cmd_check(args: argparse.Namespace) -> int:
    from sentinel import AuditEventPublisher

    publisher = AuditEventPublisher(
        nats_url=args.nats_url, audit_log=args.log or None,
    )
    if args.online:
        await publisher.start()
    report = await publisher.check()
    print(json.dumps(report, indent=2, default=str))
    await publisher.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel-audit",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--nats-url", help="NATS broker URL (default: $ASPEN_NATS_URL)")
    parser.add_argument("--log", help="JSONL journal path (default: $ASPEN_AUDIT_LOG)")

    sub = parser.add_subparsers(dest="command", required=True)

    emit = sub.add_parser("emit", help="record one audit event")
    emit.add_argument("--actor", required=True, help="acting agent/principal")
    emit.add_argument("--action", required=True, help="action performed")
    emit.add_argument("--target", default="", help="acted-upon resource")
    emit.add_argument("--result", default="ok", help="outcome (ok/deny/failed/...)")

    tail = sub.add_parser("tail", help="last N events from the JSONL journal")
    tail.add_argument("-n", type=int, default=DEFAULT_TAIL, help=f"count (default {DEFAULT_TAIL})")
    tail.add_argument("--json", action="store_true", help="raw JSON output")

    query = sub.add_parser("query", help="filtered JSONL journal read")
    query.add_argument("--actor")
    query.add_argument("--action")
    query.add_argument("--target")
    query.add_argument("--result")
    query.add_argument("--since", help="only events with ts >= this value")
    query.add_argument("--limit", type=int, default=50)
    query.add_argument("--json", action="store_true")

    sub.add_parser("replay", help="publish un-mirrored JSONL events to JetStream")

    js_last = sub.add_parser("js-last", help="tail the JetStream stream")
    js_last.add_argument("-n", type=int, default=DEFAULT_TAIL, help=f"count (default {DEFAULT_TAIL})")

    check = sub.add_parser("check", help="journal + JetStream state")
    check.add_argument("--online", action="store_true", help="attempt broker connection for stream info")

    return parser


async def main_async(args: argparse.Namespace) -> int:
    handlers = {
        "emit": cmd_emit,
        "tail": cmd_tail,
        "query": cmd_query,
        "replay": cmd_replay,
        "js-last": cmd_js_last,
        "check": cmd_check,
    }
    handler = handlers[args.command]
    return await handler(args)


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())