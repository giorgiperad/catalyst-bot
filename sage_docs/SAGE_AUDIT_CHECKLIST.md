# Sage Audit Checklist

## Purpose

Use this checklist to audit a project that integrates Sage.

## Lifecycle

- [ ] The project calls `initialize` before any wallet/data/transaction operation.
- [ ] It handles `initialize` failure explicitly.
- [ ] It does not assume failed initialization can always be retried safely.
- [ ] It prevents duplicate initialization from multiple callers.
- [ ] It serializes startup-sensitive operations.

## Session and Wallet State

- [ ] The project calls `login` before wallet-bound endpoints.
- [ ] It tracks the active fingerprint explicitly.
- [ ] It handles `NotLoggedIn` and `UnknownFingerprint` distinctly.
- [ ] It does not assume the wallet session is stateless between calls.
- [ ] It understands that watch-only imports can exist.
- [ ] It blocks signing flows for wallets without secrets.

## Network Handling

- [ ] The project validates candidate network names against `get_networks`.
- [ ] It does not persist arbitrary network names into Sage.
- [ ] It validates address prefixes against the intended network before calling Sage.
- [ ] It does not rely solely on `check_address` for network correctness.
- [ ] It coordinates wallet/network switching to avoid races.

## Input Validation

- [ ] It distinguishes CAT asset ids from DID/NFT/option/collection ids.
- [ ] It normalizes hex inputs consistently.
- [ ] It handles both `0x` and `0X` in its own adapter layer.
- [ ] It validates memos as hex bytes, not plain strings.
- [ ] It bounds-checks numeric inputs before Sage call time.
- [ ] It validates move-key indices before calling `move_key`.

## Transaction Semantics

- [ ] The project distinguishes construction, signing, and submission/broadcast.
- [ ] It does not assume `auto_submit` is true by default.
- [ ] It records whether a returned response was broadcast or only prepared.
- [ ] It handles submission failures separately from construction failures.
- [ ] It understands that WalletConnect immediate submission can return pending, failed, or unknown.

## Offer Handling

- [ ] The project uses correct asset-id namespace when building offers.
- [ ] It enforces amount `1` for NFT and option offer items.
- [ ] It handles request-only offer fee requirement.
- [ ] It treats offer import/view/take/cancel as separate behaviors.
- [ ] It audits rare option/NFT offer branches carefully.

## Read Semantics

- [ ] The project handles `Option`-like empty results correctly.
- [ ] It does not convert every `None` into an exception automatically.
- [ ] It expects some theme/log operations to be no-op or partial-success.
- [ ] It understands getters may return synthetic fallback records.

## External Dependency Handling

- [ ] It treats Dexie/NFT URI/peer submission/CNI offer-code services as unreliable dependencies.
- [ ] It applies timeout/retry policy outside Sage where needed.
- [ ] It logs or surfaces metadata-fetch failures meaningfully.
- [ ] It does not assume all external success payloads are perfectly shaped.

## RPC and Concurrency

- [ ] The project makes RPC startup idempotent.
- [ ] It avoids starting the Sage RPC server more than once.
- [ ] It coordinates stop/start RPC transitions.
- [ ] It prevents concurrent global-state mutations without ordering.

## Error Handling

- [ ] The project maps Sage errors into stable application-level categories.
- [ ] It distinguishes validation/API, unauthorized/session, not-found, internal/retryable, and DB migration/version errors.
- [ ] It does not treat all failures as user input errors.
- [ ] It does not suppress useful Sage error details that would help debugging.

## Theme and File Paths

- [ ] The project does not interpret theme save/delete success as guaranteed material change.
- [ ] It handles missing log/theme directories gracefully.
- [ ] It audits any feature depending on `save_user_theme` for partial-success behavior.

## Common Bugs To Check For

- [ ] Calling transaction APIs before login
- [ ] Sending plain-text memos
- [ ] Using wrong id namespace for assets
- [ ] Assuming successful transaction response means network submission
- [ ] Using watch-only wallets for signing
- [ ] Saving invalid network names
- [ ] Starting RPC twice
- [ ] Using `check_address` as complete validator
- [ ] Failing to normalize hex prefixes
- [ ] Mishandling `None` or empty responses
- [ ] Missing bounds check before `move_key`

## High-Priority Manual Review Targets

- [ ] Project initialization wrapper
- [ ] Wallet session manager
- [ ] Network selection UI / config persistence
- [ ] Transaction submission wrapper
- [ ] Offer creation/import flows
- [ ] WalletConnect adapter
- [ ] Error translation layer
- [ ] Retry and timeout policy around external metadata/network calls
