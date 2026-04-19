# Findings — Slice 02-09

Unit tests for `market_intel.py`.

---

## Existing coverage (before this slice)

None — no tests referenced this module directly.

---

## New coverage added

| Module / Function | Tests | Notes |
|-------------------|-------|-------|
| `_bps_to_pct` | 7 | <1%→2 decimals, ≥1%→1 decimal, boundary at 100 BPS, None/invalid→str |
| `_parse_dexie_offer` | 8 | price calc, zero amounts→None, `is_ours` via known_dexie_ids, via BOT_TAG, malformed→None |
| `_analyse_orderbook` | 8 | empty→zeros, spread calc, inverted book→zeroed bid/ask, own offers excluded, thin buy/sell, whale detection, whale cap at 5 |
| `get_competitor_spread` / `get_cached_data` | 3 | returns dict copy, same data |
| `get_stats` | 2 | all keys present, values are strings |
| `reset_session_stats` | 1 | clears refresh_count, errors, known_dexie_ids, dbx fields |
| `get_market_summary` | 3 | Decimals serialized to strings, dbx block, orderbook metadata |
| `get_orderbook_snapshot` | 3 | empty, counts, our_best_bid |
| `get_spread_recommendation` | 5 | no data→0, zero mid→0, wider→positive, tighter→negative, thin side bonus |
| `check_dbx_eligibility` | 3 | eligible, ineligible, cached second call |

**43 new tests** in `tests/test_plan_02_09_market_intel_unit.py`.

---

## Test design notes

- `market_intel.cfg` is imported at module level (`from config import cfg`), so all tests
  use a `_MI` base class that starts `patch("market_intel.cfg", _FAKE_CFG)` in `setUp`
  and stops it in `tearDown`. This covers both `__init__` (which reads `DBX_MAX_SPREAD_BPS`
  and `DEXIE_ORDERBOOK_PAGE_SIZE`) and all method calls (which read `CAT_ASSET_ID`, `BOT_TAG`).
- `_analyse_orderbook` is called directly with synthetic offer lists — no HTTP.
- `check_dbx_eligibility` is time-gated; tests reset `_dbx["last_check"] = 0` to force recheck.

---

## No bugs found

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 0 | blocked |
