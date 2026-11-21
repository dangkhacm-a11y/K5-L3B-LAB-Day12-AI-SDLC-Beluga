# Member 1 — Gather handoff (Phase 3)

Implemented Gather-side individual inventory and freshness loop, plus the current schedule and movement. `GatherSim.inventory_items()` returns an ordered list of `{id, kind, fresh}` records, and `gather_end.data.inventory` is `{items: [...]}`. IDs use shared `IdAllocator` prefix `I`, reserve IDs already present in the hold, and are allocated for each successful gather/catch. Freshness decays each Gather tick, and items below `spoiled_below` leave the hold with a `spoiled` event. Monster loss and faint remove individual records from the end of the hold (LIFO).

Current behavior follows the user-approved assumption recorded in `docs/clarify.md`: direction ±1 via `Streams`, `current_warning`, horizontal velocity addition at/under `min_depth`, `random_current:false`, and a deterministic `current_direction` fixture. Current state is exposed in snapshots.

## Verification

- `PYTHONPATH=tests:. python3 -m unittest tests.test_gather_phase3_freshness -v` — 10 tests pass (PowerShell equivalent: `$env:PYTHONPATH='tests;.'; python -m unittest tests.test_gather_phase3_freshness -v`).
- `git diff --check` — pass.
- Legacy Gather and monster tests currently fail against this checkout's runner API (`Session.tick` missing / API mismatch), and old inventory assertions expect count-map v1.1. Full TICKET-03 integration still needs Member 3's contract/scenario/inventory adapter and Member 4's integration updates.

## Integration notes

Member 3 should preserve this list API and `gather_end` wrapper, then connect the day handoff and inventory writer to it. Contract defaults currently fall back to no freshness decay and a basic current cycle until v1.2 tuning is merged. Legacy string hold fixtures are converted to item records temporarily for in-process compatibility; v1.2 scenario validation should only admit item records.
