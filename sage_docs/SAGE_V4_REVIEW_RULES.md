# Sage V4 Review Rules

Use this checklist for any future project integrating Sage. These rules are written from the caller/integration perspective.

## Lifecycle Requirements
- Call Sage `initialize` before wallet-bound reads, writes, or transaction operations.
- Handle initialization failure separately from login failure.
- Do not assume failed initialization is safely retryable without an explicit reset/retry policy.
- Serialize startup-sensitive operations such as initialize, login, wallet switching, and network switching.
- Do not treat `resync + login` as a substitute for the documented initialization lifecycle.

## Signing Safety Rules
- Treat watch-only wallets as queryable but non-signing.
- Use `has_secrets` or equivalent wallet metadata to block signing flows before transaction construction/submission.
- Do not let send, offer, split, combine, or cancel paths discover `NoSigningKey` only after entering Sage.
- Distinguish construction, signing, and submission semantics in the adapter.
- Do not silently ignore “validate-only” or “dry-run” parameters exposed by the adapter API.

## Offer Creation Rules
- Use the correct Sage asset-id namespace when building offers.
- Enforce documented request-only offer rules, including the required fee.
- Treat offer creation, import, view, take, and cancel as separate operations with separate contracts.
- Preserve a stable response shape for the application layer, but do not invent success when the Sage result is non-final.
- Only mark cancel success for documented success cases such as explicit success or missing-offer terminal cases.

## Sync / Readiness Rules
- Use documented sync signals from `get_sync_status` as the source of truth.
- Do not promote undocumented values such as `synced=None` into “ready” without an explicit supported contract.
- Distinguish:
  - unreachable
  - reachable but not synced
  - reachable but sync state unknown
  - ready/synced
- Do not collapse all startup failures into generic login failures.

## Address / Network Validation Rules
- Validate destination addresses against the intended active network before calling Sage.
- Do not treat `check_address` as a complete network validator.
- Validate candidate network names against `get_networks` before persisting or switching.
- Reject wrong-network addresses before signing/submission code paths.
- Normalize hex and identifier inputs consistently in the adapter layer.

## Coin State / Pending Transaction Rules
- Use the documented endpoint for each intent:
  - `get_pending_transactions` for unconfirmed transaction tracking
  - `get_spendable_coin_count` for spendable coin counts
  - `get_coins(filter_mode="owned")` with `offer_id` for exact lock attribution
- Prefer `offer_id` on owned coins over subtraction heuristics such as `owned - selectable` when exact lock attribution is required.
- Do not derive pending transaction state from general transaction history when Sage already exposes a dedicated pending endpoint.
- Do not replace documented count endpoints with approximate list-length logic unless the API contract explicitly requires it.
- Keep exactly one public implementation per Sage adapter function name; do not leave shadowing duplicates in the module.
