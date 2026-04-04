# SAGE_EXECUTIVE_SUMMARY

## Top 5 Sage integration problems

1. The project does not implement the documented Sage initialization lifecycle.
   - [chia_node.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py) and [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) currently treat `resync + login` as the effective startup path, with no explicit `initialize` handling.

2. Two documented Sage adapter helpers are shadowed by duplicate definitions that use heuristics instead of the documented endpoints.
   - In [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py), the live `get_pending_transactions()` uses `get_transactions` heuristics instead of `get_pending_transactions`, and the live `get_spendable_coin_count()` uses `get_coins` instead of `get_spendable_coin_count`.

3. `create_offer()` does not match its public contract or documented Sage expectations.
   - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) `create_offer()` ignores `validate_only` and does not enforce the documented request-only-offers-require-a-fee rule.

4. Signing safety is incomplete.
   - The adapter exposes `has_secrets` for Sage keys but does not appear to block signing operations for watch-only wallets before send, offer, cancel, split, or combine flows.

5. Readiness and cancel semantics include undocumented assumptions.
   - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) `get_wallet_sync_status()` invents `synced=None` readiness logic, and `cancel_offer()` treats undocumented `500` and `202` responses as probable success.

## Safest first implementation batch

Batch 2: Pending and spendable endpoint corrections

Why this is the safest first batch:
- it is limited to [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- it only touches two helper functions and their duplicate shadowing definitions
- repository search confirmed:
  - `get_pending_transactions()` callers do not pass `wallet_id`
  - callers only depend on “returns a list, empty means no pending transactions”
  - `get_spendable_coin_count()` has no external call sites outside its definitions

## Highest-risk batch

Batch 8: Offer-lock reconciliation correctness

Why it is highest risk:
- it changes how lock attribution is derived for Sage coins
- it may affect downstream caller assumptions about free vs locked coins
- it should use exact `offer_id` data from Sage, but that can expose latent drift or hidden dependencies in current reconciliation flows

## Top testing priorities

1. Add unit tests for `get_pending_transactions()` and `get_spendable_coin_count()` before patching them.
   - These should verify endpoint usage, fallback behavior, and duplicate-definition regression.

2. Add tests for `create_offer()` contract behavior.
   - Cover `validate_only`
   - cover request-only zero-fee rejection
   - preserve current response-shape compatibility

3. Add watch-only signing guard tests.
   - hot wallet allowed
   - watch-only wallet blocked from signing
   - query-only behavior still works

4. Add readiness semantic tests for `get_wallet_sync_status()`.
   - `synced=True`
   - `synced=False`
   - `synced=None`
   - partial or missing payloads

5. Add cancel normalization tests for `cancel_offer()`.
   - explicit success
   - `404` missing offer
   - `500`
   - `202`

## Top things Claude must not accidentally break

1. Public adapter shape in [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py), unless clearly wrong.
   - Keep return types and public entry points stable where possible.

2. Caller compatibility for existing Sage helper usage.
   - Especially `get_pending_transactions()` returning a list where empty means “no pending transactions.”

3. Normal hot-wallet trading flows.
   - Offer creation, sending, and cancellation must still work for wallets with secrets.

4. Existing non-Sage wallet behavior.
   - Do not let Sage fixes spill into unrelated wallet backends.

5. Response normalization relied on by the rest of the bot.
   - Particularly for offer creation, cancel behavior, and coin-state helpers.

6. Avoid inventing new Sage semantics.
   - Use documented Sage endpoints and documented caller-side rules where available.
