"""Startup gate (H-003): require native C11 binaries, fail closed on absence.

Run at systemd unit start:
    python3 -m native_check
Exits non-zero if sandbox_run or policyexec cannot be found.
"""

from __future__ import annotations

import sys


def main() -> int:
    errors = []
    try:
        from policy_native import require_native as require_policyexec

        print(f"policyexec: {require_policyexec()}")
    except Exception as e:
        errors.append(f"policyexec: {e}")
    try:
        from sandbox_native import require_native as require_sandbox_run

        print(f"sandbox_run: {require_sandbox_run()}")
    except Exception as e:
        errors.append(f"sandbox_run: {e}")
    if errors:
        for err in errors:
            print(f"FATAL: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
