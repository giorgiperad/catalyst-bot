# AGENTS

## Sage Review And Editing Rules

When reviewing or editing Sage-related code, you must apply the review rules in [sage_docs/SAGE_V4_REVIEW_RULES.md](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_V4_REVIEW_RULES.md).

Treat these checks as mandatory:

- Verify lifecycle against Sage requirements.
  - Confirm Sage initialization is handled explicitly before wallet-bound operations.
  - Do not treat `resync + login` as a substitute for documented Sage initialization.
  - Distinguish initialization failure from login/session failure.

- Verify signing operations are blocked for wallets without secrets.
  - Treat watch-only wallets as queryable but non-signing.
  - Before send, offer, split, combine, or cancel flows, verify the active Sage wallet has secrets.

- Verify `create_offer` behavior matches Sage expectations.
  - Do not silently ignore `validate_only` or other dry-run style parameters.
  - Enforce documented request-only offer rules, including the required fee.
  - Keep offer creation, import, view, take, and cancel behavior distinct.

- Verify sync/readiness logic does not invent undocumented semantics.
  - Use documented Sage sync/readiness signals as the source of truth.
  - Do not promote undocumented states such as `synced=None` into ready/synced unless explicitly documented and supported.

- Verify pending transaction and spendable coin logic uses documented Sage endpoints where available.
  - Use `get_pending_transactions` for pending transaction tracking.
  - Use `get_spendable_coin_count` for spendable coin counts.
  - Do not replace documented Sage endpoints with derived approximations unless the API contract requires it.

- Verify send paths perform caller-side network/address validation.
  - Validate destination addresses against the intended network before calling Sage.
  - Do not rely on Sage-side parsing or `check_address` alone for network correctness.

## Scope

Apply these rules to Sage-related changes in at least these files when relevant:

- [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- [chia_node.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py)
- [wallet.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet.py)
- any Sage-specific tests
- any API or orchestration code that changes Sage startup, login, offer creation, sending, sync handling, or coin-state reconciliation
