# SAGE_MASTER_HANDOFF_FOR_CLAUDE

## 1. Purpose of this handoff

This document is a complete, implementation-ready handoff for another coding assistant working on this repository's Sage integration.

It is based only on repository-local Sage research, local Sage documentation under `/sage_docs`, direct code inspection, and Sage-specific audit and planning artifacts created in this repository.

Its purpose is to:
- summarize how Sage is used here
- record only confirmed mismatches, high-confidence issues, and missing documented edge-case handling
- break the work into small safe batches
- define patch guidance, tests, acceptance criteria, and constraints for each batch

## 2. Source documents used

- [sage_docs/SAGE_API_REFERENCE.md](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_API_REFERENCE.md)
  - Endpoint names and baseline API surface.

- [sage_docs/SAGE_COMPLETE_REFERENCE.md](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_COMPLETE_REFERENCE.md)
  - Detailed endpoint behavior, coin semantics, offer semantics, and adapter mappings.

- [sage_docs/SAGE_EDGE_CASES.md](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_EDGE_CASES.md)
  - Documented edge cases, weak handling areas, and caller-side defensive expectations.

- [sage_docs/SAGE_AUDIT_CHECKLIST.md](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_AUDIT_CHECKLIST.md)
  - Review expectations for lifecycle, session state, validation, transaction semantics, and error handling.

- [sage_docs/SAGE_V4_MISMATCH_REPORT.md](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_V4_MISMATCH_REPORT.md)
  - Repository-specific list of confirmed mismatches, high-confidence issues, and missing edge cases.

- [sage_docs/SAGE_V4_PATCH_CHECKLIST.md](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_V4_PATCH_CHECKLIST.md)
  - Patch-ready implementation items with priority, scope, risk, and test guidance.

- [sage_docs/SAGE_V4_ACCEPTANCE_CRITERIA.md](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_V4_ACCEPTANCE_CRITERIA.md)
  - Post-fix truth conditions, non-regression constraints, and verification steps.

- [sage_docs/SAGE_V4_REVIEW_RULES.md](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_V4_REVIEW_RULES.md)
  - Reusable rules for lifecycle, signing safety, offer creation, readiness, validation, and coin-state handling.

- [AGENTS.md](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/AGENTS.md)
  - Standing repository instructions that require those Sage review rules to be applied when editing or reviewing Sage-related code.

## 3. Sage integration overview in this project

### How this project uses Sage

This project uses Sage as a local wallet backend for:
- key and fingerprint enumeration
- wallet login and active-key selection
- wallet readiness checks
- address retrieval
- sending XCH and CAT transactions
- offer creation and cancellation
- coin queries and reconciliation
- split and combine operations
- pending transaction polling during coin prep flows

### Key files involved

- [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
  - primary Sage adapter

- [wallet.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet.py)
  - backend selector

- [chia_node.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py)
  - startup and login orchestration

- [coin_prep_worker.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/coin_prep_worker.py)
  - pending transaction polling and coin-prep sequencing

- [test_coin_prep.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/test_coin_prep.py)
- [test_hidden_coins.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/test_hidden_coins.py)
  - manual/integration-style Sage helper usage

### Important call paths

- Startup/login:
  - [chia_node.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py) `_log_in_fingerprint()`
  - calls [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) `sage_login()`

- Offer creation:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) `create_offer()`

- Offer cancellation:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) `cancel_offer()`

- Pending transaction polling:
  - [coin_prep_worker.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/coin_prep_worker.py)
  - [test_coin_prep.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/test_coin_prep.py)
  - [test_hidden_coins.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/test_hidden_coins.py)

### Current integration assumptions

- Sage is effectively ready without an explicit `initialize` call.
- `resync + login` is treated as the effective Sage lifecycle.
- some response semantics are inferred heuristically instead of using documented endpoints
- `create_offer()` exposes `validate_only` but does not honor it
- readiness is inferred when `synced` is not explicit
- watch-only wallet metadata exists but is not enforced as a signing guard

## 4. Confirmed mismatches

### 4.1 Missing explicit Sage initialization lifecycle
- Title: Missing explicit Sage initialization lifecycle
- Severity/priority: High / P0
- Exact file:
  - [chia_node.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py)
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Exact function:
  - `_log_in_fingerprint()`
  - `sage_login()`
- What the code currently does:
  - `_log_in_fingerprint()` calls `sage_login()`
  - `sage_login()` does `resync(fingerprint)` then `login(fingerprint)` and verifies the active key
