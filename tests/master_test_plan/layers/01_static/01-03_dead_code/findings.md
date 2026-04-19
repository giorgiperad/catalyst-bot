# Findings — Slice 01-03

Vulture baseline (80% confidence): 3 items, all confirmed real.
F841 dead-variable triage: 18 items, all confirmed dead.
Dead parameters: 2 independent instances.

---

## Finding F1: `cat_token_amount` — dead parameter in `_smart_topup_wallet`

**Check:** 1.1 / 2.1 · **Severity:** medium · **Status:** fixed

`coin_manager.CoinManager._smart_topup_wallet` accepted `cat_token_amount: int = None`.
Callers at lines ~4340 and ~4406 passed `cat_token_amount=cat_token_size`. The parameter
was never read in the method body (verified by reading lines 4635–4931). Removing it also
exposed that the `cat_token_size` computation blocks at both call sites were dead —
they existed solely to compute the now-removed argument.

### Resolution
- Fix committed: (this slice commit)
- Regression: `tests/test_plan_01_03_dead_code.py::TestSmartTopupWalletDeadParam`
- No regressions in `pytest -q`

---

## Finding F2: `zombie_buy_count` / `zombie_sell_count` — dead params in `_create_offers_if_needed`

**Check:** 1.1 / 2.1 · **Severity:** low · **Status:** fixed

`bot_loop.BotLoop._create_offers_if_needed` had two trailing params
`zombie_buy_count: int = 0` and `zombie_sell_count: int = 0`. Caller passed live values.
A comment mentioned zombies but used `effective_buy_count` (computed from wallet IDs).
The parameters were dead since the zombie-count logic was replaced by `effective_*_count`.

### Resolution
- Fix committed: (this slice commit)
- Regression: `tests/test_plan_01_03_dead_code.py::TestCreateOffersIfNeededDeadParams`

---

## Finding F3: 18 × F841 dead local variable assignments

**Check:** 3.1 · **Severity:** low · **Status:** fixed

All 18 non-auto-fixable F841 items from the 01-01 spawn queue resolved:

| File | Name | Disposition |
|------|------|-------------|
| `api_server.py:525` | `activities` | dead — `activity` (line 512) was the used var |
| `api_server.py:2369` | `risk_data` | dead assignment, value never read |
| `api_server.py:7188-7189` | `max_buy`, `max_sell` | read from request args but unused; function uses `_smart_max_*` |
| `boost_manager.py:353` | `target_price` | dead — `buy_price`/`sell_price` that fed it were also dead |
| `boost_manager.py:558` | `created` | side-effect call; changed to bare `self._create_gap_closer_pair(...)` |
| `coin_manager.py:2921` | `new_count` | initialised, loop ran, never incremented or read |
| `coin_manager.py:2973` | `reappeared_count` | comment said "counted by database.py"; dead |
| `coin_manager.py:4150-4155` | `spare_keep_pct` block | pace-based pct block; downstream used `_topup_tier_pct()` instead |
| `coin_manager.py:4193` | `cat_scale_dec` | assigned, never referenced |
| `coin_manager.py:6205-6208` | `spent_ids` | stub "compare Sage coin selection"; never completed |
| `coin_prep_worker.py:1558,1575` | `in_wallet_section` | set and reset but never read in loop |
| `database.py:2336-2341` | `requested_xch`, `requested_cat` | parsed from offer summary but only `offered_*` was used |
| `database.py:2902` | `existing_size_xch` | fetched but comparison only used `side`/`price` |
| `doctor.py:54` | `skips` | counted but never included in report string |
| `splash_manager.py:306` | `r` | HTTP GET return value ignored; changed to bare call |
| `wallet_sage.py:3118,3169` | `last_count` | pre/post polling counts; loop checked deltas inline |

### Resolution
- Fix committed: (this slice commit)
- Regression: `tests/test_plan_01_03_dead_code.py::TestF841DeadVariablesRemoved`

---

## Closed findings tallied here

| Count | Status |
|-------|--------|
| 0 | open |
| 3 | fixed |
| 0 | blocked |
