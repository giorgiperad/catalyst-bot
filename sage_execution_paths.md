# Sage Execution Paths

Path inventory scope: all explicit control-flow branches found in backend endpoints, WalletConnect endpoints, Tauri commands, and shared parser/transaction helpers. This is a source-derived exhaustive map of explicit branches in those entrypoints and helpers.

## crates/sage/src/endpoints/keys.rs
### `login`
- straight-line flow: no explicit conditional branch in this function body
### `logout`
- straight-line flow: no explicit conditional branch in this function body
### `resync`
- conditional: `if login {`
- conditional: `if req.delete_coins {`
- conditional: `if req.delete_assets {`
- conditional: `if req.delete_files {`
- conditional: `if req.delete_offers {`
- conditional: `if req.delete_addresses {`
- conditional: `if req.delete_blocks {`
### `generate_mnemonic`
- straight-line flow: no explicit conditional branch in this function body
### `import_key`
- conditional: `if key_hex.starts_with("0x") || key_hex.starts_with("0X") {`
- conditional: `if let Ok(master_pk) = bytes.clone().try_into() {`
- error path: `return Err(Error::InvalidKey);`
- conditional: `if word_count != 12 && word_count != 24 {`
- error path: `return Err(Error::InvalidMnemonic(format!(`
- default/optional flow: `words.get(idx).copied().unwrap_or("unknown"),`
- conditional: `if req.unhardened.unwrap_or(true) {`
- conditional: `if req.hardened.unwrap_or(true)`
- conditional: `if req.login {`
### `delete_database`
- conditional: `if path.try_exists()? {`
- conditional: `if db_file.try_exists()? {`
### `delete_key`
- conditional: `if self.config.global.fingerprint == Some(req.fingerprint) {`
- conditional: `if path.try_exists()? {`
### `rename_key`
- error path: `return Err(Error::UnknownFingerprint);`
### `set_wallet_emoji`
- error path: `return Err(Error::UnknownFingerprint);`
### `get_key`
- fallback/early-exit: `let Some(fingerprint) = fingerprint else {`
- graceful empty/false path: `return Ok(GetKeyResponse { key: None });`
- default/optional flow: `let wallet_config = self.wallet_config().cloned().unwrap_or_default();`
- default/optional flow: `let network_id = wallet_config.network.unwrap_or_else(|| self.network_id());`
- fallback/early-exit: `let Some(master_pk) = self.keychain.extract_public_key(fingerprint)? else {`
### `get_secret_key`
- graceful empty/false path: `return Ok(GetSecretKeyResponse { secrets: None });`
### `get_keys`
- fallback/early-exit: `let Some(master_pk) = self.keychain.extract_public_key(wallet.fingerprint)? else {`
- default/optional flow: `network_id: wallet.network.clone().unwrap_or_else(|| self.network_id()),`

