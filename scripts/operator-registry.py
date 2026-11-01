#!/usr/bin/env python3
"""Aspen operator registry CLI (ADR-0012 step 1).

Enroll, list, revoke, and inspect operator-of-record entries in the
local operator registry (JSON-backed).

Subcommands:
    enroll <human_id> <display_name>   register a new operator
    list                                list active operators
    revoke <human_id>                   deactivate an operator
    show <human_id>                     show operator details

Exit codes: 0 ok, 1 error, 2 usage.
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_PYTHON = SCRIPT_DIR.parent / "src" / "python"
if str(SRC_PYTHON) not in sys.path:
    sys.path.insert(0, str(SRC_PYTHON))


def cmd_enroll(args: argparse.Namespace) -> int:
    from services.operator_registry import OperatorRegistry

    registry = OperatorRegistry(db_path=args.registry)
    try:
        op = registry.enroll(
            human_id=args.human_id,
            display_name=args.display_name,
            enrolled_by=args.enrolled_by or "",
            aliases=args.aliases,
            plant_id=args.plant_id or "",
        )
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(json.dumps({
        "human_id": op.human_id,
        "display_name": op.display_name,
        "enrolled_at": op.enrolled_at,
        "status": op.status,
    }, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    from services.operator_registry import OperatorRegistry

    registry = OperatorRegistry(db_path=args.registry)
    operators = registry.list(active_only=not args.all)
    if not operators:
        print("(no operators)")
        return 0
    for op in operators:
        alias_str = f" aliases={op.aliases}" if op.aliases else ""
        print(f"{op.human_id:<24}  {op.display_name:<20}  {op.status:<8}  {op.plant_id}{alias_str}")
    return 0


def cmd_revoke(args: argparse.Namespace) -> int:
    from services.operator_registry import OperatorRegistry

    registry = OperatorRegistry(db_path=args.registry)
    if registry.revoke(args.human_id):
        print(f"revoked: {args.human_id}")
        return 0
    print(f"error: operator '{args.human_id}' not found", file=sys.stderr)
    return 1


def cmd_show(args: argparse.Namespace) -> int:
    from services.operator_registry import OperatorRegistry

    registry = OperatorRegistry(db_path=args.registry)
    op = registry.get(args.human_id)
    if op is None:
        print(f"error: operator '{args.human_id}' not found", file=sys.stderr)
        return 1
    print(json.dumps({
        "human_id": op.human_id,
        "display_name": op.display_name,
        "enrolled_at": op.enrolled_at,
        "enrolled_by": op.enrolled_by,
        "aliases": op.aliases,
        "status": op.status,
        "plant_id": op.plant_id,
    }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="operator-registry",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--registry",
        help="path to registry JSON file (default: /var/lib/aspen/operator-registry.json)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    enroll = sub.add_parser("enroll", help="register a new operator")
    enroll.add_argument("human_id", help="canonical operator identifier")
    enroll.add_argument("display_name", help="human-readable display name")
    enroll.add_argument("--enrolled-by", help="who performed the enrollment")
    enroll.add_argument("--aliases", nargs="*", default=[], help="alternate identifiers (email, MXID, etc.)")
    enroll.add_argument("--plant-id", help="plant this operator belongs to")

    list_p = sub.add_parser("list", help="list operators")
    list_p.add_argument("--all", action="store_true", help="include revoked operators")

    revoke = sub.add_parser("revoke", help="deactivate an operator")
    revoke.add_argument("human_id", help="operator to revoke")

    show = sub.add_parser("show", help="show operator details")
    show.add_argument("human_id", help="operator to inspect")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    handlers = {
        "enroll": cmd_enroll,
        "list": cmd_list,
        "revoke": cmd_revoke,
        "show": cmd_show,
    }
    handler = handlers[args.command]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())