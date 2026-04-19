# Findings — Slice 02-19

Unit tests for `fill_tracker.py` + `fill_classifier.py`.

---

## Existing coverage (before this slice)

None — no tests referenced these modules directly.

---

## New coverage added

| Module / Function | Tests | Notes |
|-------------------|-------|-------|
| `FillType` constants | 2 | All 5 types defined, values are strings |
| `FillClassification.is_arb` | 5 | retail/unknown=False, sweep_buy/sell/combined=True |
| `classify_fill` | 8 | No dexie→UNKNOWN, dexie no signals→RETAIL, combined flag, matched_offers, arb hash sell/buy, reasons populated, spent_block_index |
| `_extract_taker_puzzle_hash` | 4 | None, no output_coins, buy-side xch, fallback key |
| `FillTracker._parse_iso_ts` | 4 | Valid ISO, None, empty, invalid |
| `FillTracker._extract_dexie_coin_ids` | 4 | input_coins, output_coins, empty, 0x strip |
| `FillTracker._check_mass_disappearance` | 4 | Zero previous, small, first strike, 3-strike accept |
| `FillTracker` state helpers | 6 | time_since_last_fill, get_fill_history/limit, get_fill_counts, set_baseline |

**37 new tests** in `tests/test_plan_02_19_fill_tracker_classifier_unit.py`.

---

## Test corrections

`classify_fill` and `_extract_taker_puzzle_hash` import `cfg` lazily inside the function
via `from config import cfg`. Tests that need to control cfg must patch `config.cfg`, not
`fill_classifier.cfg` (the latter doesn't exist at module level). Fixed all 4 affected tests.

---

## No bugs found

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 0 | blocked |
