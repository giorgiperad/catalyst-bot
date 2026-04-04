# Sage Integration Guide

## Purpose

This guide explains how another system should integrate with Sage safely.

## How External Systems Should Use Sage

### Recommended Lifecycle

Use this order:

1. start host application
2. call `initialize`
3. fetch or configure network state if needed
4. import or enumerate wallets
5. call `login` with target fingerprint
6. only then:
   - query balances/assets
   - build transactions
   - sign messages
   - create or take offers
7. optionally start RPC if needed

### Treat Sage As Stateful

Do not treat Sage as a stateless RPC backend.

Sage depends on:

- persisted config
- in-memory active wallet
- current network
- peer state
- local key availability

### Validate Inputs Before Call Time

Callers should validate:

- address belongs to expected network
- id namespace is correct
- amounts fit expected numeric range
- memos are hex bytes
- network name exists in `get_networks`

## Integration Assumptions Sage Makes

### Assumptions About Callers

- caller initializes once before normal use
- caller logs in before wallet-dependent calls
- caller understands hot vs watch-only wallet difference
- caller understands `auto_submit` does not default to true
- caller does not race wallet/network switching from multiple places

### Assumptions About Data Formats

- asset ids are exact expected format
- memos are binary payloads encoded as hex
- public keys and signatures use fixed-length hex
- `Amount` values are convertible to `u64`
- DID/NFT/option/collection ids are correctly prefixed addresses

### Assumptions About Network Responses

- external metadata providers return valid data quickly enough
- peer submission results are usable for status handling
- CNI offer-code service returns expected JSON

### Assumptions About Timing and State

- startup is serialized
- config persists successfully
- sync manager is live before wallet operations need it
- wallet switch/network switch side effects are allowed to mutate global state

## Risks

### High-Risk Integration Points

- hidden session dependence
- invalid persisted network names
- using watch-only wallets for signing flows
- duplicate RPC startup
- retry after failed initialize
- relying on partial validators like `check_address`
- assuming success means submission

### Medium-Risk Integration Points

- offer paths with mixed asset namespaces
- NFT URI fetches with remote dependency and timeout behavior
- theme save/load semantics
- partial/no-op success responses
- parser prefix/casing inconsistencies

## Best Practices

### Session Safety

- always know which fingerprint is active
- avoid implicit session assumptions across processes/components
- re-check login state before signing or broadcasting

### Network Safety

- validate chosen network name before persisting
- validate address prefix outside Sage too
- keep caller-side network context explicit

### Transaction Safety

- decide intentionally whether each flow is:
  - construct-only
  - sign-only
  - sign-and-submit
- log returned summaries and spend bundles
- treat `auto_submit = false` responses as not yet broadcast

### Wallet Capability Safety

- track whether imported wallets have secret material
- block signing/UI flows for watch-only wallets before Sage returns `NoSigningKey`

### Error Handling

- map Sage errors into retryable, validation, authorization, not-found, and fatal/internal buckets
- explicitly handle `None` and empty responses

### Concurrency Safety

- serialize `initialize`, `start_rpc_server`, `switch_wallet`, `set_network`, and `set_network_override`
- avoid concurrent callers mutating shared Sage state without coordination

## Common Mistakes

- calling endpoints before `initialize`
- calling transaction endpoints before `login`
- passing wrong id type
- assuming memos are plain strings
- assuming all successful transaction responses are broadcast
- allowing arbitrary network names into config
- ignoring watch-only wallet limitations
- using `check_address` as complete validator
- assuming external metadata/network dependencies are optional
- ignoring no-op success paths in theme/log operations

## Practical Adapter Guidance

### Recommended Wrapper Model

Build an integration wrapper that:

- owns Sage lifecycle
- exposes explicit session state
- normalizes inputs
- validates network names and address formats
- tags each operation as read-only, signing-required, or network-submitting
- wraps errors into stable application-specific categories

### Suggested Safeguards

- cache `get_networks` and validate before any set-network call
- block `move_key` with caller-side index bounds checks
- make RPC startup idempotent at integration layer
- add initialize retry/reset policy if startup fails
- enforce memo encoding rules centrally
- normalize `0x` and `0X` before parser-bound calls
