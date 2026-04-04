# Sage API Reference

## Scope

This document summarizes Sage's callable surface for integration and audit work.

Companion detailed inventories:

- `sage_functional_surface.md`
- `sage_execution_paths.md`

## Access Surfaces

### Tauri Commands

Defined in `src-tauri/src/commands.rs`.

- `initialize() -> Result<()>`
- `endpoint(req: Endpoint) -> Result<EndpointResponse>`
- `validate_address(address: String) -> Result<bool>`
- `network_config() -> Result<NetworkConfig>`
- `wallet_config(fingerprint: u32) -> Result<Option<Wallet>>`
- `default_wallet_config() -> Result<WalletDefaults>`
- `is_rpc_running() -> Result<bool>`
- `start_rpc_server() -> Result<()>`
- `stop_rpc_server() -> Result<()>`
- `get_rpc_run_on_startup() -> Result<bool>`
- `set_rpc_run_on_startup(run_on_startup: bool) -> Result<()>`
- `switch_wallet() -> Result<()>`
- `move_key(fingerprint: u32, index: u32) -> Result<()>`
- `download_cni_offercode(code: String) -> Result<String>`
- `get_logs() -> Result<Vec<LogFile>>`

## Authentication and Keys

- `login(fingerprint) -> LoginResponse`
- `logout() -> LogoutResponse`
- `resync(fingerprint, delete_coins, delete_assets, delete_files, delete_offers, delete_addresses, delete_blocks) -> ResyncResponse`
- `generate_mnemonic(use_24_words) -> GenerateMnemonicResponse`
- `import_key(name, key, derivation_index, hardened, unhardened, save_secrets, login, emoji) -> ImportKeyResponse`
- `delete_database(fingerprint, network) -> DeleteDatabaseResponse`
- `delete_key(fingerprint) -> DeleteKeyResponse`
- `rename_key(fingerprint, name) -> RenameKeyResponse`
- `set_wallet_emoji(fingerprint, emoji) -> SetWalletEmojiResponse`
- `get_key(fingerprint?) -> GetKeyResponse`
- `get_secret_key(fingerprint) -> GetSecretKeyResponse`
- `get_keys() -> GetKeysResponse`

Usage notes:

- `import_key` accepts mnemonic, secret key hex, or public key hex
- `import_key` can create watch-only wallets
- `login` and `logout` rebuild wallet state

## Data and Query Endpoints

- `get_version() -> GetVersionResponse`
- `perform_database_maintenance(force_vacuum) -> PerformDatabaseMaintenanceResponse`
- `get_database_stats() -> GetDatabaseStatsResponse`
- `get_sync_status() -> GetSyncStatusResponse`
- `check_address(address) -> CheckAddressResponse`
- `get_derivations(hardened, offset, limit) -> GetDerivationsResponse`
- `get_are_coins_spendable(coin_ids) -> GetAreCoinsSpendableResponse`
- `get_spendable_coin_count(asset_id?) -> GetSpendableCoinCountResponse`
- `get_coins_by_ids(coin_ids) -> GetCoinsByIdsResponse`
- `get_coins(asset_id?, offset, limit, sort_mode, filter_mode, ascending) -> GetCoinsResponse`
- `get_all_cats() -> GetAllCatsResponse`
- `get_cats() -> GetCatsResponse`
- `get_token(asset_id?) -> GetTokenResponse`
- `get_dids() -> GetDidsResponse`
- `get_minter_did_ids(limit, offset) -> GetMinterDidIdsResponse`
- `is_asset_owned(asset_id) -> IsAssetOwnedResponse`
- `get_options(...) -> GetOptionsResponse`
- `get_option(option_id) -> GetOptionResponse`
- `get_pending_transactions() -> GetPendingTransactionsResponse`
- `get_transaction(height) -> GetTransactionResponse`
- `get_transactions(find_value, ascending, limit, offset) -> GetTransactionsResponse`
- `get_nft_collections(limit, offset, include_hidden) -> GetNftCollectionsResponse`
- `get_nft_collection(collection_id?) -> GetNftCollectionResponse`
- `get_nfts(...) -> GetNftsResponse`
- `get_nft(nft_id) -> GetNftResponse`
- `get_nft_data(nft_id) -> GetNftDataResponse`
- `get_nft_icon(nft_id) -> GetNftIconResponse`
- `get_nft_thumbnail(nft_id) -> GetNftThumbnailResponse`

Usage notes:

- many getters return `Option<T>` inside response rather than not-found errors
- grouped NFT queries support special `"none"` sentinels
- `get_nft_collection(None)` returns an uncategorized synthetic collection

## Transaction Endpoints

