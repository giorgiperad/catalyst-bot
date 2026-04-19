# Findings — Slice 02-25

Unit tests for `reaction_strategy.py` (pure functions) and `dynamic_amm_buffer.py` (sweep tracker).

---

## New coverage added

| Module / Function | Tests | Notes |
|-------------------|-------|-------|
| `RequoteSeverity` enum | 4 | 5 members, names, NONE/EMERGENCY accessible |
| `CycleBudget` dataclass | 13 | defaults, custom limits, can_cancel/create, use_cancel/create, remaining, total, exhausted, non-negative floor |
| `compute_offer_staleness` | 7 | perfect match, 5% deviation, missing/zero/invalid price, always non-negative |
| `classify_drift` | 9 | zero, below, at inner/mid/full/emergency thresholds, above emergency, custom thresholds |
| `tiers_for_severity` | 5 | NONE→∅, INNER→{inner}, INNER_MID→{inner,mid}, FULL/EMERGENCY→all-4 |
| `filter_offers_by_tiers` | 6 | empty, all match, some match, no match, missing tier→mid, case insensitive |
| `TIER_PRIORITY` | 3 | inner=0, extreme=3, 4 tiers |
| `DynamicAMMBuffer` + `reset_buffer` | 10 | fresh=0 sweeps, record_sweep, multiple sweeps, reset, 0/1/3/6 sweep multipliers, string bps, module-level API |

**57 new tests** in `tests/test_plan_02_25_dynamic_amm_buffer_reaction_strategy_unit.py`.

---

## Notes

`reaction_strategy.py` is entirely pure — tests require no mocking.
`DynamicAMMBuffer` uses default config values (via `getattr(cfg, ..., default)`) so
multiplier tests work without config patching. `reset_buffer()` is provided
explicitly for test isolation.

---

## No bugs found
