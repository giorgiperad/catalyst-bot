# Fixes — Slice 04-04

No production bugs found. Three test-side corrections:

1. Added bot mock to `test_invalid_body_returns_400` — route checks `if not bot` before parsing body.
2. `test_bot_none_returns_error` → `test_bot_none_uses_direct_wallet_path` — bot=None routes to direct wallet RPC (not an error). Mock wallet functions to prevent live Sage calls.
3. `test_bot_running_cancel_all_returns_response` replaced with `test_bot_running_returns_409` + `test_bot_stopped_cancel_all_returns_success` — running bot returns 409 by design.