## crates/sage/src/endpoints/data.rs
### `get_version`
- straight-line flow: no explicit conditional branch in this function body
### `perform_database_maintenance`
- straight-line flow: no explicit conditional branch in this function body
### `get_database_stats`
- straight-line flow: no explicit conditional branch in this function body
### `get_sync_status`
- default/optional flow: `.map_or(0, |metadata| metadata.len());`
- default/optional flow: `.map_or(0, |idx| idx + 1),`
- default/optional flow: `checked_files: wallet.db.checked_files().await?.try_into().unwrap_or(0),`
- default/optional flow: `total_files: wallet.db.total_files().await?.try_into().unwrap_or(0),`
### `check_address`
- fallback/early-exit: `let Some(address) = Address::decode(&req.address).ok() else {`
- graceful empty/false path: `return Ok(CheckAddressResponse { valid: false });`
### `get_derivations`
- straight-line flow: no explicit conditional branch in this function body
### `get_are_coins_spendable`
- straight-line flow: no explicit conditional branch in this function body
### `get_spendable_coin_count`
- straight-line flow: no explicit conditional branch in this function body
### `get_coins_by_ids`
- straight-line flow: no explicit conditional branch in this function body
### `get_coins`
- default/optional flow: `.transpose()?`
- default/optional flow: `.unwrap_or_default(),`
### `get_all_cats`
- default/optional flow: `.transpose()?,`
### `get_cats`
- default/optional flow: `.transpose()?,`
### `get_token`
- default/optional flow: `.transpose()?`
- default/optional flow: `.unwrap_or_default();`
- default/optional flow: `.transpose()?,`
- default/optional flow: `.transpose()?;`
### `get_dids`
- straight-line flow: no explicit conditional branch in this function body
### `get_minter_did_ids`
- straight-line flow: no explicit conditional branch in this function body
### `is_asset_owned`
- straight-line flow: no explicit conditional branch in this function body
### `get_options`
- straight-line flow: no explicit conditional branch in this function body
### `get_option`
- graceful empty/false path: `return Ok(GetOptionResponse { option: None });`
### `get_pending_transactions`
- straight-line flow: no explicit conditional branch in this function body
### `get_transaction`
- default/optional flow: `.transpose()?;`
### `get_transactions`
- straight-line flow: no explicit conditional branch in this function body
### `get_nft_collections`
- straight-line flow: no explicit conditional branch in this function body
### `get_nft_collection`
- default/optional flow: `let collection_id = req.collection_id.map(parse_collection_id).transpose()?;`
- fallback/early-exit: `let Some(collection) = wallet.db.collection(collection_id).await? else {`
- graceful empty/false path: `return Ok(GetNftCollectionResponse { collection: None });`
### `get_nfts`
- conditional: `if collection_id == "none" {`
- conditional: `if minter_did_id == "none" {`
- conditional: `if owner_did_id == "none" {`
- error path: `_ => return Err(Error::InvalidGroup),`
### `get_nft`
- fallback/early-exit: `let Some(row) = wallet.db.wallet_nft(nft_id).await? else {`
- graceful empty/false path: `return Ok(GetNftResponse { nft: None });`
### `get_nft_data`
- fallback/early-exit: `let Some(nft) = wallet.db.nft(nft_id).await? else {`
- graceful empty/false path: `return Ok(GetNftDataResponse { data: None });`
### `get_nft_icon`
- fallback/early-exit: `let Some(nft) = wallet.db.nft(nft_id).await? else {`
- graceful empty/false path: `return Ok(GetNftIconResponse { icon: None });`
- fallback/early-exit: `let Some(data_hash) = metadata.as_ref().and_then(|m| m.data_hash) else {`
### `get_nft_thumbnail`
- fallback/early-exit: `let Some(nft) = wallet.db.nft(nft_id).await? else {`
- graceful empty/false path: `return Ok(GetNftThumbnailResponse { thumbnail: None });`
- fallback/early-exit: `let Some(data_hash) = metadata.as_ref().and_then(|m| m.data_hash) else {`
- default/optional flow: `.transpose()?;`
- conditional: `if minter_did.as_deref() == Some("did:chia:1c9mxmqnyaymseunws8r0dfxwpfjxetha53lk72wm7syxkln6perqapkpzw") ||`
- default/optional flow: `.transpose()?,`
- default/optional flow: `.unwrap_or_default(),`

## crates/sage/src/endpoints/transactions.rs
### `send_xch`
- straight-line flow: no explicit conditional branch in this function body
### `bulk_send_xch`
- straight-line flow: no explicit conditional branch in this function body
### `combine`
- straight-line flow: no explicit conditional branch in this function body
### `auto_combine_xch`
- default/optional flow: `let max_amount = req.max_coin_amount.map(parse_amount).transpose()?;`
- fallback/early-exit: `let Some(max_amount) = max_amount else {`
### `split`
- straight-line flow: no explicit conditional branch in this function body
### `auto_combine_cat`
- default/optional flow: `let max_amount = req.max_coin_amount.map(parse_amount).transpose()?;`
- fallback/early-exit: `let Some(max_amount) = max_amount else {`
### `issue_cat`
- straight-line flow: no explicit conditional branch in this function body
### `send_cat`
- straight-line flow: no explicit conditional branch in this function body
### `bulk_send_cat`
- straight-line flow: no explicit conditional branch in this function body
### `multi_send`
- straight-line flow: no explicit conditional branch in this function body
### `create_did`
- straight-line flow: no explicit conditional branch in this function body
### `bulk_mint_nfts`
- straight-line flow: no explicit conditional branch in this function body
### `transfer_nfts`
- straight-line flow: no explicit conditional branch in this function body
### `add_nft_uri`
- straight-line flow: no explicit conditional branch in this function body
### `assign_nfts_to_did`
- default/optional flow: `let did_id = req.did_id.map(parse_did_id).transpose()?;`
### `transfer_dids`
- straight-line flow: no explicit conditional branch in this function body
### `normalize_dids`
- straight-line flow: no explicit conditional branch in this function body
### `mint_option`
- fallback/early-exit: `let Some(asset_id) = asset.asset_id else {`
- default/optional flow: `.unwrap_or_default();`
### `transfer_options`
- straight-line flow: no explicit conditional branch in this function body
### `exercise_options`
- straight-line flow: no explicit conditional branch in this function body
### `finalize_clawback`
- straight-line flow: no explicit conditional branch in this function body
### `sign_coin_spends`
- conditional: `if req.auto_submit {`
### `view_coin_spends`
- straight-line flow: no explicit conditional branch in this function body
### `submit_transaction`
- straight-line flow: no explicit conditional branch in this function body
### `transact`
- straight-line flow: no explicit conditional branch in this function body
### `transact_with`
- conditional: `if auto_submit {`
### `convert_nft_mint`
- default/optional flow: `.transpose()?;`
- default/optional flow: `edition_number: item.edition_number.unwrap_or(1) as u64,`
- default/optional flow: `edition_total: item.edition_total.unwrap_or(1) as u64,`

