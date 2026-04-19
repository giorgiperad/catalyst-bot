# Findings — Slice 01-05

mypy 1.20.1, `--ignore-missing-imports`, on 6 core modules:
config.py, database.py, wallet.py, fill_tracker.py, risk_manager.py, price_engine.py

Total in target files: 110 errors (65 [assignment], 17 [arg-type], 8 [operator],
8 [index], 4 [return-value], 3 [var-annotated], 1 each: [truthy-function],
[return], [misc], [import-untyped], [call-overload])

2 real bugs found and fixed. Remainder are annotation gaps logged in spawn_queue.

---

## Finding F1: `wallet.py` missing `get_spendable_coin_count` export

**Check:** 1.3 (attr-defined) · **Severity:** medium · **Status:** fixed

`api_server.py` does `from wallet import get_spendable_coin_count` at lines 2065 and
2303. `wallet.py` re-exported neither from `wallet_sage` nor `wallet_chia`. In the Sage
branch the function exists (`wallet_sage.py:1199`) but wasn't in the import list.
In the Chia branch the function didn't exist at all.

At runtime this was a silent `ImportError` swallowed by a broad `except Exception: pass`
at api_server.py:2077. Result: coin counts silently showed as 0 in the dashboard
fallback path.

### Resolution
- Added `get_spendable_coin_count` to both branches of wallet.py
- Added `get_spendable_coin_count(wallet_id) -> int` to wallet_chia.py using
  `get_spendable_coins_rpc` + `len(confirmed_records)`
- Fix committed: (this slice commit)
- Regression: `tests/test_plan_01_05_type_audit.py::TestWalletExportsGetSpendableCoinCount`

---

## Finding F2: `database.update_offer_status` — missing return after for loop

**Check:** 1.3 ([return]) · **Severity:** low · **Status:** fixed

mypy reported `Missing return statement [return]` on the function declaration at line 1070.
The for loop `for _attempt in range(3):` always exits via `return True`, `return False`,
or `continue` (never completes normally), but mypy can't prove this. Added `return False`
after the loop as a defensive fallback and to satisfy the type checker.

### Resolution
- Added `return False  # all retries exhausted` after the for loop
- Fix committed: (this slice commit)
- Regression: `tests/test_plan_01_05_type_audit.py::TestDatabaseUpdateOfferStatusAlwaysReturns`

---

## Closed findings tallied here

| Count | Status |
|-------|--------|
| 0 | open |
| 2 | fixed |
| ~108 | annotation gaps (see spawn_queue) |
| 0 | blocked |
