# Sage Architecture

## Overview

Sage is a Chia wallet system built as a layered application:

- React frontend in `src`
- Tauri desktop/mobile shell in `src-tauri`
- Rust backend facade in `crates/sage`
- Shared API schema in `crates/sage-api`
- Wallet engine in `crates/sage-wallet`
- Persistence layer in `crates/sage-database`
- Supporting crates for config, key storage, assets, RPC, and plugin integration

At runtime, Sage behaves like a stateful wallet service rather than a stateless library. Most meaningful operations depend on:

- initialization having completed
- a valid network being configured
- a wallet fingerprint being selected
- a wallet session being effectively logged in
- local secret material being present for signing flows

## Top-Level Modules

### Frontend

- `src/App.tsx`, `src/main.tsx`
  - React entry and route shell
- `src/pages`
  - top-level wallet screens
- `src/components`
  - reusable and feature UI components
- `src/hooks`
  - caller orchestration and frontend-side state sequencing
- `src/contexts`
  - shared app state providers
- `src/walletconnect`
  - frontend WalletConnect integration

### Desktop / IPC Shell

- `src-tauri/src/commands.rs`
  - Tauri IPC commands
  - generated endpoint wrapper
  - startup, RPC server controls, validation helpers, logs, offer-code download
- `src-tauri/src/app_state.rs`
  - app bootstrap wiring
- `src-tauri/src/lib.rs`, `src-tauri/src/main.rs`
  - Tauri runner

### Backend Facade

- `crates/sage/src/sage.rs`
  - central state object
  - config/keychain/network/wallet lifecycle
  - peer persistence
  - wallet switching
  - database connection management
- `crates/sage/src/endpoints/*.rs`
  - main callable business API
- `crates/sage/src/utils/*.rs`
  - parsing, spend submission, confirmation/summary, caching
- `crates/sage/src/error.rs`
  - shared error model and error-kind mapping

### Shared API Contract

- `crates/sage-api/src/requests/*.rs`
  - request/response types for all endpoints
- `crates/sage-api/src/records/*.rs`
  - structured records returned to callers
- `crates/sage-api/src/types/*.rs`
  - shared types like `Amount`, `Unit`, `Asset`
- `crates/sage-api/endpoints.json`
  - endpoint registry
- `crates/sage-api/endpoints-tauri.json`
  - WalletConnect/Tauri-only endpoint registry

### Wallet Engine

- `crates/sage-wallet/src`
  - coin selection
  - spend construction
  - offer logic
  - DID/NFT/option handling
  - sync manager and peer sync logic

### Persistence

- `crates/sage-database/src`
  - SQLite access layer
  - table modules
  - serialization helpers
  - maintenance/stats
- `migrations/*.sql`
  - schema evolution
- `.sqlx/*.json`
  - SQLx prepared-query metadata

### Supporting Crates

- `crates/sage-config`
  - config and migration of old config/network formats
- `crates/sage-keychain`
  - key and secret persistence/encryption
- `crates/sage-assets`
  - CAT/NFT metadata fetch and parsing
- `crates/sage-rpc`
  - RPC server integration
- `tauri-plugin-sage`
  - custom Tauri plugin surface

## Core Runtime State

### `Sage`

Defined in `crates/sage/src/sage.rs`.

Main fields:

- `path`
  - root app data directory
- `config`
  - global/network config
- `wallet_config`
  - wallet-specific settings and ordering
- `network_list`
  - available network definitions
- `keychain`
  - stored public/secret keys
- `wallet`
  - currently active wallet engine instance
- `peer_state`
  - live peer connection state
- `command_sender`
  - sync manager command channel
- `unit`
  - current display unit
- `test`
  - testing mode flag

### Wallet Access Gate

`wallet()` in `crates/sage/src/sage.rs` is the main guard for session-dependent behavior.

It assumes:

- `config.global.fingerprint` is set
- the key exists in keychain
- the in-memory wallet exists
- the in-memory wallet matches the selected fingerprint