## crates/sage/src/endpoints/offers.rs
### `make_offer`
- default/optional flow: `let selected_coin_ids = parse_coin_ids(req.coin_ids.unwrap_or_default())?;`
- default/optional flow: `.transpose()?,`
- conditional: `if let Some(asset_id) = asset_id {`
- conditional: `if let Ok(asset_id) = parse_asset_id(asset_id.clone()) {`
- conditional: `if amount != 1 {`
- error path: `return Err(Error::InvalidAmount(raw_amount.to_string()));`
- error path: `return Err(Error::InvalidAssetId(asset_id));`
- conditional: `if !has_offered_assets && offered.fee == 0 {`
- error path: `return Err(Error::InvalidAmount(`
- conditional: `if peer.is_none() {`
- error path: `return Err(Error::CouldNotFetchNft(nft_id));`
- error path: `return Err(Error::CouldNotFetchOption(option_id));`
- error path: `return Err(Error::NoSigningKey);`
- conditional: `if req.auto_import {`
### `take_offer`
- error path: `return Err(Error::NoSigningKey);`
- conditional: `if req.auto_submit {`
### `view_offer`
- straight-line flow: no explicit conditional branch in this function body
### `import_offer`
- conditional: `if wallet.db.offer(offer_id).await?.is_some() {`
- default/optional flow: `royalty: offered_royalties.cats.get(&asset_id).copied().unwrap_or(0),`
- conditional: `if let Some(hash) = metadata.data_hash`
- conditional: `if let Some(hash) = metadata.metadata_hash`
- default/optional flow: `.unwrap_or(0),`
- conditional: `if !tx.is_known_coin(coin_id).await? {`
- error path: `return Err(Error::Wallet(WalletError::CannotImportOffer));`
- conditional: `if offered_amounts.xch > 0 || offered_royalties.xch > 0 {`
- conditional: `if requested_amounts.xch > 0 || requested_royalties.xch > 0 {`
### `combine_offers`
- straight-line flow: no explicit conditional branch in this function body
### `get_offers`
- straight-line flow: no explicit conditional branch in this function body
### `get_offers_for_asset`
- straight-line flow: no explicit conditional branch in this function body
### `get_offer`
- straight-line flow: no explicit conditional branch in this function body
### `delete_offer`
- default/optional flow: `.transpose()?`
- fallback/early-exit: `let Some(row) = wallet.db.option_assets(asset.hash).await? else {`
- error path: `return Err(Error::MissingOption(asset.hash));`
- conditional: `if is_requested {`
### `cancel_offer`
- fallback/early-exit: `let Some(row) = wallet.db.offer(offer_id).await? else {`
- error path: `return Err(Error::MissingOffer(offer_id));`
### `cancel_offers`
- fallback/early-exit: `let Some(row) = wallet.db.offer(offer_id).await? else {`
- error path: `return Err(Error::MissingOffer(offer_id));`