- What Sage documentation says it should do:
  - explicitly handle `initialize` before wallet/data/transaction operations
- Why it matters:
  - startup ordering and init failure are not controlled by the integration

### 4.2 Shadowed pending transaction helper uses `get_transactions` heuristics
- Title: Live `get_pending_transactions()` does not use documented endpoint
- Severity/priority: High / P0
- Exact file:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Exact function:
  - `get_pending_transactions()`
- What the code currently does:
  - earlier definition uses `rpc("get_pending_transactions", {}, ...)`
  - later duplicate definition shadows it and uses `rpc("get_transactions", ...)` plus status/error heuristics
- What Sage documentation says it should do:
  - use `get_pending_transactions` for unconfirmed transaction tracking
- Why it matters:
  - the active implementation is no longer using the documented endpoint

### 4.3 Shadowed spendable coin count helper uses `get_coins` approximation
- Title: Live `get_spendable_coin_count()` does not use documented endpoint
- Severity/priority: High / P0
- Exact file:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Exact function:
  - `get_spendable_coin_count()`
- What the code currently does:
  - earlier definition uses `rpc("get_spendable_coin_count", {"asset_id": asset_id}, ...)`
  - later duplicate definition shadows it and uses `get_coins(filter_mode="selectable")`
- What Sage documentation says it should do:
  - use `get_spendable_coin_count(asset_id)`
- Why it matters:
  - the active implementation replaced a documented endpoint with a derived count

### 4.4 `create_offer(validate_only=...)` is not honored
- Title: `create_offer()` ignores `validate_only`
- Severity/priority: High / P0
- Exact file:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Exact function:
  - `create_offer()`
- What the code currently does:
  - accepts `validate_only=True`
  - always sets `auto_import=True`
  - always calls `rpc("make_offer", payload, ...)`
- What Sage documentation says it should do:
  - integrations must distinguish construction, signing, and submission semantics
- Why it matters:
  - the function signature advertises a mode the adapter does not provide

### 4.5 Undocumented sync readiness inference
- Title: `get_wallet_sync_status()` invents `synced=None` semantics
- Severity/priority: Medium / P1
- Exact file:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Exact function:
  - `get_wallet_sync_status()`
- What the code currently does:
  - treats `synced is None` as synced if coin counts line up
  - also treats zero/zero coin counts as synced
- What Sage documentation says it should do:
  - `get_sync_status` is documented with explicit `synced: true|false`
- Why it matters:
  - readiness is being inferred from undocumented adapter heuristics

## 5. High-confidence issues

### 5.1 Undocumented cancel success normalization
- Title: `cancel_offer()` treats `500` and `202` like success
- Priority: P1
- Exact file:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Exact function:
  - `cancel_offer()`
- Why it is likely a real problem:
  - docs support `404 missing offer` as a success case
  - docs do not support generic `500` or `202` being promoted to success
- What needs verification during implementation:
  - whether any caller depends on `"uncertain": True` plus `"success": True`

### 5.2 Heuristic lock attribution remains in active adapter logic
- Title: Exact `offer_id` attribution is available but not consistently used
- Priority: P1
- Exact file:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Exact function:
  - `get_owned_coins()`
  - `get_owned_coins_detailed()`
  - `get_selectable_coins_map()`
  - adjacent heuristic logic
- Why it is likely a real problem:
  - Sage docs identify `offer_id` on owned coins as the exact lock source
  - the adapter already exposes `get_owned_coins_detailed()`
- What needs verification during implementation:
  - which callers still rely on the older heuristic behavior

### 5.3 Session startup handling is narrower than documented lifecycle expectations
- Title: Session lifecycle is compressed into `resync + login`
- Priority: P0
- Exact file:
  - [chia_node.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py)
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Exact function:
  - `_log_in_fingerprint()`
  - `sage_login()`
- Why it is likely a real problem:
  - docs separate initialization, login, active-wallet state, and startup-sensitive serialization
- What needs verification during implementation:
  - whether Sage is implicitly initialized elsewhere outside the adapter

## 6. Missing edge case handling

### 6.1 Watch-only wallets
- Edge case:
  - watch-only wallets can be queried but must not sign
- Affected file/function:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
    - `get_sage_keys()`
    - `send_transaction()`
    - `send_transaction_multi()`
    - `create_offer()`
    - `cancel_offer()`
    - split/combine helpers
  - [chia_node.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py) if active-wallet gating is enforced there
