# Findings — Slice 02-27

Unit tests for `boost_manager.py`.

## New coverage added

| Function | Tests | Notes |
|----------|-------|-------|
| `_bps_to_pct` | 3 | 30bps, 100bps, invalid input |
| `BoostManager._find_stale_offers` | 8 | empty, zero mid, no offer_manager, stale/fresh, sorted most-stale-first, missing trade_id, _distance_bps appended |

**11 new tests** in `tests/test_plan_02_27_boost_manager_unit.py`.

`_find_stale_offers` tested using a minimal `_FakeOfferManager` with a
`_offer_details_cache` dict — the only external dependency of this method.

## No bugs found