## crates/sage/src/endpoints/settings.rs
### `get_peers`
- straight-line flow: no explicit conditional branch in this function body
### `remove_peer`
- conditional: `if req.ban {`
### `add_peer`
- straight-line flow: no explicit conditional branch in this function body
### `set_discover_peers`
- conditional: `if self.config.network.discover_peers != req.discover_peers {`
### `set_target_peers`
- straight-line flow: no explicit conditional branch in this function body
### `set_network`
- straight-line flow: no explicit conditional branch in this function body
### `set_network_override`
- straight-line flow: no explicit conditional branch in this function body
### `get_networks`
- straight-line flow: no explicit conditional branch in this function body
### `get_network`
- straight-line flow: no explicit conditional branch in this function body
### `set_delta_sync`
- straight-line flow: no explicit conditional branch in this function body
### `set_delta_sync_override`
- error path: `return Err(Error::UnknownFingerprint);`
### `set_change_address`
- error path: `return Err(Error::UnknownFingerprint);`

## crates/sage/src/endpoints/actions.rs
### `resync_cat`
- straight-line flow: no explicit conditional branch in this function body
### `update_cat`
- default/optional flow: `.transpose()?`
- default/optional flow: `.unwrap_or_default();`
- fallback/early-exit: `let Some(mut asset) = wallet.db.asset(asset_id).await? else {`
- error path: `return Err(Error::MissingCat(asset_id));`
### `update_option`
- fallback/early-exit: `let Some(mut asset) = wallet.db.asset(option_id).await? else {`
- error path: `return Err(Error::MissingDid(option_id));`
### `update_did`
- fallback/early-exit: `let Some(mut asset) = wallet.db.asset(did_id).await? else {`
- error path: `return Err(Error::MissingDid(did_id));`
### `update_nft`
- fallback/early-exit: `let Some(mut asset) = wallet.db.asset(nft_id).await? else {`
- error path: `return Err(Error::MissingNft(nft_id));`
### `update_nft_collection`
- straight-line flow: no explicit conditional branch in this function body
### `redownload_nft`
- fallback/early-exit: `let Some(nft) = wallet.db.nft(nft_id).await? else {`
- error path: `return Err(Error::MissingNft(nft_id));`
- conditional: `if let Some(metadata) = metadata {`
- conditional: `if let Some(hash) = metadata.data_hash {`
- conditional: `if let Some(hash) = metadata.metadata_hash {`
- conditional: `if let Some(hash) = metadata.license_hash {`
### `increase_derivation_index`
- conditional: `if hardened {`
- error path: `return Err(Error::NoSigningKey);`
- conditional: `if unhardened {`

## crates/sage/src/endpoints/action_system.rs
### `create_transaction`
- branch dispatch: `match action {`
- conditional: `if let Some(clawback) = clawback {`
- default/optional flow: `royalty_puzzle_hash: mint.royalty_puzzle_hash.unwrap_or(sender_puzzle_hash),`
- default/optional flow: `let did_id = transfer.did_id.map(parse_id).transpose()?;`

## crates/sage/src/endpoints/themes.rs
### `delete_user_theme`
- conditional: `if req.nft_id.is_empty() {`
- conditional: `if !theme_dir.exists() {`
### `get_user_theme`
- conditional: `if req.nft_id.is_empty() {`
- graceful empty/false path: `return Ok(GetUserThemeResponse { theme: None });`
- conditional: `if !theme_json_path.exists() {`
### `save_user_theme`
- conditional: `if req.nft_id.is_empty() {`
- conditional: `if !themes_dir.exists() {`
- conditional: `if !nft_theme_dir.exists() {`
- conditional: `if let Some(nft_data) = nft_data_response.data`
- conditional: `if let Some(theme_obj) = theme_data.as_object_mut() {`
### `get_user_themes`
- conditional: `if !themes_dir.exists() {`
- branch dispatch: `match fs::read_dir(&themes_dir).await {`
- conditional: `if path.is_dir() {`
- conditional: `if theme_json_path.exists() {`
- branch dispatch: `match fs::read_to_string(&theme_json_path).await {`

