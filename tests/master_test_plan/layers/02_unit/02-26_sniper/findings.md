# Findings — Slice 02-26

Unit tests for `sniper.py`.

## New coverage added

| Function | Tests | Notes |
|----------|-------|-------|
| `_bps_to_pct` | 7 | <1% two decimals, ≥1% one decimal, string input, invalid input |
| `Sniper.prune_active_snipes` | 5 | empty, all open, some closed, all closed, side-dict also pruned |
| `Sniper.get_stats` | 4 | expected keys, initial zeros, active count reflects list, thread-safe |
| `Sniper._calculate_snipe_size` | 4 | uses SNIPER_SIZE, fallback to DEFAULT, capped by MAX_TRADE, arb_gap ignored |

**20 new tests** in `tests/test_plan_02_26_sniper_unit.py`.

## No bugs found
