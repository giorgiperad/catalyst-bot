# SAGE V4 Mismatch Report

This document records only confirmed mismatches, high-confidence issues, and missing edge case handling in this project's Sage integration.

## Confirmed Mismatches

### 1. Sage `initialize` lifecycle is not implemented
- Affected files/functions:
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
  - [chia_node.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\chia_node.py) `_log_in_fingerprint()`
- Documentation basis:
  - `sage_docs/SAGE_AUDIT_CHECKLIST.md` requires calling `initialize` before wallet/data/transaction operations and handling failure explicitly.
- Actual behavior:
  - No project call site invokes `initialize`, `start_rpc_server`, or `stop_rpc_server`.
  - Sage startup goes straight to `sage_login()`, which performs `resync` and `login`.
- Why it matters:
  - The project assumes Sage RPC is already fully initialized and ready.
  - Documented initialization failure and startup ordering cases are not handled at all.

### 2. `get_pending_transactions()` does not use the documented Sage endpoint
- Affected files/functions:
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py) `get_pending_transactions()`
- Documentation basis:
  - `sage_docs/SAGE_COMPLETE_REFERENCE.md` documents `get_pending_transactions` as the endpoint for unconfirmed transactions.
- Actual behavior:
  - An earlier implementation calls `rpc("get_pending_transactions", {}, ...)`.
  - A later duplicate definition overrides it and instead calls `rpc("get_transactions", ...)` and filters statuses heuristically.
- Why it matters:
  - The live implementation no longer follows the documented API contract.
  - Pending transaction detection is now based on inferred status semantics rather than the dedicated Sage endpoint.

### 3. `get_spendable_coin_count()` does not use the documented Sage endpoint
- Affected files/functions:
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py) `get_spendable_coin_count()`
- Documentation basis:
  - `sage_docs/SAGE_COMPLETE_REFERENCE.md` documents `get_spendable_coin_count(asset_id) -> { count }`.
- Actual behavior:
  - An earlier implementation calls `rpc("get_spendable_coin_count", ...)`.
  - A later duplicate definition overrides it and uses `get_coins(filter_mode="selectable")` plus `total_count` or list length.
- Why it matters:
  - The active implementation replaced a documented endpoint with a derived approximation.
  - Coin count semantics can drift if Sage changes `get_coins` shape or filtering behavior.

### 4. `create_offer()` ignores `validate_only`
- Affected files/functions:
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py) `create_offer()`
- Documentation basis:
  - `sage_docs/SAGE_AUDIT_CHECKLIST.md` requires callers to distinguish construction, signing, and submission behavior.
- Actual behavior:
  - `create_offer()` accepts `validate_only=True` but always calls `rpc("make_offer", payload, ...)`.
  - It always sets `auto_import=True`.
  - It never branches on `validate_only`.
- Why it matters:
  - The wrapper exposes a parameter that is never honored.
  - Callers cannot rely on the adapter to preserve “validate-only” behavior.

### 5. Sync/readiness logic invents undocumented `synced=None` behavior
- Affected files/functions:
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py) `get_wallet_sync_status()`
- Documentation basis:
  - `sage_docs/SAGE_COMPLETE_REFERENCE.md` documents `get_sync_status` with `synced: true|false`.
- Actual behavior:
  - The adapter treats `synced is None` as effectively synced if:
    - `synced_coins >= total_coins`, or
    - both counts are zero.
- Why it matters:
  - Readiness is being inferred from undocumented heuristics.
  - A wallet can be treated as ready without an explicit documented synced signal.

## High-Confidence Issues

### 6. `cancel_offer()` treats undocumented error cases as success
- Affected files/functions:
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py) `cancel_offer()`
- Documentation basis:
  - `sage_docs/SAGE_COMPLETE_REFERENCE.md` supports treating `404` missing offer as success.
- Actual behavior:
  - The adapter also treats `HTTP 500` and `HTTP 202` as success with `"uncertain": True`.
- Why it matters:
  - The docs do not support promoting generic server errors into a success path.
  - This can cause false-positive cancel success and hidden state drift.