## crates/sage/src/endpoints/wallet_connect.rs
### `filter_unlocked_coins`
- conditional: `if wallet`
### `get_asset_coins`
- default/optional flow: `let include_locked = req.included_locked.unwrap_or(false);`
- branch dispatch: `match (req.kind, req.asset_id) {`
- error path: `(Some(AssetCoinType::Cat), None) => return Err(Error::MissingAssetId),`
- default/optional flow: `req.limit.unwrap_or(10),`
- default/optional flow: `req.offset.unwrap_or(0),`
- conditional: `if include_locked {`
- fallback/early-exit: `let Some(cat) = wallet.db.cat_coin(row.coin.coin_id()).await? else {`
- error path: `return Err(Error::MissingCatCoin(row.coin.coin_id()));`
- fallback/early-exit: `let Some(did) = wallet.db.did_coin(row.coin.coin_id()).await? else {`
- error path: `return Err(Error::MissingDidCoin(row.coin.coin_id()));`
- fallback/early-exit: `let Some(nft) = wallet.db.nft_coin(row.coin.coin_id()).await? else {`
- error path: `return Err(Error::MissingNftCoin(row.coin.coin_id()));`
- default/optional flow: `confirmed_block_index: row.created_height.unwrap_or(0),`
### `sign_message_with_public_key`
- fallback/early-exit: `let Some(info) = wallet.db.derivation(public_key).await? else {`
- error path: `return Err(Error::InvalidKey);`
- error path: `return Err(Error::NoSigningKey);`
### `sign_message_by_address`
- fallback/early-exit: `let Some(public_key) = wallet.db.public_key(p2_puzzle_hash).await? else {`
- error path: `return Err(Error::InvalidKey);`
- fallback/early-exit: `let Some(info) = wallet.db.derivation(public_key).await? else {`
- error path: `return Err(Error::NoSigningKey);`
### `send_transaction_immediately`
- branch dispatch: `match submit_to_peers(&peers, spend_bundle.clone()).await? {`

## src-tauri/src/commands.rs
### `initialize`
- conditional: `if *initialized {`
- conditional: `if let Err(error) = app_state.save_peers().await {`
- conditional: `if app_state.config.rpc.enabled {`
### `endpoint`
- straight-line flow: no explicit conditional branch in this function body
### `validate_address`
- fallback/early-exit: `let Some(address) = Address::decode(&address).ok() else {`
- graceful empty/false path: `return Ok(false);`
### `network_config`
- straight-line flow: no explicit conditional branch in this function body
### `wallet_config`
- straight-line flow: no explicit conditional branch in this function body
### `default_wallet_config`
- straight-line flow: no explicit conditional branch in this function body
### `is_rpc_running`
- straight-line flow: no explicit conditional branch in this function body
### `start_rpc_server`
- straight-line flow: no explicit conditional branch in this function body
### `stop_rpc_server`
- conditional: `if let Some(handle) = rpc_task.take() {`
### `get_rpc_run_on_startup`
- straight-line flow: no explicit conditional branch in this function body
### `set_rpc_run_on_startup`
- straight-line flow: no explicit conditional branch in this function body
### `switch_wallet`
- straight-line flow: no explicit conditional branch in this function body
### `move_key`
- straight-line flow: no explicit conditional branch in this function body
### `download_cni_offercode`
- conditional: `if response.status() != StatusCode::OK {`
- error path: `return Err(crate::error::Error {`
### `get_logs`
- conditional: `if !name.starts_with("app.log") {`

