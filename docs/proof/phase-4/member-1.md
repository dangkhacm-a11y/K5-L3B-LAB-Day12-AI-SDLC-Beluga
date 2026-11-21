# Phase 4 — Member 1 verification

Code commit: see commit containing this file.

## Commands and results

- `PYTHONPATH=tests:. python3 -m unittest tests.test_phase4_bench_soak -v` — 3 tests pass.
- `python3 -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json` — completed; output has exactly `avg_fps`, `p1_low_fps`, `frames`, `measured_s`, `load_ms`.
- `python3 -m chonoi.soak --seed 7 --days 10 --out docs/proof/phase-4/soak.json` — `days_completed=10`, `crashes=0`, one result per Shop close, D1–D5 plan repeats D6–D10.
- Five in-process DaySim regression tests pass: initial plan, pause/resume, shop purchases, close/progression, and upgrade progression.

## Scope and measurement note

The benchmark measures steady-state simulation ticks per second in the Gather runtime loop, not browser rendered frames. It currently reports these tick rates in the contract's `avg_fps` and `p1_low_fps` fields because the ticket defines those field names but does not define a browser harness. Do not treat comparison to the FPS goals as official until PO confirms this interpretation; see `docs/clarify.md`.

The soak uses an empty deterministic input stream. It verifies the ten-day process, phase transitions, schedule replay, and no-crash condition; it does not demonstrate positive earnings or successful customer service. Results retain current cumulative earned/reputation/score when Shop closes.

The broader Day end-to-end regression currently hits an existing Gather ↔ Day item schema mismatch on this branch (`fresh` item records vs legacy string hold). That cross-module handoff needs the Phase 3 owners to reconcile before claiming the full Day regression passes.