If any of those fail, many endpoints fail with:

- `NotLoggedIn`
- `UnknownFingerprint`

## Data Flow

### UI / Integration Path

1. External caller or frontend invokes a Tauri command or endpoint wrapper.
2. `src-tauri/src/commands.rs` routes:
   - direct commands like `initialize`, `validate_address`, `get_logs`
   - generated `endpoint(req)` dispatch for request/response APIs
3. `AppState` locks the shared `Sage` instance.
4. `Sage` endpoint implementation performs:
   - session lookup
   - parsing/validation
   - database reads/writes
   - wallet engine calls
   - optional network submission
5. Shared response records from `sage-api` are returned through IPC/RPC.

### Transaction Path

1. Caller submits transaction request in `sage-api` request shape.
2. Endpoint in `crates/sage/src/endpoints/transactions.rs` parses addresses, ids, memos, and amounts.
3. Wallet engine builds `CoinSpend` list.
4. `transact()` / `transact_with()`:
   - optionally signs and submits if `auto_submit = true`
   - always builds confirmation summary
5. Caller receives summary plus coin spends or a specialized transaction response.

### Offer Path

1. Caller creates, imports, views, or takes an offer.
2. Offer endpoint decodes or constructs offer data.
3. External asset metadata may be fetched for NFTs/options.
4. Offer is signed or summarized.
5. Offer is optionally imported into local DB.
6. Cancellation/take flows may create or submit transactions.

### Sync / Peer Path

1. `initialize()` sets up sync manager and peer state.
2. `setup_peers()` restores peer snapshot from disk.
3. Sync manager commands are sent over `command_sender`.
4. Peer state is periodically persisted by the background loop in `src-tauri/src/commands.rs`.

## Call Graph Summary

### Startup

- `initialize`
  - `app_state::initialize`
  - `Sage::initialize`
  - background peer-save loop
  - optional RPC startup

- `Sage::initialize`
  - `setup_keys`
  - `setup_config`
  - `setup_logging`
  - `setup_sync_manager`
  - `setup_peers`

### Wallet Session

- `login`
  - set fingerprint
  - save config
  - `switch_wallet`

- `logout`
  - clear fingerprint
  - save config
  - `switch_wallet`

- `switch_wallet`
  - `switch_network`
  - extract public key
  - connect DB
  - run migrations
  - construct `Wallet`
  - send sync-manager wallet switch command

### Endpoint Dispatch

- Tauri `endpoint(req)`
  - generated by `impl_endpoints_tauri!`
  - forwards to `state.lock().await.endpoint(req)`
  - async or sync behavior depends on endpoint registry

### Shared Validation Helpers

- `parse_address`
  - network-prefix enforced address decode
- `parse_asset_id`, `parse_nft_id`, `parse_did_id`, `parse_option_id`
  - strict ID parsing
- `parse_amount`
  - `Amount -> u64` guard
- `parse_memos`
  - hex bytes only

### Submission Helpers

- `sign` in `crates/sage/src/utils/spends.rs`
  - signs spend bundle
- `submit` in `crates/sage/src/utils/spends.rs`
  - sends to peers / insert transaction side effects
- `summarize` in `crates/sage/src/utils/confirmation.rs`
  - produces caller-facing confirmation summary

## Architectural Behaviors That Matter For Integration

- Sage is stateful and mutable.
- Config is persisted eagerly.
- Wallet/network switches affect later behavior globally.
- Many endpoint implementations depend on helper parsing functions with strict formats.
- Auto-submit is usually opt-in.
- Some read paths return `None` or `false` rather than errors.
- Some external metadata/network calls are part of normal behavior, not exceptional behavior.

## Reusable Audit Notes

When auditing another system that integrates Sage, verify:

- it respects Sage lifecycle ordering
- it knows which calls require secrets
- it validates network/address/id formats before call time
- it distinguishes construct-only vs submit-and-broadcast flows
- it handles empty responses and not-found cases correctly
- it serializes stateful operations like initialize, wallet switch, and RPC startup