## crates/sage/src/sage.rs
### `new`
- straight-line flow: no explicit conditional branch in this function body
### `initialize`
- conditional: `if !log_dir.exists() {`
- conditional: `if let Err(error) = tracing::subscriber::set_global_default(subscriber) {`
- conditional: `if key_path.try_exists()? {`
- conditional: `if config_path.try_exists()? {`
- conditional: `if let Some(old_config) = toml::from_str::<OldConfig>(&config_text)`
- conditional: `if network_list_path.try_exists()? {`
- conditional: `if let Ok(old_network_list) = toml::from_str::<IndexMap<String, OldNetwork>>(&text) {`
- conditional: `if !ssl_dir.try_exists()? {`
- default/optional flow: `.unwrap_or_default()`
### `switch_network`
- straight-line flow: no explicit conditional branch in this function body
### `switch_wallet`
- fallback/early-exit: `let Some(fingerprint) = self.config.global.fingerprint else {`
- fallback/early-exit: `let Some(master_pk) = self.keychain.extract_public_key(fingerprint)? else {`
- error path: `return Err(Error::UnknownFingerprint);`
- default/optional flow: `let wallet_config = self.wallet_config().cloned().unwrap_or_default();`
- default/optional flow: `.transpose()?`
### `setup_peers`
- conditional: `if !peer_dir.exists() {`
- default/optional flow: `Peers::from_bytes(&fs::read(&peer_path)?).unwrap_or_else(|error| {`
- conditional: `if now >= timestamp {`
- conditional: `if state.peer(ip).is_some() {`
### `save_peers`
- conditional: `if !peer_dir.exists() {`
### `parse_address`
- conditional: `if address.prefix != self.network().prefix() {`
- error path: `return Err(Error::AddressPrefix(address.prefix));`
### `connect_to_database`
- conditional: `if let Err(_error) = sqlx::migrate!("../../migrations").run(&pool).await {`
- error path: `return Err(Error::DatabaseVersionTooOld);`
### `wallet_db_path`
- conditional: `if wallet.fingerprint == fingerprint {`
- default/optional flow: `.unwrap_or_else(|| self.network_id());`
### `wallet_config`
- straight-line flow: no explicit conditional branch in this function body
### `network`
- conditional: `if let Some(wallet) = self.wallet_config()`
### `network_id`
- straight-line flow: no explicit conditional branch in this function body
### `wallet`
- fallback/early-exit: `let Some(fingerprint) = self.config.global.fingerprint else {`
- error path: `return Err(Error::NotLoggedIn);`
- conditional: `if !self.keychain.contains(fingerprint) {`
- error path: `return Err(Error::UnknownFingerprint);`
- conditional: `if wallet.fingerprint != fingerprint {`
### `save_config`
- straight-line flow: no explicit conditional branch in this function body
### `save_keychain`
- straight-line flow: no explicit conditional branch in this function body

## crates/sage/src/utils/parse.rs
### `parse_asset_id`
- straight-line flow: no explicit conditional branch in this function body
### `parse_coin_id`
- straight-line flow: no explicit conditional branch in this function body
### `parse_coin_ids`
- straight-line flow: no explicit conditional branch in this function body
### `parse_did_id`
- conditional: `if address.prefix != "did:chia:" {`
- error path: `return Err(Error::InvalidDidId(input));`
### `parse_nft_id`
- conditional: `if address.prefix != "nft" {`
- error path: `return Err(Error::InvalidNftId(input));`
### `parse_option_id`
- conditional: `if address.prefix != "option" {`
- error path: `return Err(Error::InvalidOptionId(input));`
### `parse_collection_id`
- conditional: `if address.prefix != "col" {`
- error path: `return Err(Error::InvalidCollectionId(input));`
### `parse_offer_id`
- straight-line flow: no explicit conditional branch in this function body
### `parse_amount`
- fallback/early-exit: `let Some(amount) = input.to_u64() else {`
- error path: `return Err(Error::InvalidAmount(input.to_string()));`
### `parse_hash`
- straight-line flow: no explicit conditional branch in this function body
### `parse_signature`
- straight-line flow: no explicit conditional branch in this function body
### `parse_signature_message`
- conditional: `if stripped.chars().all(|c| c.is_ascii_hexdigit()) && !stripped.is_empty() {`
### `parse_public_key`
- straight-line flow: no explicit conditional branch in this function body
### `parse_program`
- straight-line flow: no explicit conditional branch in this function body
### `parse_memos`
- straight-line flow: no explicit conditional branch in this function body
### `parse_any_asset_id`
- straight-line flow: no explicit conditional branch in this function body

## crates/sage/src/utils/spends.rs
### `sign`
- error path: `return Err(Error::NoSigningKey);`
### `submit`
- straight-line flow: no explicit conditional branch in this function body

