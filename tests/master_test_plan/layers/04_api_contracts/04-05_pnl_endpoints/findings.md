# Findings — Slice 04-05

API contract tests for PnL and fills/purge endpoints.

## New coverage added

| Test class | Tests | Notes |
|------------|-------|-------|
| `TestPnlGet` | 5 | bot=None→500, 200 with bot, required keys, fill counts, sniper key |
| `TestPnlResetPreview` | 5 | 200, success key, required keys, integer types, has_data=False on empty |
| `TestPnlReset` | 6 | 401, 400 missing/wrong confirm, case-insensitive accept, 200 success, message key |
| `TestFillsPurge` | 5 | 401, 200 success, purge count keys, risk_manager.reset_position called, bot=None path |

**21 new tests** in `tests/test_plan_04_05_pnl_endpoints.py`.

## Fix required (test-side)

`test_lowercase_reset_not_accepted` → `test_confirm_case_insensitive`: the `api_pnl_reset` handler applies `.strip().upper()` before comparing to "RESET", so lowercase "reset" IS accepted and returns 200. Test updated to assert 200.

## No production bugs found
