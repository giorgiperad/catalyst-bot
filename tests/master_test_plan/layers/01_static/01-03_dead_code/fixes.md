# Fixes — Slice 01-03

---

## Fix (this commit): dead code sweep — params, F841, vulture whitelist

**Addresses:** F1, F2, F3 · **Files touched:** `coin_manager.py`, `bot_loop.py`,
`api_server.py`, `boost_manager.py`, `coin_prep_worker.py`, `database.py`,
`doctor.py`, `splash_manager.py`, `wallet_sage.py`, `vulture_whitelist.py`,
`tests/test_plan_01_03_dead_code.py`

### Change summary
Removed two dead method parameters (`cat_token_amount` in `_smart_topup_wallet` and
`zombie_buy_count`/`zombie_sell_count` in `_create_offers_if_needed`), along with all
18 F841 unused-local-variable assignments flagged by ruff. Created `vulture_whitelist.py`
to document intentionally-kept-but-unused names (PyWebView API, Flask routes,
`CycleBudget`).

### Regression coverage
- `TestSmartTopupWalletDeadParam` (3 tests) — signature, caller kwargs, dead computation
- `TestCreateOffersIfNeededDeadParams` (3 tests) — signature, caller kwargs
- `TestF841DeadVariablesRemoved` (8 tests) — spot-checks removed dead assignments
- `TestModulesImportClean` (5 tests) — key modules import without NameError

### Verified no regressions in
```
pytest -q
```
Result: 540 passed, 0 failed (+19 new tests, was 521)

---

## Lessons / gotchas

- Removing a dead variable block can cascade: `buy_price`/`sell_price` were dead, but
  `proven_spread_bps = self._arb_floor_bps` in the same block was live. Remove only the
  dead assignments, not the entire containing block.
- Vulture at 80% confidence is a tight filter: 3 hits vs 370 at 60%. The 370-item 60%
  run is dominated by PyWebView bridge methods and Flask routes (both framework-called,
  not Python-called). Always filter those before triaging.
- `cat_token_amount` was a parameter that callers pass but the method never read — a
  "dead on arrival" parameter. The computation at call sites was also dead as a result.
