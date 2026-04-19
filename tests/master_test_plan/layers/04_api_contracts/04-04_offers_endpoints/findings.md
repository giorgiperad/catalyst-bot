# Findings — Slice 04-04

API contract tests for offers endpoints.

## New coverage added

| Test class | Tests | Notes |
|------------|-------|-------|
| `TestOffersGet` | 4 | bot=None→500, 200 with bot, buys/sells/counts keys, zero counts |
| `TestCancelAllStatus` | 2 | always 200, success key |
| `TestOpenOfferCount` | 3 | 200, open_count integer, success=True |
| `TestCancelOffer` | 8 | 401, 500 no-bot, 400 bad-body (needs bot mock), 400 missing/empty trade_id, 200 success, trade_id echoed, 400 on error result |
| `TestCancelAllPost` | 4 | 401, bot=None→direct wallet→200, running bot→409, stopped bot→200 |

**21 new tests** in `tests/test_plan_04_04_offers_endpoints.py`.

## Fixes required (test-side)

1. **`test_invalid_body_returns_400`**: must patch bot to avoid the `if not bot: return 500` guard before the JSON check fires.
2. **`test_bot_none_returns_error` (renamed `test_bot_none_uses_direct_wallet_path`)**: bot=None does NOT return an error — the handler takes the direct wallet RPC path. Must mock `wallet.get_all_offers`, `wallet.cancel_offers_batch`, `wallet.is_offer_time_expired` to avoid hitting the live wallet. With empty offer list returns 200.
3. **`test_bot_running_cancel_all_returns_response` (replaced)**: a running bot returns **409** ("Stop the bot before cancelling all offers"), not 200/202. Added separate `test_bot_stopped_cancel_all_returns_success` for the 200 path.

## No production bugs found