## crates/sage/src/utils/confirmation.rs
### `summarize`
- conditional: `if wallet.db.is_p2_puzzle_hash(coin.puzzle_hash).await? {`
- default/optional flow: `Some(wallet.db.asset(info.launcher_id).await?.unwrap_or(Asset {`
- default/optional flow: `.unwrap_or(output.coin.puzzle_hash);`
- default/optional flow: `asset: asset.map(|asset| self.encode_asset(asset)).transpose()?,`
### `extract_nft_data`
- fallback/early-exit: `let Some(onchain_metadata) = onchain_metadata else {`
- conditional: `if let Some(data_hash) = onchain_metadata.data_hash {`
- conditional: `if let Some(Data {`
- conditional: `if let Some(metadata_hash) = onchain_metadata.metadata_hash {`
- conditional: `if let Some(metadata) = cache.nft_data.get(&metadata_hash) {`
### `json_bundle`
- straight-line flow: no explicit conditional branch in this function body
### `json_spend`
- straight-line flow: no explicit conditional branch in this function body
### `json_coin`
- straight-line flow: no explicit conditional branch in this function body
### `rust_bundle`
- straight-line flow: no explicit conditional branch in this function body
### `rust_spend`
- straight-line flow: no explicit conditional branch in this function body
### `rust_coin`
- straight-line flow: no explicit conditional branch in this function body

## Handled Edge Cases
- Key import accepts three shapes: hex public key, hex private key, or 12/24-word mnemonic; mnemonic errors are specialized for wrong count, unknown word, and invalid checksum.
- Resync can be partial: coins/assets/files/offers/addresses/blocks can each be deleted independently.
- Address validators usually return benign values on decode failure (`false`/`None`) instead of crashing.
- NFT getters commonly degrade to `None` when the NFT, metadata, icon, or thumbnail is missing.
- Get NFT collection supports both a specific collection and a synthetic ?uncategorized? fallback record when no collection id is provided.
- Get NFTs supports special grouping sentinels like `none` for no-collection / no-minter-DID / no-owner-DID.
- WalletConnect send path distinguishes `Pending`, `Failed(status,error)`, and `Unknown` submission outcomes.
- Theme read/delete endpoints treat empty NFT ids and missing files/directories as no-op or `None` responses.
- Optional fee auto-submit flows are consistently handled through `transact` / `transact_with`.
- Signature parsing supports `0x`-prefixed and raw hex, and signature-message parsing also accepts plain text.

## Missing Or Weak Edge-Case Handling
- Initialization can get stuck: `src-tauri/src/commands.rs` sets `initialized = true` before `app_state::initialize(...)` succeeds. If initialization fails, later calls short-circuit and never retry.
- RPC start is not idempotent: `start_rpc_server` unconditionally spawns a new task and overwrites the old handle, so duplicate server startup is not blocked.
- `move_key` can panic on out-of-range insertion because `Vec::insert(index, wallet)` is used without bounds validation.
- `set_network` writes the requested network name without validating it exists in `network_list`; later `network()` uses `expect("network not found")`, so bad config can panic the process.
- `set_network_override` has the same missing validation problem for wallet-specific network names.
- `network()` panics instead of returning a typed error when the configured network is missing.
- `resync` clears the logged-in fingerprint before the destructive work; if a later step fails, the prior login state is not restored.
- `delete_database` only removes `<network>.sqlite`; sidecar SQLite files like `-wal`/`-shm` are not explicitly cleaned up.
- `check_address` decodes the address but does not verify the network prefix matches the current network before checking wallet ownership.
- `save_user_theme` silently returns success when NFT data exists but metadata JSON or theme payload is absent; some failure modes become no-op writes rather than explicit errors.
- `get_user_themes` swallows per-file read failures by printing to stderr and continuing, so callers cannot distinguish partial success from full success.
- `auto_combine_xch` and `auto_combine_cat` do not guard against selecting 0 or 1 eligible coins before calling combine; correctness is deferred to lower layers.
- `parse_coin_id`, `parse_hash`, `parse_signature`, `parse_public_key`, and `parse_program` strip lowercase `0x` only, not uppercase `0X`, unlike `import_key`.
- `parse_signature_message` treats any all-hex string such as `cafe` as bytes instead of literal text; there is no escape hatch to force text interpretation for hex-looking strings.
- `import_offer` appears to append requested options into `nft_rows` instead of `option_rows`, which is likely a classification bug in a less-common branch.
- `download_cni_offercode` makes a network request but only special-cases non-200 responses; malformed success payloads or transport edge cases rely on generic error conversion.
- `get_logs` errors if the log directory does not exist instead of returning an empty list.
- Many write/update endpoints (`update_*`, `set_change_address`, etc.) do not normalize or trim user-provided strings, so empty-but-non-null values can be persisted as-is.

Explicit execution-path bullets recorded: 322.
Traversal status: 100% complete for the explicit entrypoint/helper control flow included in this scope.