# Findings — Slice 02-13

Unit tests for `ladder_planner.py` and `ladder_watchdog.py`.

---

## Existing coverage (before this slice)

`tests/test_ladder_planner.py` existed but had minimal coverage of the
dataclass methods and none of the watchdog functions.

---

## New coverage added

| Module / Function | Tests | Notes |
|-------------------|-------|-------|
| `amount_fmt` | 5 | XCH/CAT/mojos ranges, exactly 1 XCH, zero |
| `LadderPlan.ready_count` / `oversize_count` / `unready_count` | 3 | via helper |
| `LadderPlan.is_viable` | 4 | all ready, threshold met/not-met, empty |
| `LadderPlan.summary` | 1 | key presence |
| `plan_ladder` | 6 | all assigned, empty coins, no reuse, viable, reshapes, side attr |
| `AuditResult.has_errors` / `has_warnings` | 4 | error/warn/info/empty |
| `audit_ladder_shape` | 7 | empty, correct count, mismatch, taper violation, std inversion, rev inversion, ok=False |
| `check_coin_invariants` | 7 | balanced, inv mismatch, xch mismatch, cat mismatch, tolerance, zero wallet, summary keys |

**37 new tests** in `tests/test_plan_02_13_ladder_planner_watchdog_unit.py`.

---

## No bugs found

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 0 | blocked |
