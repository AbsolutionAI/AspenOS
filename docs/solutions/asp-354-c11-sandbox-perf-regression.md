# ASP-354 — C11 sandbox performance investigation

Date: 2026-08-23 · Node: BT-ASP-SRV (kernel 7.0.0-30-generic, 16 cores, uid 1000)

## Symptom

Benchmark reported `c11_internal_wall` p50 ≈ 2.8–3.4 ms against a "<2 ms" gate
(ASP-189), while the smoke test asserted absolute p50 (relaxed to 5.0 ms to keep
CI green).

## Root causes

1. **Criterion misread.** ADR 0001 line 57 says *“Overhead p50 < 2ms for trivial
   command (vs Python baseline)”* — overhead vs the Python baseline, not absolute
   latency. `scripts/bench-sandbox.sh` compared the absolute internal p50 against
   the threshold.
2. **Environmental floor.** Pure fork+exec+wait of `/bin/echo` inside sandbox_run
   is p50 ≈ 2.9 ms on this kernel before any isolation feature. The ADR's original
   "≪ 2 ms" verdict was measured on different hardware/kernel. The C path also pays
   double process creation in outer-spawn terms (python→sandbox_run→echo).
3. **seccomp cost is small but real:** +0.46 ms p50 (rule_add building ~60 cBPF
   rules). Could be cut by hoisting filter construction before the wall-clock start
   if ever needed.
4. **Namespaces silently no-op unprivileged.** `unshare(CLONE_NEWNS/NEWPID)` fails
   EPERM for uid 1000; soft-fail meant every run printed `ns=1` while achieving no
   isolation, contributing ~0 ms.

## Evidence (N=300 interleaved, p50 ms)

| variant                | internal | delta |
|------------------------|---------:|------:|
| bare fork+exec+wait    |    2.911 |     — |
| + seccomp              |    3.377 | +0.46 |
| + ns (unprivileged)    |      ±0  |     0 |
| py_exec baseline       |    2.782 |     — |

## Changes

- `scripts/bench-sandbox.sh`: assert **overhead** = c11_internal_p50 − py_exec_p50
  < 2 ms (`ADR_P50_OVERHEAD_MAX`, default 2.0) per ADR wording; absolutes still reported.
- `sandbox_run.c`: warn on namespace soft-fail (`need CAP_SYS_ADMIN`); summary line
  relabelled `ns_req=` so requested ≠ achieved is visible.

## Result

Overhead p50 ≈ +0.51 ms ≪ 2 ms → ADR criterion PASS without weakening anything.

## Follow-ups

- If absolute latency ever matters, hoist seccomp filter construction pre-fork
  (~−0.46 ms) or run sandbox under a privileged supervisor to get real ns isolation.
- **Architect ratification (2026-08-23, Aspen):** **APPROVED.** ADR 0001 gate is
  `overhead = c11_internal_p50 − py_exec_p50 < 2 ms`. Absolute internal latency is
  diagnostic only. Bench + smoke labels aligned; ADR text clarified so the historical
  absolute table cannot re-introduce the misread.