- Documented Sage expectation:
  - callers should block signing flows for wallets without secrets
- Current gap:
  - `has_secrets` is available, but no hard signing preflight guard was found
- Expected safe behavior:
  - watch-only wallets remain queryable
  - signing/submission paths fail fast before calling Sage

### 6.2 Request-only offers require a fee
- Edge case:
  - request-only offers are allowed only with a fee
- Affected file/function:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) `create_offer()`
- Documented Sage expectation:
  - request-only offers must include a fee
- Current gap:
  - `create_offer()` hardcodes `"fee": "0"`
- Expected safe behavior:
  - fee-free request-only offers are rejected or blocked before the Sage RPC call

### 6.3 Caller-side address and network validation
- Edge case:
  - wrong-network or malformed addresses must be blocked before send
- Affected file/function:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
    - `send_transaction()`
    - `send_transaction_multi()`
    - `send_cat_multi()`
- Documented Sage expectation:
  - callers should validate network names and should not rely on `check_address` alone
- Current gap:
  - send paths pass addresses straight through to Sage
- Expected safe behavior:
  - malformed and wrong-network destinations are rejected before signing/submission

### 6.4 Initialization failure and retry policy
- Edge case:
  - failed first init may block later retries; startup-sensitive operations must be serialized
- Affected file/function:
  - [chia_node.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py) `_log_in_fingerprint()`
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) `sage_login()`
- Documented Sage expectation:
  - initialization failure, retry, and startup ordering should be handled explicitly
- Current gap:
  - there is no explicit `initialize` call, so there is also no explicit init failure or retry handling
- Expected safe behavior:
  - init-vs-login state and retry behavior should be deterministic

## 7. Recommended implementation batches

### Batch 1: Sage startup lifecycle
- Batch name:
  - Sage startup lifecycle
- Issues included:
  - missing explicit Sage `initialize`
  - missing init failure/retry handling
  - lifecycle currently compressed into `resync + login`
- Files touched:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
  - [chia_node.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py)
- Why these changes belong together:
  - they all affect the same startup/login boundary
- Risk level:
  - Medium
- Whether it can be implemented independently:
  - Yes

### Batch 2: Pending and spendable endpoint corrections
- Batch name:
  - Pending and spendable endpoint corrections
- Issues included:
  - `get_pending_transactions()` should use the documented endpoint
  - `get_spendable_coin_count()` should use the documented endpoint
  - duplicate shadowing definitions should be removed
- Files touched:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Why these changes belong together:
  - both are adapter read helpers currently shadowed by duplicate definitions
- Risk level:
  - Low to Medium
- Whether it can be implemented independently:
  - Yes

### Batch 3: Offer creation contract fixes
- Batch name:
  - Offer creation contract fixes
- Issues included:
  - `create_offer()` ignores `validate_only`
  - request-only fee rule is not enforced
- Files touched:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Why these changes belong together:
  - both changes are inside the same public offer-construction function
- Risk level:
  - Medium
- Whether it can be implemented independently:
  - Yes

### Batch 4: Watch-only signing guardrails
- Batch name:
  - Watch-only signing guardrails
- Issues included:
  - signing operations are not blocked for wallets without secrets
- Files touched:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
  - possibly [chia_node.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py)
- Why these changes belong together:
  - this is one safety policy applied across signing entry points
- Risk level:
  - Medium
- Whether it can be implemented independently:
  - Yes

### Batch 5: Sync and readiness semantics
- Batch name:
  - Sync and readiness semantics
- Issues included:
  - `get_wallet_sync_status()` invents undocumented `synced=None` behavior
- Files touched:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Why these changes belong together:
  - this is one contained readiness logic correction
- Risk level:
  - Medium
- Whether it can be implemented independently:
  - Yes

### Batch 6: Cancel-offer success semantics
- Batch name:
  - Cancel-offer success semantics
- Issues included:
  - `cancel_offer()` treats undocumented `500` and `202` as success
- Files touched:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Why these changes belong together:
  - this is a narrow error-normalization correction in one function
- Risk level:
  - Low to Medium
- Whether it can be implemented independently:
  - Yes

### Batch 7: Send-path address and network validation
- Batch name:
  - Send-path address and network validation
- Issues included:
  - send helpers do not perform caller-side network/address validation
- Files touched:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Why these changes belong together:
  - all affected functions are outbound send helpers and need the same validation rule
