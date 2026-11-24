#!/usr/bin/env bash
# Print C11 internal p50/p95 across sandbox modes on this runner.
# Diagnostic only — does not gate. Exit 0 always so a measure job is not a required check.
# Usage: bash scripts/c11-bench-modes.sh [N]
set -u
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"
N="${1:-100}"
SB="$REPO_DIR/src/c/sandbox_spike/sandbox_run"

if [[ ! -x "$SB" ]]; then
  make -C src/c/sandbox_spike all || exit 1
fi

model="$(awk -F: '/model name/{gsub(/^[ \t]+/, "", $2); print $2; exit}' /proc/cpuinfo 2>/dev/null || true)"
echo "runner_uname=$(uname -sr)"
echo "runner_nproc=$(nproc 2>/dev/null || echo unknown)"
echo "runner_model=${model:-unknown}"
if [[ -n "${RUNNER_NAME:-}" ]]; then
  echo "runner_name=$RUNNER_NAME"
fi
if [[ -n "${RUNNER_OS:-}" ]]; then
  echo "runner_os=$RUNNER_OS runner_arch=${RUNNER_ARCH:-unknown}"
fi

python3 - "$SB" "$N" <<'PY'
import re, statistics, subprocess, sys, time

sb, n = sys.argv[1], int(sys.argv[2])

def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    i = min(len(xs) - 1, max(0, int(len(xs) * p / 100)))
    return xs[i]

modes = [
    ("default", [sb, "--timeout", "2", "--", "/bin/echo", "ok"]),
    ("no-seccomp", [sb, "--timeout", "2", "--no-seccomp", "--", "/bin/echo", "ok"]),
    ("no-ns", [sb, "--timeout", "2", "--no-ns", "--", "/bin/echo", "ok"]),
    ("bare", [sb, "--timeout", "2", "--no-seccomp", "--no-ns", "--", "/bin/echo", "ok"]),
    ("echo", ["/bin/echo", "ok"]),
]

for cmd in (m[1] for m in modes):
    for _ in range(5):
        subprocess.run(cmd, capture_output=True)

print(f"{'mode':<14} {'p50_ms':>8} {'p95_ms':>8} {'mean_ms':>8} {'min_ms':>8}  source  n={n}")
print("-" * 72)
for name, cmd in modes:
    internal = []
    outer = []
    for _ in range(n):
        t0 = time.perf_counter()
        r = subprocess.run(cmd, capture_output=True, text=True)
        outer.append((time.perf_counter() - t0) * 1000)
        m = re.search(r"wall_ms=([0-9.]+)", r.stderr or "")
        if m:
            internal.append(float(m.group(1)))
    src = internal if internal else outer
    label = "internal" if internal else "outer"
    print(
        f"{name:<14} {pct(src,50):8.3f} {pct(src,95):8.3f} "
        f"{statistics.mean(src):8.3f} {min(src):8.3f}  {label}"
    )
PY
exit 0
