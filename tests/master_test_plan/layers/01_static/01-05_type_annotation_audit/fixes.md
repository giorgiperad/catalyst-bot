# Fixes — Slice 01-05

---

## Fix (this commit): wallet missing export + database missing return

**Addresses:** F1, F2 · **Files touched:** `wallet.py`, `wallet_chia.py`,
`database.py`, `tests/test_plan_01_05_type_audit.py`

### Change summary
- `wallet_chia.py`: added `get_spendable_coin_count(wallet_id) -> int` that
  counts `confirmed_records` from `get_spendable_coins_rpc()`.
- `wallet.py`: added `get_spendable_coin_count` to both the Chia and Sage
  import branches so `from wallet import get_spendable_coin_count` works
  regardless of `WALLET_TYPE`.
- `database.py`: added `return False  # all retries exhausted` after
  `update_offer_status`'s for loop to satisfy mypy's missing-return check.

### Regression coverage
- `TestWalletExportsGetSpendableCoinCount` (6 tests) — export present in all
  modules, mock-based count verification
- `TestDatabaseUpdateOfferStatusAlwaysReturns` (2 tests) — source check +
  graceful return for unknown trade_id

### Verified no regressions in
```
pytest -q
```
Result: 548 passed, 0 failed (+8 new tests, was 540)

---

## Lessons / gotchas

- mypy `--ignore-missing-imports` on just 6 modules still pulls in transitive
  imports — use `grep "^filename.py"` to filter to the target files.
- 65 of 110 errors are `[assignment]`: `None` default for `str` parameters
  (should be `Optional[str]`). Not bugs, just annotation style — worth a
  dedicated annotation-fixup slice.
- `cursor.lastrowid` is `int | None` in mypy's view even when an INSERT just
  ran. `int(cursor.lastrowid)` will raise if lastrowid is None — callers that
  rely on this should guard or use `cursor.lastrowid or 0`.