- Risk level:
  - Low to Medium
- Whether it can be implemented independently:
  - Yes

### Batch 8: Offer-lock reconciliation correctness
- Batch name:
  - Offer-lock reconciliation correctness
- Issues included:
  - exact `offer_id`-based reconciliation is available but not consistently used
- Files touched:
  - [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
  - immediate Sage-specific callers if they consume heuristic lock attribution
- Why these changes belong together:
  - this is one data-model correction: prefer Sage's exact `offer_id` lock attribution
- Risk level:
  - Medium
- Whether it can be implemented independently:
  - Mostly yes, but exact caller dependencies should be checked first

## 8. Recommended implementation order

- 1. Pending and spendable endpoint corrections
- 2. Cancel-offer success semantics
- 3. Offer creation contract fixes
- 4. Watch-only signing guardrails
- 5. Send-path address and network validation
- 6. Sync and readiness semantics
- 7. Sage startup lifecycle
- 8. Offer-lock reconciliation correctness

This order is safest because it starts with the smallest adapter corrections, then moves into narrow contract fixes, then adds guardrails, then changes readiness semantics, then changes startup behavior, and leaves reconciliation changes for last.

## 9. Patch guidance for each batch

### Batch 1: Sage startup lifecycle
- Exact contract to preserve:
  - fingerprint-based login remains available
  - `_log_in_fingerprint()` remains the caller entry point
- Exact behavior to change:
  - add explicit init handling before login/session work
  - represent init failure separately from login failure
- Exact behavior that must not change:
  - successful local Sage startup
  - non-Sage wallet paths
- Likely regression risks:
  - startup timing changes
  - wallet-ready state may be delayed until init completes

### Batch 2: Pending and spendable endpoint corrections
- Exact contract to preserve:
  - `get_pending_transactions()` returns `list`
  - `get_spendable_coin_count(wallet_id: int = None) -> int`
  - callers should not need to change
- Exact behavior to change:
  - remove shadowing duplicate implementations
  - use Sage `get_pending_transactions`
  - use Sage `get_spendable_coin_count(asset_id)`
- Exact behavior that must not change:
  - safe empty/default returns on RPC failure
  - CAT/XCH wallet detection behavior
- Likely regression risks:
  - only if some hidden caller depended on the shadowed heuristic implementations

### Batch 3: Offer creation contract fixes
- Exact contract to preserve:
  - `create_offer()` remains the public adapter entry point
  - normal success response shape remains compatible with current offer-manager expectations
- Exact behavior to change:
  - stop silently ignoring `validate_only`
  - enforce request-only fee rule
- Exact behavior that must not change:
  - normal two-sided offer creation
  - current response normalization shape
- Likely regression risks:
  - callers may have implicitly relied on the ignored `validate_only` parameter

### Batch 4: Watch-only signing guardrails
- Exact contract to preserve:
  - watch-only wallets remain queryable
  - hot wallets with secrets remain usable
- Exact behavior to change:
  - signing/submission paths must fail fast for wallets without secrets
- Exact behavior that must not change:
  - read-only wallet operations
  - normal signing under hot wallets
- Likely regression risks:
  - environments unintentionally using watch-only keys will now fail earlier

### Batch 5: Sync and readiness semantics
- Exact contract to preserve:
  - `get_wallet_sync_status()` still returns reachability/syncing/synced information
- Exact behavior to change:
  - stop promoting undocumented `synced=None` conditions to synced/ready
- Exact behavior that must not change:
  - reachability detection
  - output shape
- Likely regression risks:
  - UI/health output may appear less optimistic

### Batch 6: Cancel-offer success semantics
- Exact contract to preserve:
  - `cancel_offer()` remains the public cancel adapter
  - documented `404 missing offer` success handling may remain if intentionally preserved
- Exact behavior to change:
  - stop treating `500` and `202` as success
- Exact behavior that must not change:
  - explicit successful cancel responses still normalize correctly
- Likely regression risks:
  - retry or polling code may need explicit non-success handling

### Batch 7: Send-path address and network validation
- Exact contract to preserve:
  - send functions remain the public send entry points
  - valid same-network sends still work
- Exact behavior to change:
  - reject malformed or wrong-network addresses before calling Sage
- Exact behavior that must not change:
  - valid addresses for the active network
  - payload shape after validation succeeds
- Likely regression risks:
  - previously tolerated invalid inputs will now fail earlier

### Batch 8: Offer-lock reconciliation correctness
- Exact contract to preserve:
  - caller-visible coin/offer structures should stay compatible unless clearly wrong
- Exact behavior to change:
  - use `offer_id` on owned coins as the primary lock-attribution source where lock attribution matters
- Exact behavior that must not change:
  - free-vs-locked coin visibility for callers
  - expected output fields consumed elsewhere
- Likely regression risks:
  - reconciliation changes may surface latent downstream assumptions

## 10. Tests to add or update

### Batch 1: Sage startup lifecycle
- Unit tests:
  - init success path
  - init failure path
  - login not attempted before init success
- Integration tests:
  - startup/login flow through `_log_in_fingerprint()`
- Regression tests:
  - duplicate startup attempts are serialized
- Tests expected to fail before patch:
  - init-before-login ordering tests
- Tests expected to pass after patch:
  - explicit init lifecycle tests

### Batch 2: Pending and spendable endpoint corrections
- Unit tests:
  - `get_pending_transactions` uses Sage pending endpoint
  - `get_pending_transactions` parses `pending_transactions`
  - `get_pending_transactions` accepts `transactions` and `data`
  - `get_pending_transactions` returns `[]` on `None` or exception
  - `get_spendable_coin_count` uses documented endpoint for XCH
  - `get_spendable_coin_count` uses documented endpoint for CAT
  - `get_spendable_coin_count` parses string count
  - `get_spendable_coin_count` returns `0` on missing CAT asset id
  - `get_spendable_coin_count` returns `0` on bad or missing count
- Integration tests:
  - none required in the first pass if unit tests fully isolate `rpc()`
- Regression tests:
  - only one public definition exists for each function name
- Tests expected to fail before patch:
  - endpoint-usage tests
  - duplicate-definition regression test
- Tests expected to pass after patch:
  - all endpoint-usage and duplicate-definition tests

### Batch 3: Offer creation contract fixes
- Unit tests:
  - `validate_only=True`
  - `validate_only=False`
  - request-only zero-fee failure
  - request-only nonzero-fee path
- Integration tests:
  - normal two-sided offer creation path
- Regression tests:
  - response shape remains compatible with current offer manager
- Tests expected to fail before patch:
  - `validate_only` behavior test
  - request-only zero-fee guard test
- Tests expected to pass after patch:
  - all of the above

### Batch 4: Watch-only signing guardrails
- Unit tests:
  - hot wallet allowed
  - watch-only wallet blocked
- Integration tests:
  - send blocked for watch-only wallet
  - create_offer blocked for watch-only wallet
- Regression tests:
  - read-only queries still work under watch-only
- Tests expected to fail before patch:
  - watch-only signing guard tests
- Tests expected to pass after patch:
  - watch-only guard tests

### Batch 5: Sync and readiness semantics
- Unit tests:
  - `synced=True`
  - `synced=False`
  - `synced=None`
  - missing optional fields
- Integration tests:
  - health/readiness flow if one exists
- Regression tests:
  - output shape remains stable
- Tests expected to fail before patch:
  - unknown-sync-state non-promotion tests
- Tests expected to pass after patch:
  - readiness semantic tests

### Batch 6: Cancel-offer success semantics
- Unit tests:
  - normal success payload
  - `404` missing-offer success path
  - `500` non-success path
  - `202` non-success path unless separately verified
- Integration tests:
  - cancel flow through current caller if available
- Regression tests:
  - return shape remains compatible for documented success cases
- Tests expected to fail before patch:
  - `500` and `202` non-success tests
- Tests expected to pass after patch:
  - cancel normalization tests

### Batch 7: Send-path address and network validation
- Unit tests:
  - valid address accepted
  - wrong-network prefix rejected
  - malformed address rejected
  - multi-send fails when one destination is invalid
- Integration tests:
  - send path with a valid address on the intended network
- Regression tests:
  - valid payloads still reach Sage unchanged after validation
- Tests expected to fail before patch:
  - wrong-network and malformed-address rejection tests
- Tests expected to pass after patch:
  - all send validation tests

### Batch 8: Offer-lock reconciliation correctness
- Unit tests:
  - owned coin with `offer_id=null`
  - owned coin with `offer_id` set
  - mixed free and locked owned set
- Integration tests:
  - caller path that consumes locked/free attribution
- Regression tests:
  - no unexpected output-shape breakage for existing coin maps
- Tests expected to fail before patch:
  - tests asserting exact `offer_id` attribution if exact attribution is not yet used
- Tests expected to pass after patch:
  - exact attribution tests

## 11. Acceptance criteria

### Batch 1: Sage startup lifecycle
- What must be true after fix:
  - explicit init-before-login handling exists
  - init failure is distinct from login failure
- What must not break:
  - successful local Sage startup
  - fingerprint login flow
- How to verify success:
  - trace startup path and run init success/failure tests

### Batch 2: Pending and spendable endpoint corrections
- What must be true after fix:
  - `get_pending_transactions()` uses Sage `get_pending_transactions`
  - `get_spendable_coin_count()` uses Sage `get_spendable_coin_count(asset_id)`
  - only one public definition remains for each
- What must not break:
  - return types
  - CAT/XCH handling
  - safe fallback behavior
- How to verify success:
  - unit tests plus duplicate-definition regression checks

### Batch 3: Offer creation contract fixes
- What must be true after fix:
  - `validate_only` is honored or explicitly rejected
  - request-only fee rule is enforced
- What must not break:
  - normal two-sided offer creation
  - response shape compatibility
- How to verify success:
  - create-offer tests for both modes and request-only edge cases

### Batch 4: Watch-only signing guardrails
- What must be true after fix:
  - watch-only wallets cannot enter signing paths
- What must not break:
  - query operations under watch-only
  - hot-wallet signing flows
- How to verify success:
  - watch-only and hot-wallet path tests

### Batch 5: Sync and readiness semantics
- What must be true after fix:
  - unknown sync state is not silently treated as synced
- What must not break:
  - reachability reporting
  - output shape
- How to verify success:
  - mocked sync payload tests

### Batch 6: Cancel-offer success semantics
- What must be true after fix:
  - `404` may remain success if intentionally preserved
  - `500` and `202` are not treated as success by default
- What must not break:
  - explicit success path
- How to verify success:
  - cancel normalization tests

### Batch 7: Send-path address and network validation
- What must be true after fix:
  - malformed and wrong-network addresses are rejected before calling Sage
- What must not break:
  - valid same-network send paths
- How to verify success:
  - validation tests for valid and invalid destinations

### Batch 8: Offer-lock reconciliation correctness
- What must be true after fix:
  - exact `offer_id` data is used where lock attribution matters
- What must not break:
  - caller-visible coin/offer shapes unless clearly wrong and intentionally updated
- How to verify success:
  - mixed lock/free reconciliation tests

## 12. Constraints for Claude

Strict instructions:
- do not do broad refactors
- preserve public adapter shape unless clearly wrong
- preserve caller compatibility unless proven unnecessary
- do not invent Sage semantics
- use documented Sage endpoints where available
- keep changes batch-scoped
- add tests with each batch

Additional constraints:
- prefer small safe batches over cross-cutting cleanup
- do not change unrelated wallet backends
- do not silently change response shapes consumed elsewhere unless a test-backed fix requires it
- if a batch reveals a hidden dependency, stop and document it before widening scope

## 13. Known uncertainties

- The current runtime environment may already initialize Sage externally before this adapter is used. The repository-local audit did not find an explicit project call site for `initialize`, but implementation should confirm whether any hidden external bootstrapping exists.
- `create_offer(validate_only=...)` clearly ignores the parameter today, but the safest implementation choice is still open:
  - implement a real non-submitting path if supported, or
  - explicitly reject unsupported validate-only requests
- `cancel_offer()` callers may currently depend on `"uncertain": True` plus `"success": True`; that dependency should be checked before changing return semantics.
- Offer-lock reconciliation should identify exact downstream callers before replacing heuristic attribution logic.

## 14. Suggested way to hand this to Claude

The safest approach is to give Claude one batch at a time, not the full Sage workstream at once.

Recommended first batch:
- Batch 2: Pending and spendable endpoint corrections

Why start there:
- it is the smallest safe batch
- it is confined to [wallet_sage.py](/C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- repository search already confirmed:
  - `get_pending_transactions()` callers do not pass `wallet_id`
  - callers only depend on "returns a list, empty means no pending transactions"
  - `get_spendable_coin_count()` has no external call sites outside its definitions

Suggested handoff flow:
1. give Claude only one batch brief at a time
2. require tests with that batch
3. after Claude produces a patch, use Codex to review:
   - whether only intended files changed
   - whether public adapter contracts were preserved
   - whether new tests are high-signal and batch-scoped
   - whether the patch introduced any invented Sage semantics