### 7. Exact `offer_id`-based reconciliation is available but not consistently used
- Affected files/functions:
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
    - `get_owned_coins()`
    - `get_owned_coins_detailed()`
    - `get_selectable_coins_map()`
    - comments and helper logic around spendable/owned workarounds
- Documentation basis:
  - `sage_docs/SAGE_COMPLETE_REFERENCE.md` marks `offer_id` on `owned` coins as the exact source of lock attribution and recommends using `get_owned_coins_detailed()`.
- Actual behavior:
  - The adapter implements `get_owned_coins_detailed()`.
  - It still keeps and documents older `owned - selectable` and coin-count workaround logic in active paths.
- Why it matters:
  - Sage already exposes exact lock attribution.
  - Continuing to rely on heuristics increases reconciliation drift risk.

### 8. Session lifecycle is compressed into `resync + login`
- Affected files/functions:
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py) `sage_login()`
  - [chia_node.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\chia_node.py) `_log_in_fingerprint()`
- Documentation basis:
  - `sage_docs/SAGE_AUDIT_CHECKLIST.md` separates initialization, login, active-fingerprint tracking, and startup-sensitive serialization.
- Actual behavior:
  - `sage_login()` performs `resync(fingerprint)` then `login(fingerprint)` and treats that as sufficient wallet startup.
- Why it matters:
  - Documented lifecycle concerns are compressed into one optimistic login path.
  - Init failure, reset, and session-state edge cases remain uncovered.

## Missing Edge Case Handling

### 9. Watch-only wallets are not blocked from signing flows
- Affected files/functions:
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
    - `get_sage_keys()`
    - `send_transaction()`
    - `send_transaction_multi()`
    - `create_offer()`
    - `cancel_offer()`
    - split/combine helpers
- Documentation basis:
  - `sage_docs/SAGE_EDGE_CASES.md` says watch-only wallets can be imported and queried but fail signing flows with `NoSigningKey`.
  - `sage_docs/SAGE_AUDIT_CHECKLIST.md` says callers should block signing flows for wallets without secrets.
- Actual behavior:
  - `get_sage_keys()` exposes `has_secrets`.
  - No matching preflight guard was found before signing operations.
- Why it matters:
  - The integration has the metadata needed to block these flows but does not enforce it.
  - Signing failures will happen later and less predictably than necessary.

### 10. Request-only offer fee rule is not enforced
- Affected files/functions:
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py) `create_offer()`
- Documentation basis:
  - `sage_docs/SAGE_EDGE_CASES.md` says request-only offers are allowed only with a fee.
  - `sage_docs/SAGE_AUDIT_CHECKLIST.md` explicitly requires handling this rule.
- Actual behavior:
  - `create_offer()` hardcodes `"fee": "0"`.
  - It does not detect or reject request-only offers.
- Why it matters:
  - The wrapper has no compliant handling for a documented Sage edge case.
  - Callers can construct a request-only offer path that Sage will reject.

### 11. Send paths do not validate address/network correctness in the adapter
- Affected files/functions:
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)
    - `send_transaction()`
    - `send_transaction_multi()`
    - `send_cat_multi()`
- Documentation basis:
  - `sage_docs/SAGE_AUDIT_CHECKLIST.md` says callers should validate network names against `get_networks` and not rely solely on `check_address`.
  - `sage_docs/SAGE_EDGE_CASES.md` says `check_address` is only a partial validator.
- Actual behavior:
  - The adapter passes destination addresses directly through to Sage.
  - No adapter-side network-prefix validation was found.
- Why it matters:
  - Documented caller responsibilities are not implemented.
  - Wrong-network addresses can reach signing/submission code paths.

### 12. Initialization failure and retry edge cases are completely unhandled
- Affected files/functions:
  - [chia_node.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\chia_node.py) `_log_in_fingerprint()`
  - [wallet_sage.py](C:\Users\t_you\Pictures\01 Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py) `sage_login()`
- Documentation basis:
  - `sage_docs/SAGE_EDGE_CASES.md` says failed first init may block later retries and startup-sensitive operations should be serialized.
- Actual behavior:
  - Because the integration never calls `initialize`, it has no explicit handling for init failure, reset policy, or retry policy.
- Why it matters:
  - One of the main documented Sage lifecycle edge cases is outside the control of the integration.
  - Recovery behavior is undefined.
