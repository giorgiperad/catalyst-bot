# SAGE V4 Patch Checklist

This checklist is implementation-oriented. Every item below maps to a confirmed mismatch, high-confidence issue, or missing documented edge case.

## 1. Implement Sage initialization lifecycle
- Priority: P0
- File: [chia_node.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\chia_node.py), [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
- Function:
  - `_log_in_fingerprint()`
  - `sage_login()`
- Exact change needed:
  - Add an explicit Sage initialization step before wallet-bound operations.
  - Handle initialization failure distinctly from login failure.
  - Do not treat `resync + login` as a replacement for initialization.
- Expected behavior after fix:
  - Sage startup has a defined order: initialize, then login/session work.
  - Failures surface as initialization errors instead of generic login failures.
- Regression risk:
  - Medium. Startup timing and wallet-ready behavior may change.
- Tests required:
  - startup test where initialization succeeds
  - startup test where initialization fails
  - test that login is not attempted before init success

## 2. Restore documented `get_pending_transactions` behavior
- Priority: P0
- File: [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
- Function: `get_pending_transactions()`
- Exact change needed:
  - Remove the duplicate override.
  - Keep a single implementation that uses Sage `get_pending_transactions`.
- Expected behavior after fix:
  - Pending transaction queries use the documented unconfirmed-transactions endpoint.
- Regression risk:
  - Low to medium. Some callers may currently rely on the heuristic fields from `get_transactions`.
- Tests required:
  - unit test for response parsing from `get_pending_transactions`
  - regression test that duplicate definitions do not exist

## 3. Restore documented `get_spendable_coin_count` behavior
- Priority: P0
- File: [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
- Function: `get_spendable_coin_count()`
- Exact change needed:
  - Remove the duplicate override.
  - Keep a single implementation that calls Sage `get_spendable_coin_count(asset_id)`.
- Expected behavior after fix:
  - Spendable coin count comes from the documented count endpoint, not from derived `get_coins` behavior.
- Regression risk:
  - Low.
- Tests required:
  - unit test for XCH count path
  - unit test for CAT count path
  - regression test that duplicate definitions do not exist

## 4. Make `create_offer(validate_only=...)` behave correctly
- Priority: P0
- File: [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
- Function: `create_offer()`
- Exact change needed:
  - Either implement a real non-submitting path for `validate_only`, or reject unsupported validate-only calls explicitly.
  - Do not silently ignore the parameter.
- Expected behavior after fix:
  - Callers get behavior that matches the function signature.
  - The wrapper no longer implies support for a mode it does not provide.
- Regression risk:
  - Medium. Existing call sites may depend on the current misleading behavior.
- Tests required:
  - test for `validate_only=True`
  - test for `validate_only=False`
  - test that response shape remains compatible with current offer-manager expectations

## 5. Enforce Sage request-only offer fee rule
- Priority: P0
- File: [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
- Function: `create_offer()`
- Exact change needed:
  - Detect request-only offers.
  - Reject fee-free request-only offers or require a nonzero fee before calling Sage.
- Expected behavior after fix:
  - The wrapper blocks or handles request-only offers in a way consistent with Sage documentation.
- Regression risk:
  - Low.
- Tests required:
  - request-only offer with zero fee should fail fast
  - request-only offer with fee should proceed
  - normal two-sided offer should keep working

## 6. Stop inferring sync readiness from undocumented `synced=None` heuristics
- Priority: P1
- File: [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
- Function: `get_wallet_sync_status()`
- Exact change needed:
  - Remove undocumented promotion of `synced is None` to ready/synced.
  - Distinguish “reachable but sync state unknown” from “synced”.
- Expected behavior after fix:
  - Sync status reflects documented Sage signals.
  - Unknown sync state is not reported as ready by default.
- Regression risk:
  - Medium. Startup/health UI may appear less optimistic.
- Tests required:
  - `synced=True`
  - `synced=False`
  - `synced=None`
  - empty/partial sync payload

## 7. Restrict `cancel_offer()` success cases to documented behavior
- Priority: P1
- File: [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
- Function: `cancel_offer()`
- Exact change needed:
  - Keep `404/missing offer` as success if desired.
  - Stop treating generic `HTTP 500` and `HTTP 202` as successful cancel outcomes.
- Expected behavior after fix:
  - Cancel success reflects documented cases only.
  - Uncertain or failed server responses remain non-successful until verified elsewhere.
- Regression risk:
  - Medium. Existing polling/retry flow may need to handle more explicit uncertainty.
- Tests required:
  - `404` missing offer path
  - `500` path
  - `202` path
  - normal success path

## 8. Prefer exact `offer_id`-based coin reconciliation
- Priority: P1
- File: [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
- Function:
  - `get_owned_coins_detailed()`
  - `get_owned_coins()`
  - `get_selectable_coins_map()`
  - any caller still using `owned - selectable` as primary lock attribution
- Exact change needed:
  - Where Sage lock attribution is needed, use `owned` coins with `offer_id` as the primary source.
  - Do not use coin-count or subtraction heuristics as the main source when exact `offer_id` data is already available.
- Expected behavior after fix:
  - Locked coin attribution is based on Sage’s exact offer linkage.
- Regression risk:
  - Medium. Reconciliation behavior may surface previously hidden drift.
- Tests required:
  - owned coin with `offer_id=null`
  - owned coin with `offer_id` set
  - reconciliation path with mixed free and locked coins

## 9. Block watch-only wallets from signing flows
- Priority: P1
- File: [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py), [chia_node.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\chia_node.py)
- Function:
  - `get_sage_keys()`
  - `sage_login()`
  - `send_transaction()`
  - `send_transaction_multi()`
  - `create_offer()`
  - `cancel_offer()`
- Exact change needed:
  - Track whether the active Sage key has `has_secrets`.
  - Refuse signing/submission operations for keys without secrets.
- Expected behavior after fix:
  - Watch-only wallets remain queryable but cannot enter signing paths.
- Regression risk:
  - Medium if current environments use watch-only keys unexpectedly.
- Tests required:
  - login to hot wallet
  - login to watch-only wallet
  - signing operation under watch-only wallet must fail fast with explicit reason

## 10. Validate addresses against intended network before send
- Priority: P1
- File: [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
- Function:
  - `send_transaction()`
  - `send_transaction_multi()`
  - `send_cat_multi()`
- Exact change needed:
  - Add adapter-side address/network validation before calling Sage.
  - Do not pass destination addresses straight through without network checks.
- Expected behavior after fix:
  - Wrong-network or malformed addresses are rejected before signing/submission.
- Regression risk:
  - Low to medium. Some loosely validated inputs may now fail earlier.
- Tests required:
  - valid mainnet/testnet-style address for configured network
  - wrong-network prefix
  - malformed address

## 11. Add explicit init failure/retry handling
- Priority: P1
- File: [chia_node.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\chia_node.py), [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
- Function:
  - `_log_in_fingerprint()`
  - `sage_login()`
  - new init wrapper if added
- Exact change needed:
  - Represent initialization failure as its own state.
  - Add deterministic retry/reset behavior instead of folding all startup failures into login.
- Expected behavior after fix:
  - Recovery from startup problems is explicit and testable.
- Regression risk:
  - Medium.
- Tests required:
  - failed first init
  - retry after init failure
  - login after successful retry
