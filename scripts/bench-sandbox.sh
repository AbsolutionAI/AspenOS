#!/usr/bin/env bash
# Starship OS — C11 sandbox vs Python baseline (ADR 0001)
# Usage: bash scripts/bench-sandbox.sh [N]
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"
N="${1:-200}"
SB="$REPO_DIR/src/c/sandbox_spike/sandbox_run"

if [[ ! -x "$SB" ]]; then
  make -C src/c/sandbox_spike all
fi

echo "=== Sandbox benchmark (N=$N) ==="
python3 - "$SB" "$N" <<'PY'
import re, statistics, subprocess, sys, time

sb, n = sys.argv[1], int(sys.argv[2])

def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    i = min(len(xs) - 1, max(0, int(len(xs) * p / 100)))
    return xs[i]

c_internal = []
c_outer = []
py_exec = []
py_shell = []

# warmup
for _ in range(5):
    subprocess.run([sb, "--timeout", "2", "--", "/bin/echo", "ok"], capture_output=True)
    subprocess.run(["/bin/echo", "ok"], capture_output=True)

for _ in range(n):
    r = subprocess.run(
        [sb, "--timeout", "2", "--", "/bin/echo", "ok"],
        capture_output=True, text=True,
    )
    m = re.search(r"wall_ms=([0-9.]+)", r.stderr or "")
    if m:
        c_internal.append(float(m.group(1)))
    t0 = time.perf_counter()
    subprocess.run([sb, "--timeout", "2", "--", "/bin/echo", "ok"], capture_output=True, check=True)
    c_outer.append((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    subprocess.run(["/bin/echo", "ok"], capture_output=True, check=True)
    py_exec.append((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    subprocess.run("/bin/echo ok", shell=True, capture_output=True, check=True)
    py_shell.append((time.perf_counter() - t0) * 1000)

rows = [
    ("c11_internal_wall", c_internal, "fork+exec inside sandbox_run"),
    ("c11_outer_spawn", c_outer, "Python spawns sandbox_run binary"),
    ("py_exec", py_exec, "subprocess.run argv (no shell)"),
    ("py_shell", py_shell, "subprocess shell (CommandExecutor-like)"),
]
print(f"{'metric':<22} {'p50_ms':>8} {'p95_ms':>8} {'mean_ms':>8}  note")
print("-" * 72)
for name, xs, note in rows:
    print(f"{name:<22} {pct(xs,50):8.3f} {pct(xs,95):8.3f} {statistics.mean(xs):8.3f}  {note}")

p50_c = pct(c_internal, 50)
p95_c = pct(c_internal, 95)
p50_py = pct(py_exec, 50)
overhead = p50_c - p50_py
# ASP-807. Absolute 2ms false-fails one ubuntu-latest SKU and passes another
# on the same commit (overhead vs py_exec was 0.338ms on both). Keep the ADR
# 2ms figure as that overhead budget. 5ms absolute ceiling is ~2.1x the slow
# SKU p95 (2.361ms, job 138864085841) and above the host historical max
# (~3.7ms), so SKU spread cannot red the required smoke check.
abs_limit = 5.0
ovr_limit = 2.0
ok_abs = p50_c < abs_limit
ok_ovr = overhead < ovr_limit
ok = ok_abs and ok_ovr
print("-" * 72)
print(
    f"ADR 0001 overhead (c11_internal p50 - py_exec p50 < {ovr_limit:.0f}ms): "
    f"{'PASS' if ok_ovr else 'FAIL'} ({overhead:.3f} ms; "
    f"c11 p50={p50_c:.3f} p95={p95_c:.3f} py_exec p50={p50_py:.3f})"
)
print(
    f"ASP-807 absolute ceiling (c11_internal p50 < {abs_limit:.0f}ms): "
    f"{'PASS' if ok_abs else 'FAIL'} ({p50_c:.3f} ms)"
)
print(f"ADR 0001 criterion: {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
PY