- `send_xch(address, amount, fee, memos, clawback, auto_submit) -> TransactionResponse`
- `bulk_send_xch(addresses, amount, fee, memos, auto_submit) -> TransactionResponse`
- `combine(coin_ids, fee, auto_submit) -> TransactionResponse`
- `split(coin_ids, output_count, fee, auto_submit) -> TransactionResponse`
- `auto_combine_xch(max_coins, max_coin_amount, fee, auto_submit) -> AutoCombineXchResponse`
- `issue_cat(name, ticker, amount, fee, auto_submit) -> TransactionResponse`
- `send_cat(asset_id, address, amount, fee, include_hint, memos, clawback, auto_submit) -> TransactionResponse`
- `bulk_send_cat(asset_id, addresses, amount, fee, include_hint, memos, auto_submit) -> TransactionResponse`
- `auto_combine_cat(asset_id, max_coins, max_coin_amount, fee, auto_submit) -> AutoCombineCatResponse`
- `multi_send(payments, fee, auto_submit) -> TransactionResponse`
- `create_did(name, fee, auto_submit) -> TransactionResponse`
- `bulk_mint_nfts(mints, did_id, fee, auto_submit) -> BulkMintNftsResponse`
- `transfer_nfts(nft_ids, address, fee, clawback, auto_submit) -> TransactionResponse`
- `add_nft_uri(nft_id, kind, uri, fee, auto_submit) -> TransactionResponse`
- `assign_nfts_to_did(nft_ids, did_id, fee, auto_submit) -> TransactionResponse`
- `transfer_dids(did_ids, address, fee, clawback, auto_submit) -> TransactionResponse`
- `normalize_dids(did_ids, fee, auto_submit) -> TransactionResponse`
- `mint_option(underlying, strike, expiration_seconds, fee, auto_submit) -> MintOptionResponse`
- `transfer_options(option_ids, address, fee, clawback, auto_submit) -> TransactionResponse`
- `exercise_options(option_ids, fee, auto_submit) -> TransactionResponse`
- `finalize_clawback(coin_ids, fee, auto_submit) -> TransactionResponse`
- `sign_coin_spends(coin_spends, partial, auto_submit) -> SignCoinSpendsResponse`
- `view_coin_spends(coin_spends) -> ViewCoinSpendsResponse`
- `submit_transaction(spend_bundle) -> SubmitTransactionResponse`

Usage notes:

- `auto_submit` is usually opt-in
- many transaction calls can return construct-only output
- callers should distinguish construction from submission

## Offers

- `make_offer(requested_assets, offered_assets, fee, receive_address, expires_at_second, auto_import, coin_ids) -> MakeOfferResponse`
- `take_offer(offer, fee, auto_submit) -> TakeOfferResponse`
- `combine_offers(offers) -> CombineOffersResponse`
- `view_offer(offer) -> ViewOfferResponse`
- `import_offer(offer) -> ImportOfferResponse`
- `get_offers() -> GetOffersResponse`
- `get_offers_for_asset(asset_id) -> GetOffersForAssetResponse`
- `get_offer(offer_id) -> GetOfferResponse`
- `delete_offer(offer_id) -> DeleteOfferResponse`
- `cancel_offer(offer_id, fee, auto_submit) -> TransactionResponse`
- `cancel_offers(offer_ids, fee, auto_submit) -> TransactionResponse`

Usage notes:

- NFTs and options must use amount `1`
- request-only offers require a fee
- auto-import can persist newly built offers

## Settings and Peers

- `get_peers() -> GetPeersResponse`
- `remove_peer(ip, ban) -> EmptyResponse`
- `add_peer(ip) -> EmptyResponse`
- `set_discover_peers(discover_peers) -> EmptyResponse`
- `set_target_peers(target_peers) -> EmptyResponse`
- `set_network(name) -> EmptyResponse`
- `set_network_override(fingerprint, name) -> EmptyResponse`
- `get_networks() -> NetworkList`
- `get_network() -> GetNetworkResponse`
- `set_delta_sync(delta_sync) -> EmptyResponse`
- `set_delta_sync_override(fingerprint, delta_sync) -> EmptyResponse`
- `set_change_address(fingerprint, change_address) -> EmptyResponse`

## Metadata / Actions

- `resync_cat(asset_id) -> ResyncCatResponse`
- `update_cat(record) -> UpdateCatResponse`
- `update_option(option_id, visible) -> UpdateOptionResponse`
- `update_did(did_id, name, visible) -> UpdateDidResponse`
- `update_nft(nft_id, visible) -> UpdateNftResponse`
- `update_nft_collection(collection_id, visible) -> UpdateNftCollectionResponse`
- `redownload_nft(nft_id) -> RedownloadNftResponse`
- `increase_derivation_index(hardened, unhardened, index) -> IncreaseDerivationIndexResponse`

## Action-System Builder

- `create_transaction(selected_coin_ids, actions, auto_submit) -> TransactionResponse`

Action variants:

- `Send`
- `MintNft`
- `UpdateNft`
- `Fee`

## Theme Endpoints

- `delete_user_theme(nft_id) -> DeleteUserThemeResponse`
- `get_user_theme(nft_id) -> GetUserThemeResponse`
- `save_user_theme(nft_id) -> SaveUserThemeResponse`
- `get_user_themes() -> GetUserThemesResponse`

## WalletConnect Endpoints

- `filter_unlocked_coins(coin_ids) -> FilterUnlockedCoinsResponse`
- `get_asset_coins(kind, asset_id, included_locked, offset, limit) -> Vec<SpendableCoin>`
- `sign_message_with_public_key(message, public_key) -> SignMessageWithPublicKeyResponse`
- `sign_message_by_address(message, address) -> SignMessageByAddressResponse`
- `send_transaction_immediately(spend_bundle) -> SendTransactionImmediatelyResponse`

## Parsing and Format Rules

- CAT asset id: 32-byte hex
- coin id: 32-byte hex, usually lowercase `0x` supported
- DID id: `did:chia:...`
- NFT id: `nft...`
- option id: `option...`
- collection id: `col...`
- offer id: 32-byte hex
- amount must fit into `u64`
- memos are hex-encoded bytes
- public key: 48-byte hex
- signature: 96-byte hex
- signature message:
  - hex-looking strings decode to bytes
  - non-hex strings are treated as text bytes
