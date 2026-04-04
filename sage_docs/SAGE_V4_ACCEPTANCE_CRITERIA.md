# SAGE V4 Acceptance Criteria

This document defines what must be true after each Sage integration fix, what must not change, how to verify it, and which edge cases must be tested.

## 1. Sage initialization lifecycle
- What must be true after fix:
  - Sage initialization is executed before wallet-bound login or transaction operations.
  - Initialization failure is surfaced distinctly from login failure.
- What must not change:
  - Successful local Sage startup and normal login must still work.
  - Fingerprint-based login flow must remain available.
- How to verify it:
  - Trace startup path from `_log_in_fingerprint()` through the Sage adapter.
  - Confirm initialization is called before login/session work.
- Edge cases to test:
  - initialization succeeds
  - initialization fails
  - initialization is attempted twice

## 2. `get_pending_transactions()` endpoint usage
- What must be true after fix:
  - The active implementation calls Sage `get_pending_transactions`.
  - There is only one public `get_pending_transactions()` definition.
- What must not change:
  - Callers still receive a list result.
- How to verify it:
  - Search `wallet_sage.py` for duplicate definitions.
  - Mock Sage response for `get_pending_transactions` and assert parsed output.
- Edge cases to test:
  - empty pending list
  - one pending item
  - unexpected but valid empty payload

## 3. `get_spendable_coin_count()` endpoint usage
- What must be true after fix:
  - The active implementation calls Sage `get_spendable_coin_count(asset_id)`.
  - There is only one public `get_spendable_coin_count()` definition.
- What must not change:
  - XCH and CAT wallet callers still get integer counts.
- How to verify it:
  - Search `wallet_sage.py` for duplicate definitions.
  - Mock count responses for XCH and CAT.
- Edge cases to test:
  - `count` as int
  - `count` as string
  - missing CAT asset id

## 4. `create_offer(validate_only=...)` behavior
- What must be true after fix:
  - `validate_only` is either truly honored or explicitly rejected as unsupported.
  - The adapter no longer silently ignores the parameter.
- What must not change:
  - Normal offer creation response shape must remain compatible with existing offer manager expectations.
- How to verify it:
  - Execute both `validate_only=True` and `validate_only=False` code paths.
  - Assert the return value clearly reflects the mode used.
- Edge cases to test:
  - normal XCH↔CAT offer
  - validate-only request
  - unsupported validate-only path if rejected

## 5. Request-only offer fee rule
- What must be true after fix:
  - Fee-free request-only offers are blocked or handled before calling Sage.
  - Request-only offers with a required fee can proceed.
- What must not change:
  - Normal two-sided offers must still work with zero fee if otherwise valid.
- How to verify it:
  - Build a request-only offer payload and observe adapter behavior.
- Edge cases to test:
  - request-only, zero fee
  - request-only, nonzero fee
  - normal offer with offered and requested assets

## 6. Sync/readiness reporting
- What must be true after fix:
  - `synced=True` is reported only from documented or explicitly supported signals.
  - Unknown sync state is not silently promoted to synced.
- What must not change:
  - Reachability detection must still work.
- How to verify it:
  - Mock `get_sync_status` payloads and inspect `get_wallet_sync_status()` output.
- Edge cases to test:
  - `synced=True`
  - `synced=False`
  - `synced=None`
  - missing optional fields

## 7. `cancel_offer()` success handling
- What must be true after fix:
  - `404/missing offer` can remain a success case if kept.
  - `500` and `202` are not automatically promoted to success.
- What must not change:
  - Normal successful cancel responses still normalize into the expected adapter format.
- How to verify it:
  - Mock `_sage_post()` failures and inspect returned result objects.
- Edge cases to test:
  - 404 missing offer
  - 500 server error
  - 202 accepted/non-final
  - explicit success payload

## 8. `offer_id`-based lock attribution
- What must be true after fix:
  - Where lock attribution matters, the implementation uses Sage `offer_id` on owned coins as the primary source.
- What must not change:
  - Coin maps and offer reconciliation outputs used by the rest of the bot must remain structurally compatible.
- How to verify it:
  - Feed owned/selectable coin sets with and without `offer_id`.
  - Confirm locked coins are attributed directly from `offer_id`.
- Edge cases to test:
  - free owned coin
  - offer-locked owned coin
  - mixed owned set with several locks

## 9. Watch-only wallet handling
- What must be true after fix:
  - Watch-only keys can be listed and inspected.
  - Signing flows are blocked when `has_secrets` is false.
- What must not change:
  - Hot-wallet flows with secrets must still work.
- How to verify it:
  - Mock `get_sage_keys()`/active key metadata with `has_secrets` true and false.
- Edge cases to test:
  - watch-only login
  - send attempt under watch-only wallet
  - offer creation under watch-only wallet

## 10. Address/network validation on send paths
- What must be true after fix:
  - Send paths reject wrong-network or malformed addresses before calling Sage.
- What must not change:
  - Valid same-network addresses must still pass.
- How to verify it:
  - Run send-path validation with valid and invalid addresses and inspect preflight behavior.
- Edge cases to test:
  - valid address for intended network
  - wrong network prefix
  - malformed bech32 string
  - multi-send with one invalid destination

## 11. Initialization failure and retry handling
- What must be true after fix:
  - Initialization failure has a defined state and retry behavior.
  - A failed first startup attempt does not silently devolve into generic login failure.
- What must not change:
  - Successful first startup must remain straightforward.
- How to verify it:
  - Simulate init failure followed by retry.
- Edge cases to test:
  - first init failure
  - retry success
  - concurrent startup attempts
