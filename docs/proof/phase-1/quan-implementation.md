# Quán implementation verification — 2026-11-21

Scope: `chonoi/sim/quan.py`. No test files added or edited by this implementation.

- `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`: **66 tests passed** against the latest workspace. Ran outside the sandbox to allow the existing local HTTP server test.
- `python3 -m chonoi.headless --mode quan --seed 1 --ticks 600 --out /tmp/beluga-quan-600.jsonl`: exit 0; empty stock emits `no_dish` with `{}` at tick 120.
- `python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --out /tmp/beluga-gather-600.jsonl`: exit 0.
- Manual headless service with contract tuning: cook at tick 1, ready/pickup at 361, serve at 507, pay at 1107; money/earned 72, reputation 3.2. Two seed-42 runs produced identical bytes.
- Manual closing run: last-tick service emitted `served`, `paid` (reason `closing`), then one `quan_end`; money 60, reputation unchanged.
- Manual timeout run: assigned order left at tick 1 with reputation 2.5; carried food discarded.
- Manual arrivals run: customer at tick 120, timeout and replacement at tick 3720; IDs continued from C1 to C2.
- Invalid reservation exceeding stock: exit 2 before creating the output file.

Temporary scenario/input/output files used for manual runs were kept under `/tmp`.
