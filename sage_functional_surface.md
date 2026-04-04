# Sage Functional Surface

Traversal/API extraction status: 100% complete for on-disk callable surface discovered from Rust `pub fn`/`pub async fn`, Tauri commands, generated endpoint registry, and exported TypeScript functions.

## Summary Counts
- Backend endpoints in `endpoints.json`: 100
- WalletConnect/Tauri-only endpoints in `endpoints-tauri.json`: 5
- Tauri command functions in `src-tauri/src/commands.rs`: 15
- Rust public functions discovered: 506
- Exported TypeScript functions discovered: 210

## Full API / Endpoint List
### `login`
- Callable as: `login`
- Async/RPC behavior: async
- Request type: `Login`
- Response type: `LoginResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `fingerprint: u32` (required) - no inline field comment
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `logout`
- Callable as: `logout`
- Async/RPC behavior: async
- Request type: `Logout`
- Response type: `LogoutResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters: none
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `resync`
- Callable as: `resync`
- Async/RPC behavior: async
- Request type: `Resync`
- Response type: `ResyncResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `fingerprint: u32` (required) - no inline field comment
  - `delete_coins: bool` (optional) - no inline field comment
  - `delete_assets: bool` (optional) - no inline field comment
  - `delete_files: bool` (optional) - no inline field comment
  - `delete_offers: bool` (optional) - no inline field comment
  - `delete_addresses: bool` (optional) - no inline field comment
  - `delete_blocks: bool` (optional) - no inline field comment
- Returns: empty object / unit-style response
- Optional parameters: delete_coins, delete_assets, delete_files, delete_offers, delete_addresses, delete_blocks
- Edge cases / alternative patterns: supports omitted/defaulted fields; performs async wallet/database/network work

### `generate_mnemonic`
- Callable as: `generate_mnemonic`
- Async/RPC behavior: sync
- Request type: `GenerateMnemonic`
- Response type: `GenerateMnemonicResponse`
- Behavioral notes: implementation is straightforward state lookup/update plus validation
- Parameters:
  - `use_24_words: bool` (required) - no inline field comment
- Returns:
  - `mnemonic: String` (present) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: implementation is straightforward state lookup/update plus validation

### `import_key`
- Callable as: `import_key`
- Async/RPC behavior: async
- Request type: `ImportKey`
- Response type: `ImportKeyResponse`
- Behavioral notes: contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `name: String` (required) - Display name for the wallet
  - `key: String` (required) - Mnemonic phrase or private key
  - `derivation_index: u32` (optional) - no inline field comment
  - `hardened: Option<bool>` (optional) - no inline field comment
  - `unhardened: Option<bool>` (optional) - no inline field comment
  - `save_secrets: bool` (optional) - no inline field comment
  - `login: bool` (optional) - no inline field comment
  - `emoji: Option<String>` (optional) - no inline field comment
- Returns:
  - `fingerprint: u32` (present) - no inline field comment
- Optional parameters: derivation_index, hardened, unhardened, save_secrets, login, emoji
- Edge cases / alternative patterns: supports omitted/defaulted fields; contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `delete_key`
- Callable as: `delete_key`
- Async/RPC behavior: sync
- Request type: `DeleteKey`
- Response type: `DeleteKeyResponse`
- Behavioral notes: implementation is straightforward state lookup/update plus validation
- Parameters:
  - `fingerprint: u32` (required) - no inline field comment
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: implementation is straightforward state lookup/update plus validation

### `delete_database`
- Callable as: `delete_database`
- Async/RPC behavior: sync
- Request type: `DeleteDatabase`
- Response type: `DeleteDatabaseResponse`
- Behavioral notes: implementation is straightforward state lookup/update plus validation
- Parameters:
  - `fingerprint: u32` (required) - no inline field comment
  - `network: String` (required) - Network name
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: implementation is straightforward state lookup/update plus validation

### `rename_key`
- Callable as: `rename_key`
- Async/RPC behavior: sync
- Request type: `RenameKey`
- Response type: `RenameKeyResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state
- Parameters:
  - `fingerprint: u32` (required) - no inline field comment
  - `name: String` (required) - New display name
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: returns validation or lookup errors on invalid input/state

### `set_wallet_emoji`
- Callable as: `set_wallet_emoji`
- Async/RPC behavior: sync
- Request type: `SetWalletEmoji`
- Response type: `SetWalletEmojiResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state
- Parameters:
  - `fingerprint: u32` (required) - no inline field comment
  - `emoji: Option<String>` (optional) - no inline field comment
- Returns: empty object / unit-style response
- Optional parameters: emoji
- Edge cases / alternative patterns: supports omitted/defaulted fields; returns validation or lookup errors on invalid input/state

### `get_key`
- Callable as: `get_key`
- Async/RPC behavior: sync
- Request type: `GetKey`
- Response type: `GetKeyResponse`
- Behavioral notes: contains optional/default-path handling
- Parameters:
  - `fingerprint: Option<u32>` (optional) - no inline field comment
- Returns:
  - `key: Option<KeyInfo>` (optional) - no inline field comment
- Optional parameters: fingerprint
- Edge cases / alternative patterns: supports omitted/defaulted fields; contains optional/default-path handling

### `get_secret_key`
- Callable as: `get_secret_key`
- Async/RPC behavior: sync
- Request type: `GetSecretKey`
- Response type: `GetSecretKeyResponse`
- Behavioral notes: implementation is straightforward state lookup/update plus validation
- Parameters:
  - `fingerprint: u32` (required) - no inline field comment
- Returns:
  - `secrets: Option<SecretKeyInfo>` (optional) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: implementation is straightforward state lookup/update plus validation

### `get_keys`
- Callable as: `get_keys`
- Async/RPC behavior: sync
- Request type: `GetKeys`
- Response type: `GetKeysResponse`
- Behavioral notes: contains optional/default-path handling
- Parameters: none
- Returns:
  - `keys: Vec<KeyInfo>` (present) - List of wallet keys
- Optional parameters: none detected
- Edge cases / alternative patterns: contains optional/default-path handling

### `get_sync_status`
- Callable as: `get_sync_status`
- Async/RPC behavior: async
- Request type: `GetSyncStatus`
- Response type: `GetSyncStatusResponse`
- Behavioral notes: contains optional/default-path handling; performs async wallet/database/network work
- Parameters: none
- Returns:
  - `selectable_balance: Amount` (present) - Current wallet selectable balance
  - `unit: Unit` (present) - Unit for balance display
  - `synced_coins: u32` (present) - Number of coins synced
  - `total_coins: u32` (present) - Total coins to sync
  - `receive_address: String` (present) - Current receive address
  - `burn_address: String` (present) - Burn address for the wallet
  - `unhardened_derivation_index: u32` (present) - Unhardened derivation index
  - `hardened_derivation_index: u32` (present) - Hardened derivation index
  - `checked_files: u32` (present) - Number of NFT files checked
  - `total_files: u32` (present) - Total NFT files to check
  - `database_size: u64` (present) - Database size in bytes
- Optional parameters: none detected
- Edge cases / alternative patterns: contains optional/default-path handling; performs async wallet/database/network work

### `get_version`
- Callable as: `get_version`
- Async/RPC behavior: sync
- Request type: `GetVersion`
- Response type: `GetVersionResponse`
- Behavioral notes: implementation is straightforward state lookup/update plus validation
- Parameters: none
- Returns:
  - `version: String` (present) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: implementation is straightforward state lookup/update plus validation

### `get_database_stats`
- Callable as: `get_database_stats`
- Async/RPC behavior: async
- Request type: `GetDatabaseStats`
- Response type: `GetDatabaseStatsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters: none
- Returns:
  - `total_pages: i64` (present) - Total pages in database
  - `free_pages: i64` (present) - Number of free pages
  - `free_percentage: f64` (present) - Percentage of free space
  - `page_size: i64` (present) - Size of each page in bytes
  - `database_size_bytes: i64` (present) - Total database size in bytes
  - `free_space_bytes: i64` (present) - Free space in bytes
  - `wal_pages: i64` (present) - Number of WAL pages
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `perform_database_maintenance`
- Callable as: `perform_database_maintenance`
- Async/RPC behavior: async
- Request type: `PerformDatabaseMaintenance`
- Response type: `PerformDatabaseMaintenanceResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `force_vacuum: bool` (required) - no inline field comment
- Returns:
  - `vacuum_duration_ms: u64` (present) - Time spent vacuuming in milliseconds
  - `analyze_duration_ms: u64` (present) - Time spent analyzing in milliseconds
  - `wal_checkpoint_duration_ms: u64` (present) - Time spent checkpointing WAL in milliseconds
  - `total_duration_ms: u64` (present) - Total maintenance duration in milliseconds
  - `pages_vacuumed: i64` (present) - Number of pages reclaimed by vacuum
  - `wal_pages_checkpointed: i64` (present) - Number of WAL pages checkpointed
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `check_address`
- Callable as: `check_address`
- Async/RPC behavior: async
- Request type: `CheckAddress`
- Response type: `CheckAddressResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `address: String` (required) - no inline field comment
- Returns:
  - `valid: bool` (present) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_derivations`
- Callable as: `get_derivations`
- Async/RPC behavior: async
- Request type: `GetDerivations`
- Response type: `GetDerivationsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `hardened: bool` (optional) - no inline field comment
  - `offset: u32` (required) - no inline field comment
  - `limit: u32` (required) - no inline field comment
- Returns:
  - `derivations: Vec<DerivationRecord>` (present) - List of address derivations
  - `total: u32` (present) - Total number of derivations available
- Optional parameters: hardened
- Edge cases / alternative patterns: supports omitted/defaulted fields; performs async wallet/database/network work

### `get_are_coins_spendable`
- Callable as: `get_are_coins_spendable`
- Async/RPC behavior: async
- Request type: `GetAreCoinsSpendable`
- Response type: `GetAreCoinsSpendableResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `coin_ids: Vec<String>` (required) - List of coin IDs to check
- Returns:
  - `spendable: bool` (present) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_spendable_coin_count`
- Callable as: `get_spendable_coin_count`
- Async/RPC behavior: async
- Request type: `GetSpendableCoinCount`
- Response type: `GetSpendableCoinCountResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `asset_id: Option<String>` (optional) - no inline field comment
- Returns:
  - `count: u32` (present) - Number of spendable coins
- Optional parameters: asset_id
- Edge cases / alternative patterns: supports omitted/defaulted fields; performs async wallet/database/network work

### `get_coins_by_ids`
- Callable as: `get_coins_by_ids`
- Async/RPC behavior: async
- Request type: `GetCoinsByIds`
- Response type: `GetCoinsByIdsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `coin_ids: Vec<String>` (required) - List of coin IDs to retrieve
- Returns:
  - `coins: Vec<CoinRecord>` (present) - List of coins matching the requested IDs
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_coins`
- Callable as: `get_coins`
- Async/RPC behavior: async
- Request type: `GetCoins`
- Response type: `GetCoinsResponse`
- Behavioral notes: contains optional/default-path handling; performs async wallet/database/network work
- Parameters:
  - `asset_id: Option<String>` (optional) - no inline field comment
  - `offset: u32` (required) - no inline field comment
  - `limit: u32` (required) - no inline field comment
  - `sort_mode: CoinSortMode` (optional) - no inline field comment
  - `filter_mode: CoinFilterMode` (optional) - no inline field comment
  - `ascending: bool` (optional) - no inline field comment
- Returns:
  - `coins: Vec<CoinRecord>` (present) - List of coins
  - `total: u32` (present) - Total number of coins available
- Optional parameters: asset_id, sort_mode, filter_mode, ascending
- Edge cases / alternative patterns: supports omitted/defaulted fields; contains optional/default-path handling; performs async wallet/database/network work

### `get_cats`
- Callable as: `get_cats`
- Async/RPC behavior: async
- Request type: `GetCats`
- Response type: `GetCatsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters: none
- Returns:
  - `cats: Vec<TokenRecord>` (present) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_all_cats`
- Callable as: `get_all_cats`
- Async/RPC behavior: async
- Request type: `GetAllCats`
- Response type: `GetAllCatsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters: none
- Returns:
  - `cats: Vec<TokenRecord>` (present) - List of all CAT tokens
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_token`
- Callable as: `get_token`
- Async/RPC behavior: async
- Request type: `GetToken`
- Response type: `GetTokenResponse`
- Behavioral notes: contains optional/default-path handling; performs async wallet/database/network work
- Parameters:
  - `asset_id: Option<String>` (optional) - no inline field comment
- Returns:
  - `token: Option<TokenRecord>` (optional) - no inline field comment
- Optional parameters: asset_id
- Edge cases / alternative patterns: supports omitted/defaulted fields; contains optional/default-path handling; performs async wallet/database/network work

### `get_dids`
- Callable as: `get_dids`
- Async/RPC behavior: async
- Request type: `GetDids`
- Response type: `GetDidsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters: none
- Returns:
  - `dids: Vec<DidRecord>` (present) - List of DIDs
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_minter_did_ids`
- Callable as: `get_minter_did_ids`
- Async/RPC behavior: async
- Request type: `GetMinterDidIds`
- Response type: `GetMinterDidIdsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `offset: u32` (required) - no inline field comment
  - `limit: u32` (required) - no inline field comment
- Returns:
  - `did_ids: Vec<String>` (present) - List of minter DID IDs
  - `total: u32` (present) - Total number of minter DIDs
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_options`
- Callable as: `get_options`
- Async/RPC behavior: async
- Request type: `GetOptions`
- Response type: `GetOptionsResponse`
- Behavioral notes: contains optional/default-path handling; performs async wallet/database/network work
- Parameters:
  - `offset: u32` (required) - no inline field comment
  - `limit: u32` (required) - no inline field comment
  - `sort_mode: OptionSortMode` (optional) - no inline field comment
  - `ascending: bool` (optional) - no inline field comment
  - `find_value: Option<String>` (optional) - no inline field comment
  - `include_hidden: bool` (optional) - no inline field comment
- Returns:
  - `options: Vec<OptionRecord>` (present) - List of options
  - `total: u32` (present) - Total number of options
- Optional parameters: sort_mode, ascending, find_value, include_hidden
- Edge cases / alternative patterns: supports omitted/defaulted fields; contains optional/default-path handling; performs async wallet/database/network work

### `get_option`
- Callable as: `get_option`
- Async/RPC behavior: async
- Request type: `GetOption`
- Response type: `GetOptionResponse`
- Behavioral notes: contains optional/default-path handling; performs async wallet/database/network work
- Parameters:
  - `option_id: String` (required) - Option ID
- Returns:
  - `option: Option<OptionRecord>` (optional) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: contains optional/default-path handling; performs async wallet/database/network work

### `get_pending_transactions`
- Callable as: `get_pending_transactions`
- Async/RPC behavior: async
- Request type: `GetPendingTransactions`
- Response type: `GetPendingTransactionsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters: none
- Returns:
  - `transactions: Vec<PendingTransactionRecord>` (present) - List of pending transactions
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_transaction`
- Callable as: `get_transaction`
- Async/RPC behavior: async
- Request type: `GetTransaction`
- Response type: `GetTransactionResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `height: u32` (required) - Transaction height/ID
- Returns:
  - `transaction: Option<TransactionRecord>` (optional) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_transactions`
- Callable as: `get_transactions`
- Async/RPC behavior: async
- Request type: `GetTransactions`
- Response type: `GetTransactionsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `offset: u32` (required) - no inline field comment
  - `limit: u32` (required) - no inline field comment
  - `ascending: bool` (required) - no inline field comment
  - `find_value: Option<String>` (optional) - no inline field comment
- Returns:
  - `transactions: Vec<TransactionRecord>` (present) - List of transactions
  - `total: u32` (present) - Total number of transactions
- Optional parameters: find_value
- Edge cases / alternative patterns: supports omitted/defaulted fields; performs async wallet/database/network work

### `get_nft_collections`
- Callable as: `get_nft_collections`
- Async/RPC behavior: async
- Request type: `GetNftCollections`
- Response type: `GetNftCollectionsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `offset: u32` (required) - no inline field comment
  - `limit: u32` (required) - no inline field comment
  - `include_hidden: bool` (required) - no inline field comment
- Returns:
  - `collections: Vec<NftCollectionRecord>` (present) - List of NFT collections
  - `total: u32` (present) - Total number of collections
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_nft_collection`
- Callable as: `get_nft_collection`
- Async/RPC behavior: async
- Request type: `GetNftCollection`
- Response type: `GetNftCollectionResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `collection_id: Option<String>` (optional) - no inline field comment
- Returns:
  - `collection: Option<NftCollectionRecord>` (optional) - no inline field comment
- Optional parameters: collection_id
- Edge cases / alternative patterns: supports omitted/defaulted fields; performs async wallet/database/network work

### `get_nfts`
- Callable as: `get_nfts`
- Async/RPC behavior: async
- Request type: `GetNfts`
- Response type: `GetNftsResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `collection_id: Option<String>` (optional) - no inline field comment
  - `minter_did_id: Option<String>` (optional) - no inline field comment
  - `owner_did_id: Option<String>` (optional) - no inline field comment
  - `name: Option<String>` (optional) - no inline field comment
  - `offset: u32` (required) - no inline field comment
  - `limit: u32` (required) - no inline field comment
  - `sort_mode: NftSortMode` (required) - Sort mode
  - `include_hidden: bool` (required) - no inline field comment
- Returns:
  - `nfts: Vec<NftRecord>` (present) - List of NFTs
  - `total: u32` (present) - Total number of NFTs
- Optional parameters: collection_id, minter_did_id, owner_did_id, name
- Edge cases / alternative patterns: supports omitted/defaulted fields; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `get_nft`
- Callable as: `get_nft`
- Async/RPC behavior: async
- Request type: `GetNft`
- Response type: `GetNftResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `nft_id: String` (required) - NFT coin ID
- Returns:
  - `nft: Option<NftRecord>` (optional) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_nft_icon`
- Callable as: `get_nft_icon`
- Async/RPC behavior: async
- Request type: `GetNftIcon`
- Response type: `GetNftIconResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `nft_id: String` (required) - NFT coin ID
- Returns:
  - `icon: Option<String>` (optional) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_nft_thumbnail`
- Callable as: `get_nft_thumbnail`
- Async/RPC behavior: async
- Request type: `GetNftThumbnail`
- Response type: `GetNftThumbnailResponse`
- Behavioral notes: contains optional/default-path handling; performs async wallet/database/network work
- Parameters:
  - `nft_id: String` (required) - NFT coin ID
- Returns:
  - `thumbnail: Option<String>` (optional) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: contains optional/default-path handling; performs async wallet/database/network work

### `get_nft_data`
- Callable as: `get_nft_data`
- Async/RPC behavior: async
- Request type: `GetNftData`
- Response type: `GetNftDataResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `nft_id: String` (required) - NFT coin ID
- Returns:
  - `data: Option<NftData>` (optional) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `send_xch`
- Callable as: `send_xch`
- Async/RPC behavior: async
- Request type: `SendXch`
- Response type: `SendXchResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `address: String` (required) - no inline field comment
  - `amount: Amount` (required) - Amount to send
  - `fee: Amount` (required) - Transaction fee
  - `memos: Vec<String>` (optional) - no inline field comment
  - `clawback: Option<u64>` (optional) - no inline field comment
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: memos, clawback, auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `bulk_send_xch`
- Callable as: `bulk_send_xch`
- Async/RPC behavior: async
- Request type: `BulkSendXch`
- Response type: `BulkSendXchResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `addresses: Vec<String>` (required) - List of recipient addresses
  - `amount: Amount` (required) - Amount to send to each address
  - `fee: Amount` (required) - Transaction fee
  - `memos: Vec<String>` (optional) - no inline field comment
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: memos, auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `combine`
- Callable as: `combine`
- Async/RPC behavior: async
- Request type: `Combine`
- Response type: `CombineResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `coin_ids: Vec<String>` (required) - Coin IDs to combine
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `split`
- Callable as: `split`
- Async/RPC behavior: async
- Request type: `Split`
- Response type: `SplitResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `coin_ids: Vec<String>` (required) - Coin IDs to split
  - `output_count: u32` (required) - Number of output coins
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `auto_combine_xch`
- Callable as: `auto_combine_xch`
- Async/RPC behavior: async
- Request type: `AutoCombineXch`
- Response type: `AutoCombineXchResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `max_coins: u32` (required) - Maximum number of coins to combine
  - `max_coin_amount: Option<Amount>` (optional) - no inline field comment
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns:
  - `coin_ids: Vec<String>` (present) - Combined coin IDs
  - `summary: TransactionSummary` (present) - Transaction summary
  - `coin_spends: Vec<CoinSpendJson>` (present) - Coin spends in the transaction
- Optional parameters: max_coin_amount, auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `auto_combine_cat`
- Callable as: `auto_combine_cat`
- Async/RPC behavior: async
- Request type: `AutoCombineCat`
- Response type: `AutoCombineCatResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `asset_id: String` (required) - Asset ID of the CAT
  - `max_coins: u32` (required) - Maximum number of coins to combine
  - `max_coin_amount: Option<Amount>` (optional) - no inline field comment
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns:
  - `coin_ids: Vec<String>` (present) - Combined coin IDs
  - `summary: TransactionSummary` (present) - Transaction summary
  - `coin_spends: Vec<CoinSpendJson>` (present) - Coin spends in the transaction
- Optional parameters: max_coin_amount, auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `issue_cat`
- Callable as: `issue_cat`
- Async/RPC behavior: async
- Request type: `IssueCat`
- Response type: `IssueCatResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `name: String` (required) - Token name
  - `ticker: String` (required) - Token ticker symbol
  - `amount: Amount` (required) - Initial supply amount
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `send_cat`
- Callable as: `send_cat`
- Async/RPC behavior: async
- Request type: `SendCat`
- Response type: `SendCatResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `asset_id: String` (required) - Asset ID of the CAT
  - `address: String` (required) - Recipient address
  - `amount: Amount` (required) - Amount to send
  - `fee: Amount` (required) - Transaction fee
  - `include_hint: bool` (optional) - no inline field comment
  - `memos: Vec<String>` (optional) - no inline field comment
  - `clawback: Option<u64>` (optional) - no inline field comment
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: include_hint, memos, clawback, auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `bulk_send_cat`
- Callable as: `bulk_send_cat`
- Async/RPC behavior: async
- Request type: `BulkSendCat`
- Response type: `BulkSendCatResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `asset_id: String` (required) - Asset ID of the CAT
  - `addresses: Vec<String>` (required) - List of recipient addresses
  - `amount: Amount` (required) - Amount to send to each address
  - `fee: Amount` (required) - Transaction fee
  - `include_hint: bool` (optional) - no inline field comment
  - `memos: Vec<String>` (optional) - no inline field comment
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: include_hint, memos, auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `multi_send`
- Callable as: `multi_send`
- Async/RPC behavior: async
- Request type: `MultiSend`
- Response type: `MultiSendResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `payments: Vec<Payment>` (required) - List of payments to make
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `create_did`
- Callable as: `create_did`
- Async/RPC behavior: async
- Request type: `CreateDid`
- Response type: `CreateDidResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `name: String` (required) - DID name
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `bulk_mint_nfts`
- Callable as: `bulk_mint_nfts`
- Async/RPC behavior: async
- Request type: `BulkMintNfts`
- Response type: `BulkMintNftsResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `mints: Vec<NftMint>` (required) - List of NFTs to mint
  - `did_id: String` (required) - DID ID for the NFT collection
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns:
  - `nft_ids: Vec<String>` (present) - List of minted NFT IDs
  - `summary: TransactionSummary` (present) - Transaction summary
  - `coin_spends: Vec<CoinSpendJson>` (present) - Coin spends in the transaction
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `transfer_nfts`
- Callable as: `transfer_nfts`
- Async/RPC behavior: async
- Request type: `TransferNfts`
- Response type: `TransferNftsResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `nft_ids: Vec<String>` (required) - NFT IDs to transfer
  - `address: String` (required) - Recipient address
  - `fee: Amount` (required) - Transaction fee
  - `clawback: Option<u64>` (optional) - no inline field comment
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: clawback, auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `add_nft_uri`
- Callable as: `add_nft_uri`
- Async/RPC behavior: async
- Request type: `AddNftUri`
- Response type: `AddNftUriResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `nft_id: String` (required) - NFT ID
  - `uri: String` (required) - URI to add
  - `fee: Amount` (required) - Transaction fee
  - `kind: NftUriKind` (required) - Type of URI
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `assign_nfts_to_did`
- Callable as: `assign_nfts_to_did`
- Async/RPC behavior: async
- Request type: `AssignNftsToDid`
- Response type: `AssignNftsToDidResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `nft_ids: Vec<String>` (required) - NFT IDs to assign
  - `did_id: Option<String>` (optional) - no inline field comment
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: did_id, auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `transfer_dids`
- Callable as: `transfer_dids`
- Async/RPC behavior: async
- Request type: `TransferDids`
- Response type: `TransferDidsResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `did_ids: Vec<String>` (required) - DID IDs to transfer
  - `address: String` (required) - Recipient address
  - `fee: Amount` (required) - Transaction fee
  - `clawback: Option<u64>` (optional) - no inline field comment
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: clawback, auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `normalize_dids`
- Callable as: `normalize_dids`
- Async/RPC behavior: async
- Request type: `NormalizeDids`
- Response type: `NormalizeDidsResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `did_ids: Vec<String>` (required) - DID IDs to normalize
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `mint_option`
- Callable as: `mint_option`
- Async/RPC behavior: async
- Request type: `MintOption`
- Response type: `MintOptionResponse`
- Behavioral notes: supports optional automatic submission flow; contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `expiration_seconds: u64` (required) - Expiration time in seconds
  - `underlying: OptionAsset` (required) - Underlying asset
  - `strike: OptionAsset` (required) - Strike price asset
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns:
  - `option_id: String` (present) - ID of the minted option
  - `summary: TransactionSummary` (present) - Transaction summary
  - `coin_spends: Vec<CoinSpendJson>` (present) - Coin spends in the transaction
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `transfer_options`
- Callable as: `transfer_options`
- Async/RPC behavior: async
- Request type: `TransferOptions`
- Response type: `TransferOptionsResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `option_ids: Vec<String>` (required) - Option IDs to transfer
  - `address: String` (required) - Recipient address
  - `fee: Amount` (required) - Transaction fee
  - `clawback: Option<u64>` (optional) - no inline field comment
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: clawback, auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `exercise_options`
- Callable as: `exercise_options`
- Async/RPC behavior: async
- Request type: `ExerciseOptions`
- Response type: `ExerciseOptionsResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `option_ids: Vec<String>` (required) - Option IDs to exercise
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `finalize_clawback`
- Callable as: `finalize_clawback`
- Async/RPC behavior: async
- Request type: `FinalizeClawback`
- Response type: `FinalizeClawbackResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `coin_ids: Vec<String>` (required) - The coins to finalize the clawback for
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `create_transaction`
- Callable as: `create_transaction`
- Async/RPC behavior: async
- Request type: `CreateTransaction`
- Response type: `CreateTransactionResponse`
- Behavioral notes: supports optional automatic submission flow; contains optional/default-path handling; performs async wallet/database/network work
- Parameters:
  - `selected_coin_ids: Vec<String>` (optional) - no inline field comment
  - `actions: Vec<Action>` (optional) - The list of actions to perform in the transaction
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: selected_coin_ids, actions, auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; contains optional/default-path handling; performs async wallet/database/network work

### `sign_coin_spends`
- Callable as: `sign_coin_spends`
- Async/RPC behavior: async
- Request type: `SignCoinSpends`
- Response type: `SignCoinSpendsResponse`
- Behavioral notes: supports optional automatic submission flow; performs async wallet/database/network work
- Parameters:
  - `coin_spends: Vec<CoinSpendJson>` (required) - Coin spends to sign
  - `auto_submit: bool` (optional) - no inline field comment
  - `partial: bool` (optional) - no inline field comment
- Returns:
  - `spend_bundle: SpendBundleJson` (present) - Signed spend bundle
- Optional parameters: auto_submit, partial
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; performs async wallet/database/network work

### `view_coin_spends`
- Callable as: `view_coin_spends`
- Async/RPC behavior: async
- Request type: `ViewCoinSpends`
- Response type: `ViewCoinSpendsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `coin_spends: Vec<CoinSpendJson>` (required) - Coin spends to view
- Returns:
  - `summary: TransactionSummary` (present) - Transaction summary
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `submit_transaction`
- Callable as: `submit_transaction`
- Async/RPC behavior: async
- Request type: `SubmitTransaction`
- Response type: `SubmitTransactionResponse`
- Behavioral notes: supports optional automatic submission flow; contains optional/default-path handling; performs async wallet/database/network work
- Parameters:
  - `spend_bundle: SpendBundleJson` (required) - Spend bundle to submit
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: supports optional automatic submission flow; contains optional/default-path handling; performs async wallet/database/network work

### `make_offer`
- Callable as: `make_offer`
- Async/RPC behavior: async
- Request type: `MakeOffer`
- Response type: `MakeOfferResponse`
- Behavioral notes: contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `requested_assets: Vec<OfferAmount>` (required) - Assets requested in the offer
  - `offered_assets: Vec<OfferAmount>` (required) - Assets offered in exchange
  - `fee: Amount` (required) - Transaction fee
  - `receive_address: Option<String>` (optional) - no inline field comment
  - `expires_at_second: Option<u64>` (optional) - no inline field comment
  - `auto_import: bool` (optional) - no inline field comment
  - `coin_ids: Option<Vec<String>>` (optional) - no inline field comment
- Returns:
  - `offer: String` (present) - Offer string (bech32 encoded)
  - `offer_id: String` (present) - Offer ID
- Optional parameters: receive_address, expires_at_second, auto_import, coin_ids
- Edge cases / alternative patterns: supports omitted/defaulted fields; contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `take_offer`
- Callable as: `take_offer`
- Async/RPC behavior: async
- Request type: `TakeOffer`
- Response type: `TakeOfferResponse`
- Behavioral notes: supports optional automatic submission flow; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `offer: String` (required) - Offer string to accept
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns:
  - `summary: TransactionSummary` (present) - Transaction summary
  - `spend_bundle: SpendBundleJson` (present) - Spend bundle
  - `transaction_id: String` (present) - Transaction ID
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `combine_offers`
- Callable as: `combine_offers`
- Async/RPC behavior: sync
- Request type: `CombineOffers`
- Response type: `CombineOffersResponse`
- Behavioral notes: implementation is straightforward state lookup/update plus validation
- Parameters:
  - `offers: Vec<String>` (required) - Offer strings to combine
- Returns:
  - `offer: String` (present) - Combined offer string
- Optional parameters: none detected
- Edge cases / alternative patterns: implementation is straightforward state lookup/update plus validation

### `view_offer`
- Callable as: `view_offer`
- Async/RPC behavior: async
- Request type: `ViewOffer`
- Response type: `ViewOfferResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `offer: String` (required) - Offer string to view
- Returns:
  - `offer: OfferSummary` (present) - Offer summary
  - `status: OfferRecordStatus` (present) - Offer status
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `import_offer`
- Callable as: `import_offer`
- Async/RPC behavior: async
- Request type: `ImportOffer`
- Response type: `ImportOfferResponse`
- Behavioral notes: contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `offer: String` (required) - Offer string to import
- Returns:
  - `offer_id: String` (present) - ID of the imported offer
- Optional parameters: none detected
- Edge cases / alternative patterns: contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `get_offers`
- Callable as: `get_offers`
- Async/RPC behavior: async
- Request type: `GetOffers`
- Response type: `GetOffersResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters: none
- Returns:
  - `offers: Vec<OfferRecord>` (present) - List of offers
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_offers_for_asset`
- Callable as: `get_offers_for_asset`
- Async/RPC behavior: async
- Request type: `GetOffersForAsset`
- Response type: `GetOffersForAssetResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `asset_id: String` (required) - Asset ID to filter by
- Returns:
  - `offers: Vec<OfferRecord>` (present) - List of offers involving the asset
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_offer`
- Callable as: `get_offer`
- Async/RPC behavior: async
- Request type: `GetOffer`
- Response type: `GetOfferResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `offer_id: String` (required) - Offer ID
- Returns:
  - `offer: OfferRecord` (present) - Offer details
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `delete_offer`
- Callable as: `delete_offer`
- Async/RPC behavior: async
- Request type: `DeleteOffer`
- Response type: `DeleteOfferResponse`
- Behavioral notes: contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `offer_id: String` (required) - Offer ID to delete
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `cancel_offer`
- Callable as: `cancel_offer`
- Async/RPC behavior: async
- Request type: `CancelOffer`
- Response type: `CancelOfferResponse`
- Behavioral notes: supports optional automatic submission flow; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `offer_id: String` (required) - Offer ID to cancel
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `cancel_offers`
- Callable as: `cancel_offers`
- Async/RPC behavior: async
- Request type: `CancelOffers`
- Response type: `CancelOffersResponse`
- Behavioral notes: supports optional automatic submission flow; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `offer_ids: Vec<String>` (required) - Offer IDs to cancel
  - `fee: Amount` (required) - Transaction fee
  - `auto_submit: bool` (optional) - no inline field comment
- Returns: alias to `TransactionResponse`
- Optional parameters: auto_submit
- Edge cases / alternative patterns: supports omitted/defaulted fields; supports optional automatic submission flow; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `get_peers`
- Callable as: `get_peers`
- Async/RPC behavior: async
- Request type: `GetPeers`
- Response type: `GetPeersResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters: none
- Returns:
  - `peers: Vec<PeerRecord>` (present) - List of connected peers
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_user_themes`
- Callable as: `get_user_themes`
- Async/RPC behavior: async
- Request type: `GetUserThemes`
- Response type: `GetUserThemesResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters: none
- Returns:
  - `themes: Vec<String>` (present) - List of theme NFT IDs
- Optional parameters: none detected
- Edge cases / alternative patterns: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `get_user_theme`
- Callable as: `get_user_theme`
- Async/RPC behavior: async
- Request type: `GetUserTheme`
- Response type: `GetUserThemeResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `nft_id: String` (required) - NFT ID of the theme
- Returns:
  - `theme: Option<String>` (optional) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `save_user_theme`
- Callable as: `save_user_theme`
- Async/RPC behavior: async
- Request type: `SaveUserTheme`
- Response type: `SaveUserThemeResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `nft_id: String` (required) - NFT ID of the theme
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `delete_user_theme`
- Callable as: `delete_user_theme`
- Async/RPC behavior: async
- Request type: `DeleteUserTheme`
- Response type: `DeleteUserThemeResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `nft_id: String` (required) - NFT ID of the theme
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `remove_peer`
- Callable as: `remove_peer`
- Async/RPC behavior: async
- Request type: `RemovePeer`
- Response type: `RemovePeerResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `ip: String` (required) - no inline field comment
  - `ban: bool` (required) - no inline field comment
- Returns: alias to `EmptyResponse`
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `add_peer`
- Callable as: `add_peer`
- Async/RPC behavior: async
- Request type: `AddPeer`
- Response type: `AddPeerResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `ip: String` (required) - no inline field comment
- Returns: alias to `EmptyResponse`
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `set_discover_peers`
- Callable as: `set_discover_peers`
- Async/RPC behavior: async
- Request type: `SetDiscoverPeers`
- Response type: `SetDiscoverPeersResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `discover_peers: bool` (required) - no inline field comment
- Returns: alias to `EmptyResponse`
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `set_target_peers`
- Callable as: `set_target_peers`
- Async/RPC behavior: async
- Request type: `SetTargetPeers`
- Response type: `SetTargetPeersResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `target_peers: u32` (required) - no inline field comment
- Returns: alias to `EmptyResponse`
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `set_network`
- Callable as: `set_network`
- Async/RPC behavior: async
- Request type: `SetNetwork`
- Response type: `SetNetworkResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `name: String` (required) - no inline field comment
- Returns: alias to `EmptyResponse`
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `set_network_override`
- Callable as: `set_network_override`
- Async/RPC behavior: async
- Request type: `SetNetworkOverride`
- Response type: `SetNetworkOverrideResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `fingerprint: u32` (required) - no inline field comment
  - `name: Option<String>` (optional) - no inline field comment
- Returns: alias to `EmptyResponse`
- Optional parameters: name
- Edge cases / alternative patterns: supports omitted/defaulted fields; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `get_networks`
- Callable as: `get_networks`
- Async/RPC behavior: sync
- Request type: `GetNetworks`
- Response type: `GetNetworksResponse`
- Behavioral notes: implementation is straightforward state lookup/update plus validation
- Parameters: none
- Returns: alias to `NetworkList`
- Optional parameters: none detected
- Edge cases / alternative patterns: implementation is straightforward state lookup/update plus validation

### `get_network`
- Callable as: `get_network`
- Async/RPC behavior: sync
- Request type: `GetNetwork`
- Response type: `GetNetworkResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state
- Parameters: none
- Returns:
  - `network: Network` (present) - Current network configuration
  - `kind: NetworkKind` (present) - Network type classification
- Optional parameters: none detected
- Edge cases / alternative patterns: returns validation or lookup errors on invalid input/state

### `set_delta_sync`
- Callable as: `set_delta_sync`
- Async/RPC behavior: sync
- Request type: `SetDeltaSync`
- Response type: `SetDeltaSyncResponse`
- Behavioral notes: implementation is straightforward state lookup/update plus validation
- Parameters:
  - `delta_sync: bool` (required) - no inline field comment
- Returns: alias to `EmptyResponse`
- Optional parameters: none detected
- Edge cases / alternative patterns: implementation is straightforward state lookup/update plus validation

### `set_delta_sync_override`
- Callable as: `set_delta_sync_override`
- Async/RPC behavior: sync
- Request type: `SetDeltaSyncOverride`
- Response type: `SetDeltaSyncOverrideResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state
- Parameters:
  - `fingerprint: u32` (required) - no inline field comment
  - `delta_sync: Option<bool>` (optional) - Delta sync setting (null to use default)
- Returns: alias to `EmptyResponse`
- Optional parameters: delta_sync
- Edge cases / alternative patterns: supports omitted/defaulted fields; returns validation or lookup errors on invalid input/state

### `set_change_address`
- Callable as: `set_change_address`
- Async/RPC behavior: async
- Request type: `SetChangeAddress`
- Response type: `SetChangeAddressResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `fingerprint: u32` (required) - no inline field comment
  - `change_address: Option<String>` (optional) - no inline field comment
- Returns: alias to `EmptyResponse`
- Optional parameters: change_address
- Edge cases / alternative patterns: supports omitted/defaulted fields; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `resync_cat`
- Callable as: `resync_cat`
- Async/RPC behavior: async
- Request type: `ResyncCat`
- Response type: `ResyncCatResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `asset_id: String` (required) - no inline field comment
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `update_cat`
- Callable as: `update_cat`
- Async/RPC behavior: async
- Request type: `UpdateCat`
- Response type: `UpdateCatResponse`
- Behavioral notes: contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `record: TokenRecord` (required) - The token record containing updated metadata
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `update_did`
- Callable as: `update_did`
- Async/RPC behavior: async
- Request type: `UpdateDid`
- Response type: `UpdateDidResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `did_id: String` (required) - no inline field comment
  - `name: Option<String>` (optional) - no inline field comment
  - `visible: bool` (required) - no inline field comment
- Returns: empty object / unit-style response
- Optional parameters: name
- Edge cases / alternative patterns: supports omitted/defaulted fields; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `update_option`
- Callable as: `update_option`
- Async/RPC behavior: async
- Request type: `UpdateOption`
- Response type: `UpdateOptionResponse`
- Behavioral notes: contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `option_id: String` (required) - no inline field comment
  - `visible: bool` (required) - no inline field comment
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `update_nft`
- Callable as: `update_nft`
- Async/RPC behavior: async
- Request type: `UpdateNft`
- Response type: `UpdateNftResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `nft_id: String` (required) - no inline field comment
  - `visible: bool` (required) - no inline field comment
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `update_nft_collection`
- Callable as: `update_nft_collection`
- Async/RPC behavior: async
- Request type: `UpdateNftCollection`
- Response type: `UpdateNftCollectionResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `collection_id: String` (required) - no inline field comment
  - `visible: bool` (required) - no inline field comment
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `redownload_nft`
- Callable as: `redownload_nft`
- Async/RPC behavior: async
- Request type: `RedownloadNft`
- Response type: `RedownloadNftResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `nft_id: String` (required) - no inline field comment
- Returns: empty object / unit-style response
- Optional parameters: none detected
- Edge cases / alternative patterns: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `increase_derivation_index`
- Callable as: `increase_derivation_index`
- Async/RPC behavior: async
- Request type: `IncreaseDerivationIndex`
- Response type: `IncreaseDerivationIndexResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `hardened: Option<bool>` (optional) - no inline field comment
  - `unhardened: Option<bool>` (optional) - no inline field comment
  - `index: u32` (required) - no inline field comment
- Returns: empty object / unit-style response
- Optional parameters: hardened, unhardened
- Edge cases / alternative patterns: supports omitted/defaulted fields; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `is_asset_owned`
- Callable as: `is_asset_owned`
- Async/RPC behavior: async
- Request type: `IsAssetOwned`
- Response type: `IsAssetOwnedResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `asset_id: String` (required) - Asset ID to check
- Returns:
  - `owned: bool` (present) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `filter_unlocked_coins`
- Callable as: `filter_unlocked_coins`
- Async/RPC behavior: async
- Request type: `FilterUnlockedCoins`
- Response type: `FilterUnlockedCoinsResponse`
- Behavioral notes: performs async wallet/database/network work
- Parameters:
  - `coin_ids: Vec<String>` (required) - Coin IDs to filter
- Returns:
  - `coin_ids: Vec<String>` (present) - List of unlocked coin IDs
- Optional parameters: none detected
- Edge cases / alternative patterns: performs async wallet/database/network work

### `get_asset_coins`
- Callable as: `get_asset_coins`
- Async/RPC behavior: async
- Request type: `GetAssetCoins`
- Response type: `GetAssetCoinsResponse`
- Behavioral notes: contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `kind: Option<AssetCoinType>` (optional) - no inline field comment
  - `asset_id: Option<String>` (optional) - no inline field comment
  - `included_locked: Option<bool>` (optional) - no inline field comment
  - `offset: Option<u32>` (optional) - no inline field comment
  - `limit: Option<u32>` (optional) - no inline field comment
- Returns: alias to `Vec<SpendableCoin>`
- Optional parameters: kind, asset_id, included_locked, offset, limit
- Edge cases / alternative patterns: supports omitted/defaulted fields; contains optional/default-path handling; returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `sign_message_with_public_key`
- Callable as: `sign_message_with_public_key`
- Async/RPC behavior: async
- Request type: `SignMessageWithPublicKey`
- Response type: `SignMessageWithPublicKeyResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `message: String` (required) - Message to sign
  - `public_key: String` (required) - Public key to use for signing
- Returns:
  - `signature: String` (present) - Signature
- Optional parameters: none detected
- Edge cases / alternative patterns: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `sign_message_by_address`
- Callable as: `sign_message_by_address`
- Async/RPC behavior: async
- Request type: `SignMessageByAddress`
- Response type: `SignMessageByAddressResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `message: String` (required) - Message to sign
  - `address: String` (required) - Address whose key to use
- Returns:
  - `public_key: String` (present) - Public key used
  - `signature: String` (present) - Signature
- Optional parameters: none detected
- Edge cases / alternative patterns: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

### `send_transaction_immediately`
- Callable as: `send_transaction_immediately`
- Async/RPC behavior: async
- Request type: `SendTransactionImmediately`
- Response type: `SendTransactionImmediatelyResponse`
- Behavioral notes: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work
- Parameters:
  - `spend_bundle: SpendBundle` (required) - Spend bundle to send
- Returns:
  - `status: u8` (present) - Status code
  - `error: Option<String>` (optional) - no inline field comment
- Optional parameters: none detected
- Edge cases / alternative patterns: returns validation or lookup errors on invalid input/state; performs async wallet/database/network work

## Tauri Commands / RPC Calls
### `initialize`
- Parameters: none
- Returns: `()`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `validate_address`
- Parameters: `address: String`
- Returns: `bool`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `network_config`
- Parameters: none
- Returns: `NetworkConfig`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `wallet_config`
- Parameters: `fingerprint: u32`
- Returns: `Option<Wallet`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `default_wallet_config`
- Parameters: none
- Returns: `WalletDefaults`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `is_rpc_running`
- Parameters: none
- Returns: `bool`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `start_rpc_server`
- Parameters: none
- Returns: `()`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `stop_rpc_server`
- Parameters: none
- Returns: `()`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `get_rpc_run_on_startup`
- Parameters: none
- Returns: `bool`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `set_rpc_run_on_startup`
- Parameters: `run_on_startup: bool`
- Returns: `()`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `switch_wallet`
- Parameters: none
- Returns: `()`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `move_key`
- Parameters: `fingerprint: u32`, `index: u32`
- Returns: `()`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `download_cni_offercode`
- Parameters: `code: String`
- Returns: `String`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `get_logs`
- Parameters: none
- Returns: `Vec<LogFile`
- Behavioral notes: Desktop command exposed through Tauri IPC.

### `endpoint`
- Parameters: `req: Endpoint`
- Returns: `EndpointResponse`
- Behavioral notes: Generated wrapper over every endpoint in endpoints.json and endpoints-tauri.json; async-ness depends on endpoint registry.

## Rust Public Function List
- `crates/sage-api/macro/src/lib.rs`: `endpoint_metadata(input: TokenStream) -> TokenStream`
  Notes: No doc comment extracted.
- `crates/sage-api/macro/src/lib.rs`: `impl_endpoints(input: TokenStream) -> TokenStream`
  Notes: No doc comment extracted.
- `crates/sage-api/macro/src/lib.rs`: `impl_endpoints_tauri(input: TokenStream) -> TokenStream`
  Notes: No doc comment extracted.
- `crates/sage-api/macro/src/lib.rs`: `openapi(args: TokenStream, input: TokenStream) -> TokenStream`
  Notes: No doc comment extracted.
- `crates/sage-api/macro/src/lib.rs`: `register_openapi_types(input: TokenStream) -> TokenStream`
  Notes: No doc comment extracted.
- `crates/sage-api/macro/src/lib.rs`: `request_schemas(input: TokenStream) -> TokenStream`
  Notes: No doc comment extracted.
- `crates/sage-api/macro/src/lib.rs`: `response_schemas(input: TokenStream) -> TokenStream`
  Notes: No doc comment extracted.
- `crates/sage-api/macro/src/openapi.rs`: `impl_endpoint_metadata(_input: TokenStream1) -> TokenStream1`
  Notes: Generates endpoint metadata match arms from endpoints.json  Generates match arms that call `OpenApiMetadata` trait methods for each endpoint
- `crates/sage-api/macro/src/openapi.rs`: `impl_openapi_metadata(args: &OpenApiArgs, input: &syn::DeriveInput) -> TokenStream`
  Notes: No doc comment extracted.
- `crates/sage-api/macro/src/openapi.rs`: `impl_openapi_registration(_input: TokenStream1) -> TokenStream1`
  Notes: Generates `OpenAPI` schema registration code from endpoints.json  Takes advantage of the enforced pattern: - Endpoint: `login` (from endpoints.json) - Input type: `Login` (`PascalCase`) - Response type: `LoginResponse` (`PascalCase` + "Response")  Reads endpoints.json at compile time and generates schema registrations
- `crates/sage-api/macro/src/openapi.rs`: `impl_request_schemas(_input: TokenStream1) -> TokenStream1`
  Notes: Generates request schema match arms from endpoints.json
- `crates/sage-api/macro/src/openapi.rs`: `impl_response_schemas(_input: TokenStream1) -> TokenStream1`
  Notes: Generates response schema match arms from endpoints.json
- `crates/sage-api/src/types/amount.rs`: `to_u128() -> Option<u128>`
  Notes: No doc comment extracted.
- `crates/sage-api/src/types/amount.rs`: `to_u16() -> Option<u16>`
  Notes: No doc comment extracted.
- `crates/sage-api/src/types/amount.rs`: `to_u64() -> Option<u64>`
  Notes: No doc comment extracted.
- `crates/sage-api/src/types/amount.rs`: `u128(value: u128) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-api/src/types/amount.rs`: `u64(value: u64) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-api/src/types/unit.rs`: `cat(ticker: String) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/cats.rs`: `async fetch(asset_id: Bytes32, testnet: bool) -> Result<Self, UriError>`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/cats.rs`: `async fetch_all(testnet: bool) -> Result<Vec<Self>, UriError>`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/nfts/chip0007_metadata.rs`: `as_str() -> Option<&str>`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/nfts/chip0007_metadata.rs`: `from_bytes(bytes: &[u8]) -> Result<Self, serde_json::Error>`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/nfts/chip0007_metadata.rs`: `is_sensitive() -> bool`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/nfts/chip0007_metadata.rs`: `parse(json: &str) -> Result<Self, serde_json::Error>`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/nfts/data_uri.rs`: `base64_data_uri(blob: &[u8], mime_type: &str) -> String`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/nfts/fetch_nft_uri.rs`: `async fetch_uri(uri: String, testnet: bool) -> Result<Data, UriError>`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/nfts/fetch_nft_uri.rs`: `async fetch_uris_with_hash(uris: Vec<String>, hash: Bytes32, testnet: bool) -> Option<Data>`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/nfts/fetch_nft_uri.rs`: `async fetch_uris_without_hash(uris: Vec<String>, testnet: bool) -> Result<Data, UriError>`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/nfts/fetch_nft_uri.rs`: `async mintgarden_thumbnail(data_hash: Bytes32, testnet: bool) -> Result<Option<Thumbnail>, UriError>`
  Notes: No doc comment extracted.
- `crates/sage-assets/src/nfts/thumbnail.rs`: `thumbnail(bytes: &[u8], mime: &str) -> Result<Option<Thumbnail>, ThumbnailError>`
  Notes: No doc comment extracted.
- `crates/sage-cli/src/rpc.rs`: `async handle(path: PathBuf) -> anyhow::Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-client/src/lib.rs`: `async endpoint(body: sage_api::Endpoint) -> Result<sage_api::EndpointResponse, SageRpcError>`
  Notes: No doc comment extracted.
- `crates/sage-client/src/lib.rs`: `from_addr_and_identity(addr: SocketAddr, identity: Identity) -> Result<Self, SageRpcError>`
  Notes: No doc comment extracted.
- `crates/sage-client/src/lib.rs`: `from_dir(path: &Path) -> Result<Self, SageRpcError>`
  Notes: No doc comment extracted.
- `crates/sage-client/src/lib.rs`: `new() -> Result<Self, SageRpcError>`
  Notes: No doc comment extracted.
- `crates/sage-config/src/network.rs`: `agg_sig_me() -> Bytes32`
  Notes: No doc comment extracted.
- `crates/sage-config/src/network.rs`: `by_name(name: &str) -> Option<&Network>`
  Notes: No doc comment extracted.
- `crates/sage-config/src/network.rs`: `dns_introducers() -> Vec<String>`
  Notes: No doc comment extracted.
- `crates/sage-config/src/network.rs`: `network_id() -> String`
  Notes: No doc comment extracted.
- `crates/sage-config/src/network.rs`: `peer_introducers() -> Vec<String>`
  Notes: No doc comment extracted.
- `crates/sage-config/src/network.rs`: `prefix() -> String`
  Notes: No doc comment extracted.
- `crates/sage-config/src/old.rs`: `is_old() -> bool`
  Notes: No doc comment extracted.
- `crates/sage-config/src/old.rs`: `migrate_config(old: OldConfig) -> Result<(Config, WalletConfig), ParseIntError>`
  Notes: No doc comment extracted.
- `crates/sage-config/src/old.rs`: `migrate_networks(old: IndexMap<String) -> NetworkList`
  Notes: No doc comment extracted.
- `crates/sage-config/src/wallet.rs`: `delta_sync(defaults: &WalletDefaults) -> bool`
  Notes: No doc comment extracted.
- `crates/sage-database/src/lib.rs`: `async commit() -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/lib.rs`: `new(pool: SqlitePool) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-database/src/lib.rs`: `new(tx: SqliteTransaction<'a) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-database/src/lib.rs`: `async rollback() -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/lib.rs`: `async run_rust_migrations(ticker: String) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/lib.rs`: `async rust_migration_version() -> Result<i64>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/lib.rs`: `async set_rust_migration_version(version: i64) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/lib.rs`: `async tx() -> Result<DatabaseTx<'_>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/maintenance.rs`: `async get_database_stats() -> Result<DatabaseStats>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/maintenance.rs`: `async perform_full_maintenance() -> Result<MaintenanceStats>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/maintenance.rs`: `async perform_quick_maintenance() -> Result<MaintenanceStats>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/maintenance.rs`: `async perform_sqlite_maintenance(force_vacuum: bool) -> Result<MaintenanceStats>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/asset.rs`: `async asset(hash: Bytes32) -> Result<Option<Asset>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/asset.rs`: `async asset(hash: Bytes32) -> Result<Option<Asset>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/asset.rs`: `async asset_kind(hash: Bytes32) -> Result<Option<AssetKind>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/asset.rs`: `async delete_asset_coins(asset_hash: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/asset.rs`: `async existing_hidden_puzzle_hash(asset_hash: Bytes32) -> Result<Option<Option<Bytes32>>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/asset.rs`: `async existing_hidden_puzzle_hash(asset_hash: Bytes32) -> Result<Option<Option<Bytes32>>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/asset.rs`: `async insert_asset(asset: Asset) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/asset.rs`: `async insert_asset(asset: Asset) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/asset.rs`: `async is_asset_owned(hash: Bytes32) -> Result<bool>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/asset.rs`: `async update_asset(asset: Asset) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/asset.rs`: `async update_hidden_puzzle_hash(asset_hash: Bytes32, hidden_puzzle_hash: Option<Bytes32>) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/cat.rs`: `async all_cats() -> Result<Vec<Asset>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/cat.rs`: `async owned_cats() -> Result<Vec<Asset>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/did.rs`: `async insert_did(hash: Bytes32, coin_info: &DidCoinInfo) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/did.rs`: `async owned_dids() -> Result<Vec<DidRow>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/did.rs`: `async update_did(hash: Bytes32, coin_info: &DidCoinInfo) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/nft.rs`: `async distinct_minter_dids(limit: u32, offset: u32) -> Result<(Vec<Bytes32>, u32)>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/nft.rs`: `async insert_nft(hash: Bytes32, coin_info: &NftCoinInfo) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/nft.rs`: `async offer_nft_info(hash: Bytes32) -> Result<Option<NftOfferInfo>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/nft.rs`: `async owned_nfts(name_search: Option<String>, group_search: Option<NftGroupSearch>, sort_mode: NftSortMode, include_hidden: bool, limit: u32, offset: u32) -> Result<(Vec<NftRow>, u32)>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/nft.rs`: `async update_nft(hash: Bytes32, coin_info: &NftCoinInfo) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/nft.rs`: `async update_nft_data_hash_urls(data_hash: Bytes32, icon_url: String) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/nft.rs`: `async update_nft_metadata(hash: Bytes32, metadata_info: NftMetadataInfo) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/nft.rs`: `async wallet_nft(hash: Bytes32) -> Result<Option<NftRow>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/option.rs`: `async insert_option(hash: Bytes32, coin_info: &OptionCoinInfo) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/option.rs`: `async offer_option_info(hash: Bytes32) -> Result<Option<OptionOfferInfo>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/option.rs`: `async option_assets(launcher_id: Bytes32) -> Result<Option<OptionAssetsRow>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/option.rs`: `async option_underlying(launcher_id: Bytes32) -> Result<Option<OptionUnderlying>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/option.rs`: `async owned_options(limit: u32, offset: u32, sort_mode: OptionSortMode, ascending: bool, find_value: Option<String>, include_hidden: bool) -> Result<(Vec<OptionRow>, u32)>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/assets/option.rs`: `async wallet_option(launcher_id: Bytes32) -> Result<Option<OptionRow>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/blocks.rs`: `async insert_block(height: u32, header_hash: Bytes32, timestamp: Option<i64>, is_peak: bool) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/blocks.rs`: `async insert_height(height: u32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/blocks.rs`: `async latest_peak() -> Result<Option<(u32, Bytes32)>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/blocks.rs`: `async unsynced_blocks(limit: u32) -> Result<Vec<u32>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async are_coins_spendable(coin_ids: &[String]) -> Result<bool>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async cat_balance(asset_id: Bytes32) -> Result<u128>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async cat_coin(coin_id: Bytes32) -> Result<Option<Cat>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async coin_kind(coin_id: Bytes32) -> Result<Option<CoinKind>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async coin_records(asset_filter: AssetFilter, limit: u32, offset: u32, sort_mode: CoinSortMode, ascending: bool, filter_mode: CoinFilterMode) -> Result<(Vec<CoinRow>, u32)>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async coins_by_ids(coin_ids: &[String]) -> Result<Vec<CoinRow>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async delete_coin(coin_id: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async did(launcher_id: Bytes32) -> Result<Option<SerializedDid>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async did_coin(coin_id: Bytes32) -> Result<Option<SerializedDid>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async insert_coin(coin_state: CoinState) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async insert_lineage_proof(coin_id: Bytes32, lineage_proof: LineageProof) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async is_known_coin(coin_id: Bytes32) -> Result<bool>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async nft(launcher_id: Bytes32) -> Result<Option<SerializedNft>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async nft_coin(coin_id: Bytes32) -> Result<Option<SerializedNft>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async option(launcher_id: Bytes32) -> Result<Option<OptionContract>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async option_coin(coin_id: Bytes32) -> Result<Option<OptionContract>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async selectable_cat_balance(asset_id: Bytes32) -> Result<u128>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async selectable_cat_coin_count(asset_id: Bytes32) -> Result<u32>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async selectable_cat_coins(asset_id: Bytes32) -> Result<Vec<Cat>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async selectable_xch_balance() -> Result<u128>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async selectable_xch_coin_count() -> Result<u32>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async selectable_xch_coins() -> Result<Vec<Coin>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async set_children_synced(coin_id: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async set_transaction_children_unsynced(mempool_item_id: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async spendable_did(launcher_id: Bytes32) -> Result<Option<SerializedDid>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async spendable_nft(launcher_id: Bytes32) -> Result<Option<SerializedNft>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async spendable_option(launcher_id: Bytes32) -> Result<Option<OptionContract>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async subscription_coin_ids() -> Result<Vec<Bytes32>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async synced_coin_count() -> Result<u32>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async total_coin_count() -> Result<u32>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async underlying_coin_kind(launcher_id: Bytes32) -> Result<Option<CoinKind>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async unsynced_coins(limit: usize) -> Result<Vec<UnsyncedCoin>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async update_coin(coin_id: Bytes32, asset_hash: Bytes32, p2_puzzle_hash: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async update_coin(coin_id: Bytes32, asset_hash: Bytes32, p2_puzzle_hash: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async xch_balance() -> Result<u128>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/coins.rs`: `async xch_coin(coin_id: Bytes32) -> Result<Option<Coin>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/collections.rs`: `async collection(hash: Bytes32) -> Result<Option<CollectionRow>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/collections.rs`: `async collections(limit: u32, offset: u32, include_hidden: bool) -> Result<(Vec<CollectionRow>, u32)>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/collections.rs`: `async insert_collection(row: CollectionRow) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/collections.rs`: `async set_collection_visible(hash: Bytes32, visible: bool) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/collections.rs`: `async set_collection_visible(hash: Bytes32, visible: bool) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async candidates_for_download(check_every_seconds: i64, max_failed_attempts: u32, limit: u32) -> Result<Vec<FileUri>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async checked_files() -> Result<u64>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async delete_file_data(hash: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async file_data(hash: Bytes32) -> Result<Option<Vec<u8>>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async full_file_data(hash: Bytes32) -> Result<Option<FileData>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async icon(hash: Bytes32) -> Result<Option<ResizedImage>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async icon(hash: Bytes32) -> Result<Option<ResizedImage>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async insert_file(hash: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async insert_file_uri(hash: Bytes32, uri: String) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async insert_resized_image(file_hash: Bytes32, kind: ResizedImageKind, data: Vec<u8>) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async nfts_with_metadata_hash(hash: Bytes32) -> Result<Vec<UpdateableNft>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async set_uri_unchecked(uri: String) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async thumbnail(hash: Bytes32) -> Result<Option<ResizedImage>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async total_files() -> Result<u64>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async update_checked_uri(hash: Bytes32, uri: String) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async update_failed_uri(hash: Bytes32, uri: String) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/files.rs`: `async update_file(hash: Bytes32, data: Vec<u8>, mime_type: String, is_hash_match: bool) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/mempool_items.rs`: `async insert_mempool_coin(mempool_item_id: Bytes32, coin_id: Bytes32, is_input: bool, is_output: bool) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/mempool_items.rs`: `async insert_mempool_item(hash: Bytes32, aggregated_signature: Signature, fee: u64) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/mempool_items.rs`: `async insert_mempool_spend(mempool_item_id: Bytes32, coin_spend: CoinSpend, seq: usize) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/mempool_items.rs`: `async mempool_coin_spends(mempool_item_id: Bytes32) -> Result<Vec<CoinSpend>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/mempool_items.rs`: `async mempool_items() -> Result<Vec<MempoolItem>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/mempool_items.rs`: `async mempool_items_for_input(coin_id: Bytes32) -> Result<Vec<Bytes32>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/mempool_items.rs`: `async mempool_items_for_output(coin_id: Bytes32) -> Result<Vec<Bytes32>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/mempool_items.rs`: `async mempool_items_to_submit(check_every_seconds: i64, limit: i64) -> Result<Vec<MempoolItem>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/mempool_items.rs`: `async remove_mempool_item(mempool_item_id: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/mempool_items.rs`: `async update_mempool_item_time(mempool_item_id: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/offers.rs`: `async delete_offer(offer_id: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/offers.rs`: `async insert_offer(offer: OfferRow) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/offers.rs`: `async insert_offer_asset(offer_id: Bytes32, asset_id: Bytes32, amount: u64, royalty: u64, is_requested: bool) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/offers.rs`: `async insert_offered_coin(offer_id: Bytes32, coin_id: Bytes32) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/offers.rs`: `async offer(offer_id: Bytes32) -> Result<Option<OfferRow>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/offers.rs`: `async offer_assets(offer_id: Bytes32) -> Result<Vec<OfferedAsset>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/offers.rs`: `async offers(status: Option<OfferStatus>) -> Result<Vec<OfferRow>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/offers.rs`: `async offers_for_asset(asset_id: Bytes32, status: Option<OfferStatus>) -> Result<Vec<OfferRow>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/offers.rs`: `async offers_for_asset(asset_id: Bytes32, status: Option<OfferStatus>) -> Result<Vec<OfferRow>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/offers.rs`: `async update_offer_status(offer_id: Bytes32, status: OfferStatus) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/offers.rs`: `async update_offer_status(offer_id: Bytes32, status: OfferStatus) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async custody_p2_puzzle_hash(derivation_index: u32, is_hardened: bool) -> Result<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async custody_p2_puzzle_hashes() -> Result<Vec<Bytes32>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async derivation(public_key: PublicKey) -> Result<Option<Derivation>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async derivation_index(is_hardened: bool) -> Result<u32>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async derivations(is_hardened: bool, limit: u32, offset: u32) -> Result<(Vec<DerivationRow>, u32)>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async insert_arbor_p2_puzzle(key: PublicKey) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async insert_clawback_p2_puzzle(clawback: ClawbackV2) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async insert_custody_p2_puzzle(p2_puzzle_hash: Bytes32, key: PublicKey, derivation: Derivation) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async insert_option_p2_puzzle(underlying: OptionUnderlying) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async is_custody_p2_puzzle_hash(puzzle_hash: Bytes32) -> Result<bool>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async is_custody_p2_puzzle_hash(puzzle_hash: Bytes32) -> Result<bool>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async is_p2_puzzle_hash(puzzle_hash: Bytes32) -> Result<bool>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async is_p2_puzzle_hash(puzzle_hash: Bytes32) -> Result<bool>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async max_derivation_index(is_hardened: bool) -> Result<Option<u32>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async p2_puzzle(puzzle_hash: Bytes32) -> Result<P2Puzzle>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async public_key(p2_puzzle_hash: Bytes32) -> Result<Option<PublicKey>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/p2_puzzles.rs`: `async unused_derivation_index(is_hardened: bool) -> Result<u32>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/transactions.rs`: `is_valid_asset_id(asset_id: &str) -> bool`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/transactions.rs`: `puzzle_hash_from_address(address: &str) -> Option<String>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/transactions.rs`: `async transaction(height: u32) -> Result<Option<Transaction>>`
  Notes: No doc comment extracted.
- `crates/sage-database/src/tables/transactions.rs`: `async transactions(find_value: Option<String>, sort_ascending: bool, limit: u32, offset: u32) -> Result<(Vec<Transaction>, u32)>`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/encrypt.rs`: `encrypt(password: &[u8], rng: &mut (impl CryptoRng + Rng), data: &impl Serialize) -> Result<Encrypted, KeychainError>`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/keychain.rs`: `add_mnemonic(mnemonic: &Mnemonic, password: &[u8]) -> Result<u32, KeychainError>`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/keychain.rs`: `add_public_key(master_pk: &PublicKey) -> Result<u32, KeychainError>`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/keychain.rs`: `add_secret_key(master_sk: &SecretKey, password: &[u8]) -> Result<u32, KeychainError>`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/keychain.rs`: `contains(fingerprint: u32) -> bool`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/keychain.rs`: `extract_public_key(fingerprint: u32) -> Result<Option<PublicKey>, KeychainError>`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/keychain.rs`: `extract_secrets(fingerprint: u32, password: &[u8]) -> Result<(Option<Mnemonic>, Option<SecretKey>), KeychainError>`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/keychain.rs`: `fingerprints() -> impl Iterator<Item = u32> + '_`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/keychain.rs`: `from_bytes(data: &[u8]) -> Result<Self, KeychainError>`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/keychain.rs`: `has_secret_key(fingerprint: u32) -> bool`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/keychain.rs`: `remove(fingerprint: u32) -> bool`
  Notes: No doc comment extracted.
- `crates/sage-keychain/src/keychain.rs`: `to_bytes() -> Result<Vec<u8>, KeychainError>`
  Notes: No doc comment extracted.
- `crates/sage-rpc/src/lib.rs`: `make_router(sage: Arc<Mutex<Sage>>) -> Router`
  Notes: No doc comment extracted.
- `crates/sage-rpc/src/lib.rs`: `async start_rpc(sage: Arc<Mutex<Sage>>) -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-rpc/src/openapi.rs`: `generate_openapi() -> OpenApi`
  Notes: Generates the `OpenAPI` specification for all RPC endpoints Dynamically reads from endpoints.json at compile time
- `crates/sage-rpc/src/tests.rs`: `async endpoint(body: sage_api::Endpoint) -> Result<sage_api::EndpointResponse>`
  Notes: No doc comment extracted.
- `crates/sage-rpc/src/tests.rs`: `async new() -> Result<Self>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/child_kind.rs`: `clawback_from_memo_unchecked(allocator: &Allocator, memo: NodePtr, receiver_puzzle_hash: Bytes32, amount: u64, hinted: bool) -> Option<ClawbackV2>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/child_kind.rs`: `custody_p2_puzzle_hashes() -> Vec<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/child_kind.rs`: `from_parent(parent_coin: Coin, parent_puzzle: &Program, parent_solution: &Program, coin: Coin) -> Result<Self, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/child_kind.rs`: `parse_children(parent_coin: Coin, parent_puzzle: &Program, parent_solution: &Program) -> Result<Vec<(Coin, Self)>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/child_kind.rs`: `receiver_custody_p2_puzzle_hash() -> Option<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/child_kind.rs`: `subscribe() -> bool`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/coin_kind.rs`: `from_puzzle(puzzle: &Program) -> Result<Self, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/coin_kind.rs`: `from_puzzle_cached(allocator: &Allocator, puzzle: Puzzle) -> Result<Self, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/database.rs`: `async insert_nft(tx: &mut DatabaseTx<'_>, coin_state: CoinState, lineage_proof: Option<LineageProof>, info: SerializedNftInfo, metadata: Option<NftMetadata>, context: PuzzleContext) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/database.rs`: `async insert_option(tx: &mut DatabaseTx<'_>, coin_state: CoinState, lineage_proof: Option<LineageProof>, info: OptionInfo, context: OptionContext) -> Result<bool, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/database.rs`: `async insert_puzzle(tx: &mut DatabaseTx<'_>, coin_state: CoinState, info: ChildKind, context: PuzzleContext, underlying_p2_puzzle_hash: Option<Bytes32>) -> Result<bool, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/database.rs`: `async insert_transaction(db: &Database, peer: &WalletPeer, genesis_challenge: Bytes32, transaction_id: Bytes32, transaction: Transaction, aggregated_signature: Signature) -> Result<Vec<Bytes32>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/database.rs`: `async validate_wallet_coin(tx: &mut DatabaseTx<'_>, coin_id: Bytes32, info: &ChildKind) -> Result<bool, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/puzzle_context.rs`: `async fetch(peer: &WalletPeer, genesis_challenge: Bytes32, kind: &ChildKind) -> Result<Self, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/puzzle_context.rs`: `async fetch_minter_hash(peer: &WalletPeer, genesis_challenge: Bytes32, launcher_id: Bytes32) -> Result<Option<Bytes32>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/puzzle_context.rs`: `async fetch_option(peer: &WalletPeer, genesis_challenge: Bytes32, info: &OptionInfo) -> Result<Option<OptionContext>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/blocktime_queue.rs`: `new(db: Database, state: Arc<Mutex<PeerState>>, sync_sender: mpsc::Sender<SyncEvent>) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/blocktime_queue.rs`: `async start(delay: Duration) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/cat_queue.rs`: `new(db: Database, testnet: bool, sync_sender: mpsc::Sender<SyncEvent>) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/cat_queue.rs`: `async start(delay: Duration) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/nft_uri_queue.rs`: `new(db: Database, sync_sender: mpsc::Sender<SyncEvent>, network: Network) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/nft_uri_queue.rs`: `async start(delay: Duration) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/offer_queue.rs`: `new(db: Database, genesis_challenge: Bytes32, state: Arc<Mutex<PeerState>>, sync_sender: mpsc::Sender<SyncEvent>) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/offer_queue.rs`: `async start(delay: Duration) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/puzzle_queue.rs`: `new(db: Database, genesis_challenge: Bytes32, batch_size_per_peer: usize, state: Arc<Mutex<PeerState>>, sync_sender: mpsc::Sender<SyncEvent>, command_sender: mpsc::Sender<SyncCommand>) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/puzzle_queue.rs`: `async start(delay: Duration) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/transaction_queue.rs`: `new(db: Database, state: Arc<Mutex<PeerState>>, sync_sender: mpsc::Sender<SyncEvent>) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/queues/transaction_queue.rs`: `async start(delay: Duration) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager.rs`: `new(options: SyncOptions, state: Arc<Mutex<PeerState>>, wallet: Option<Arc<Wallet>>, network: Network, connector: Connector) -> (Self, mpsc::Sender<SyncCommand>, mpsc::Receiver<SyncEvent>)`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager.rs`: `async sync() -> ()`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/dns.rs`: `async lookup_all(hosts: &[String], port: u16, timeout: Duration, batch_size: usize) -> Vec<SocketAddr>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `acquire_peer() -> Option<WalletPeer>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `auto_discovered_peers() -> Vec<WalletPeer>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `ban(ip: IpAddr, duration: Duration, message: &str) -> ()`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `banned_peers() -> &HashMap<IpAddr, u64>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `is_banned(ip: IpAddr) -> bool`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `is_connected(ip: IpAddr) -> bool`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `peak() -> Option<(u32, Bytes32)>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `peak_of(ip: IpAddr) -> Option<(u32, Bytes32)>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `peer(ip: IpAddr) -> Option<&PeerInfo>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `peer_count() -> usize`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `peers() -> Vec<WalletPeer>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `peers_with_heights() -> Vec<(WalletPeer, u32)>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `remove_peer(ip: IpAddr) -> ()`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `reset() -> ()`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `update_peak(ip: IpAddr, height: u32, header_hash: Bytes32) -> ()`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/peer_state.rs`: `user_managed_peers() -> Vec<WalletPeer>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/wallet_sync.rs`: `async add_new_subscriptions(wallet: &Wallet, peer: &WalletPeer, coin_ids: Vec<Bytes32>, puzzle_hashes: Vec<Bytes32>, sync_sender: mpsc::Sender<SyncEvent>, command_sender: mpsc::Sender<SyncCommand>) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/wallet_sync.rs`: `async incremental_sync(wallet: &Wallet, coin_states: Vec<CoinState>, derive_automatically: bool, sync_sender: &mpsc::Sender<SyncEvent>, command_sender: &mpsc::Sender<SyncCommand>) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/sync_manager/wallet_sync.rs`: `async sync_wallet(wallet: Arc<Wallet>, peer: WalletPeer, state: Arc<Mutex<PeerState>>, sync_sender: mpsc::Sender<SyncEvent>, command_sender: mpsc::Sender<SyncCommand>, delta_sync: bool) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `async consume_until(f: impl Fn(SyncEvent) -> bool)`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `default_test_options() -> SyncOptions`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `async new(balance: u64) -> anyhow::Result<Self>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `async new_block_with_current_time() -> anyhow::Result<u64>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `async new_with_options(balance: u64, options: SyncOptions) -> anyhow::Result<Self>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `async next(balance: u64) -> anyhow::Result<Self>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `async next_with_options(balance: u64, options: SyncOptions) -> anyhow::Result<Self>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `async push_bundle(spend_bundle: SpendBundle) -> anyhow::Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `async resync() -> anyhow::Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `async transact(coin_spends: Vec<CoinSpend>) -> anyhow::Result<()>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `async wait_for_coins() -> ()`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/test.rs`: `async wait_for_puzzles() -> ()`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/transaction.rs`: `from_coin_spends(coin_spends: Vec<CoinSpend>) -> Result<Self, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/utils/offchain_metadata.rs`: `compute_nft_info(did_id: Option<Bytes32>, blob: &[u8]) -> ComputedNftInfo`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/utils/submit.rs`: `async submit_to_peers(peers: &[WalletPeer], spend_bundle: SpendBundle) -> Result<Status, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/utils/submit.rs`: `async submit_transaction(peer: &WalletPeer, spend_bundle: SpendBundle) -> Result<Status, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet.rs`: `async complete_spends(ctx: &mut SpendContext, deltas: &Deltas, spends: Spends) -> Result<Outputs, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet.rs`: `new(db: Database, fingerprint: u32, intermediate_pk: PublicKey, genesis_challenge: Bytes32, agg_sig_constants: AggSigConstants, change_p2_puzzle_hash: Option<Bytes32>) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet.rs`: `async prepare_spends(ctx: &mut SpendContext, selected_coin_ids: Vec<Bytes32>, actions: &[Action]) -> Result<Spends, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet.rs`: `async prepare_spends_for_selection(ctx: &mut SpendContext, selected_coin_ids: &[Bytes32]) -> Result<Spends, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet.rs`: `async select_spends(ctx: &mut SpendContext, spends: &mut Spends, actions: &[Action]) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet.rs`: `async spend(ctx: &mut SpendContext, selected_coin_ids: Vec<Bytes32>, actions: &[Action]) -> Result<Outputs, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/cats.rs`: `async issue_cat(amount: u64, fee: u64, multi_issuance_key: Option<PublicKey>) -> Result<(Vec<CoinSpend>, Bytes32), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/cats.rs`: `async send_cat(asset_id: Bytes32, amounts: Vec<(Bytes32, fee: u64, include_hint: bool, memos: Vec<Bytes>, clawback: Option<u64>) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/coin_management.rs`: `async combine(selected_coin_ids: Vec<Bytes32>, fee: u64) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/coin_management.rs`: `async split(selected_coin_ids: Vec<Bytes32>, output_count: usize, fee: u64) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/derivations.rs`: `async change_p2_puzzle_hash() -> Result<Bytes32, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/derivations.rs`: `async insert_unhardened_derivations(tx: &mut DatabaseTx<'_>, range: Range<u32>) -> Result<Vec<Bytes32>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/derivations.rs`: `async p2_puzzle_hashes(count: u32, hardened: bool, reuse: bool) -> Result<Vec<Bytes32>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/dids.rs`: `async create_did(fee: u64) -> Result<(Vec<CoinSpend>, SerializedDid), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/dids.rs`: `async normalize_dids(did_ids: Vec<Bytes32>, fee: u64) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/dids.rs`: `async transfer_dids(did_ids: Vec<Bytes32>, puzzle_hash: Bytes32, fee: u64, clawback: Option<u64>) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/memos.rs`: `calculate_memos(ctx: &mut SpendContext, hint: Hint, memos: Vec<Bytes>) -> Result<Memos, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/multi_send.rs`: `cat(asset_id: Bytes32, puzzle_hash: Bytes32, amount: u64) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/multi_send.rs`: `is_cat() -> bool`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/multi_send.rs`: `is_xch() -> bool`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/multi_send.rs`: `async multi_send(payments: Vec<MultiSendPayment>, fee: u64) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/multi_send.rs`: `xch(puzzle_hash: Bytes32, amount: u64) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/nfts.rs`: `async add_nft_uri(nft_id: Bytes32, fee: u64, uri: MetadataUpdate) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/nfts.rs`: `async assign_nfts(nft_ids: Vec<Bytes32>, did_id: Option<Bytes32>, fee: u64) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/nfts.rs`: `async bulk_mint_nfts(fee: u64, did_id: Bytes32, mints: Vec<WalletNftMint>) -> Result<(Vec<CoinSpend>, Vec<SerializedNft>), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/nfts.rs`: `async transfer_nfts(nft_ids: Vec<Bytes32>, puzzle_hash: Bytes32, fee: u64, clawback: Option<u64>) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/offer/aggregate_offer.rs`: `aggregate_offers(spend_bundles: Vec<SpendBundle>) -> SpendBundle`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/offer/aggregate_offer.rs`: `sort_offer(spend_bundle: SpendBundle) -> SpendBundle`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/offer/cancel_offer.rs`: `async cancel_offer(spend_bundle: SpendBundle, fee: u64) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/offer/make_offer.rs`: `async make_offer(offered: Offered, requested: Requested, expires_at: Option<u64>) -> Result<SpendBundle, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/offer/offer_assets.rs`: `async fetch_offer_cat_hidden_puzzle_hash(asset_id: Bytes32) -> Result<Option<Bytes32>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/offer/offer_assets.rs`: `async fetch_offer_nft_info(peer: Option<&WalletPeer>, launcher_id: Bytes32) -> Result<Option<NftOfferInfo>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/offer/offer_assets.rs`: `async fetch_offer_option_info(peer: Option<&WalletPeer>, launcher_id: Bytes32) -> Result<Option<OptionOfferInfo>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/offer/take_offer.rs`: `async take_offer(spend_bundle: SpendBundle, fee: u64) -> Result<SpendBundle, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/options.rs`: `async exercise_options(option_ids: Vec<Bytes32>, fee: u64) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/options.rs`: `async mint_option(mint: WalletOptionMint, fee: u64) -> Result<(Vec<CoinSpend>, OptionContract), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/options.rs`: `async transfer_options(option_ids: Vec<Bytes32>, puzzle_hash: Bytes32, fee: u64, clawback: Option<u64>) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/signing.rs`: `async sign_transaction(spend_bundle: SpendBundle, agg_sig_constants: &AggSigConstants, master_sk: SecretKey, partial: bool) -> Result<SpendBundle, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/xch.rs`: `async finalize_clawback(coin_ids: Vec<Bytes32>, fee: u64) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet/xch.rs`: `async send_xch(amounts: Vec<(Bytes32, fee: u64, memos: Vec<Bytes>, clawback: Option<u64>) -> Result<Vec<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async block_timestamp(height: u32) -> Result<(Bytes32, u64), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async fetch_coin(coin_id: Bytes32, genesis_challenge: Bytes32) -> Result<CoinState, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async fetch_coin_spend(coin_id: Bytes32, genesis_challenge: Bytes32) -> Result<CoinSpend, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async fetch_coins(coin_ids: Vec<Bytes32>, genesis_challenge: Bytes32) -> Result<Vec<CoinState>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async fetch_optional_coin(coin_id: Bytes32, genesis_challenge: Bytes32) -> Result<Option<CoinState>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async fetch_optional_coin_spend(coin_id: Bytes32, genesis_challenge: Bytes32) -> Result<Option<CoinSpend>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async fetch_puzzle_solution(coin_id: Bytes32, spent_height: u32) -> Result<(Program, Program), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `new(peer: Peer) -> Self`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async request_peers() -> Result<RespondPeers, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async send_transaction(spend_bundle: SpendBundle) -> Result<TransactionAck, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `socket_addr() -> SocketAddr`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async subscribe_coins(coin_ids: Vec<Bytes32>, previous_height: Option<u32>, header_hash: Bytes32) -> Result<Vec<CoinState>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async subscribe_puzzles(puzzle_hashes: Vec<Bytes32>, previous_height: Option<u32>, header_hash: Bytes32, filters: CoinStateFilters) -> Result<RespondPuzzleState, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async try_fetch_singleton_child(coin_id: Bytes32) -> Result<Option<CoinState>, WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async unsubscribe() -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `async unsubscribe_coins(coin_ids: Vec<Bytes32>) -> Result<(), WalletError>`
  Notes: No doc comment extracted.
- `crates/sage-wallet/src/wallet_peer.rs`: `with_pending(pending_coin_states: HashMap<Bytes32, pending_coin_spends: HashMap<Bytes32) -> Self`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/action_system.rs`: `async create_transaction(req: CreateTransaction) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/actions.rs`: `async increase_derivation_index(req: IncreaseDerivationIndex) -> Result<IncreaseDerivationIndexResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/actions.rs`: `async redownload_nft(req: RedownloadNft) -> Result<RedownloadNftResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/actions.rs`: `async resync_cat(req: ResyncCat) -> Result<ResyncCatResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/actions.rs`: `async update_cat(req: UpdateCat) -> Result<UpdateCatResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/actions.rs`: `async update_did(req: UpdateDid) -> Result<UpdateDidResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/actions.rs`: `async update_nft(req: UpdateNft) -> Result<UpdateNftResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/actions.rs`: `async update_nft_collection(req: UpdateNftCollection) -> Result<UpdateNftCollectionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/actions.rs`: `async update_option(req: UpdateOption) -> Result<UpdateOptionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async check_address(req: CheckAddress) -> Result<CheckAddressResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_all_cats(_req: GetAllCats) -> Result<GetAllCatsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_are_coins_spendable(req: GetAreCoinsSpendable) -> Result<GetAreCoinsSpendableResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_cats(_req: GetCats) -> Result<GetCatsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_coins(req: GetCoins) -> Result<GetCoinsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_coins_by_ids(req: GetCoinsByIds) -> Result<GetCoinsByIdsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_database_stats(_req: GetDatabaseStats) -> Result<GetDatabaseStatsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_derivations(req: GetDerivations) -> Result<GetDerivationsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_dids(_req: GetDids) -> Result<GetDidsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_minter_did_ids(req: GetMinterDidIds) -> Result<GetMinterDidIdsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_nft(req: GetNft) -> Result<GetNftResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_nft_collection(req: GetNftCollection) -> Result<GetNftCollectionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_nft_collections(req: GetNftCollections) -> Result<GetNftCollectionsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_nft_data(req: GetNftData) -> Result<GetNftDataResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_nft_icon(req: GetNftIcon) -> Result<GetNftIconResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_nft_thumbnail(req: GetNftThumbnail) -> Result<GetNftThumbnailResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_nfts(req: GetNfts) -> Result<GetNftsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_option(req: GetOption) -> Result<GetOptionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_options(req: GetOptions) -> Result<GetOptionsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_pending_transactions(_req: GetPendingTransactions) -> Result<GetPendingTransactionsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_spendable_coin_count(req: GetSpendableCoinCount) -> Result<GetSpendableCoinCountResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_sync_status(_req: GetSyncStatus) -> Result<GetSyncStatusResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_token(req: GetToken) -> Result<GetTokenResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_transaction(req: GetTransaction) -> Result<GetTransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async get_transactions(req: GetTransactions) -> Result<GetTransactionsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `get_version(_req: GetVersion) -> Result<GetVersionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async is_asset_owned(req: IsAssetOwned) -> Result<IsAssetOwnedResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/data.rs`: `async perform_database_maintenance(req: PerformDatabaseMaintenance) -> Result<PerformDatabaseMaintenanceResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `delete_database(req: DeleteDatabase) -> Result<DeleteDatabaseResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `delete_key(req: DeleteKey) -> Result<DeleteKeyResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `generate_mnemonic(req: GenerateMnemonic) -> Result<GenerateMnemonicResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `get_key(req: GetKey) -> Result<GetKeyResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `get_keys(_req: GetKeys) -> Result<GetKeysResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `get_secret_key(req: GetSecretKey) -> Result<GetSecretKeyResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `async import_key(req: ImportKey) -> Result<ImportKeyResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `async login(req: Login) -> Result<LoginResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `async logout(_req: Logout) -> Result<LogoutResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `rename_key(req: RenameKey) -> Result<RenameKeyResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `async resync(req: Resync) -> Result<ResyncResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/keys.rs`: `set_wallet_emoji(req: SetWalletEmoji) -> Result<SetWalletEmojiResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/offers.rs`: `async cancel_offer(req: CancelOffer) -> Result<CancelOfferResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/offers.rs`: `async cancel_offers(req: CancelOffers) -> Result<CancelOffersResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/offers.rs`: `combine_offers(req: CombineOffers) -> Result<CombineOffersResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/offers.rs`: `async delete_offer(req: DeleteOffer) -> Result<DeleteOfferResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/offers.rs`: `async get_offer(req: GetOffer) -> Result<GetOfferResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/offers.rs`: `async get_offers(_req: GetOffers) -> Result<GetOffersResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/offers.rs`: `async get_offers_for_asset(req: GetOffersForAsset) -> Result<GetOffersForAssetResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/offers.rs`: `async import_offer(req: ImportOffer) -> Result<ImportOfferResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/offers.rs`: `async make_offer(req: MakeOffer) -> Result<MakeOfferResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/offers.rs`: `async take_offer(req: TakeOffer) -> Result<TakeOfferResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/offers.rs`: `async view_offer(req: ViewOffer) -> Result<ViewOfferResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `async add_peer(req: AddPeer) -> Result<AddPeerResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `get_network(_req: GetNetwork) -> Result<GetNetworkResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `get_networks(_req: GetNetworks) -> Result<GetNetworksResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `async get_peers(_req: GetPeers) -> Result<GetPeersResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `async remove_peer(req: RemovePeer) -> Result<RemovePeerResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `async set_change_address(req: SetChangeAddress) -> Result<SetChangeAddressResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `set_delta_sync(req: SetDeltaSync) -> Result<SetDeltaSyncResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `set_delta_sync_override(req: SetDeltaSyncOverride) -> Result<SetDeltaSyncOverrideResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `async set_discover_peers(req: SetDiscoverPeers) -> Result<SetDiscoverPeersResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `async set_network(req: SetNetwork) -> Result<SetNetworkResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `async set_network_override(req: SetNetworkOverride) -> Result<SetNetworkOverrideResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/settings.rs`: `async set_target_peers(req: SetTargetPeers) -> Result<SetTargetPeersResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/themes.rs`: `async delete_user_theme(req: DeleteUserTheme) -> Result<DeleteUserThemeResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/themes.rs`: `async get_user_theme(req: GetUserTheme) -> Result<GetUserThemeResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/themes.rs`: `async get_user_themes(_req: GetUserThemes) -> Result<GetUserThemesResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/themes.rs`: `async save_user_theme(req: SaveUserTheme) -> Result<SaveUserThemeResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async add_nft_uri(req: AddNftUri) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async assign_nfts_to_did(req: AssignNftsToDid) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async auto_combine_cat(req: AutoCombineCat) -> Result<AutoCombineCatResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async auto_combine_xch(req: AutoCombineXch) -> Result<AutoCombineXchResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async bulk_mint_nfts(req: BulkMintNfts) -> Result<BulkMintNftsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async bulk_send_cat(req: BulkSendCat) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async bulk_send_xch(req: BulkSendXch) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async combine(req: Combine) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async create_did(req: CreateDid) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async exercise_options(req: ExerciseOptions) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async finalize_clawback(req: FinalizeClawback) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async issue_cat(req: IssueCat) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async mint_option(req: MintOption) -> Result<MintOptionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async multi_send(req: MultiSend) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async normalize_dids(req: NormalizeDids) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async send_cat(req: SendCat) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async send_xch(req: SendXch) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async sign_coin_spends(req: SignCoinSpends) -> Result<SignCoinSpendsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async split(req: Split) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async submit_transaction(req: SubmitTransaction) -> Result<SubmitTransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async transfer_dids(req: TransferDids) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async transfer_nfts(req: TransferNfts) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async transfer_options(req: TransferOptions) -> Result<TransactionResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/transactions.rs`: `async view_coin_spends(req: ViewCoinSpends) -> Result<ViewCoinSpendsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/wallet_connect.rs`: `async filter_unlocked_coins(req: FilterUnlockedCoins) -> Result<FilterUnlockedCoinsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/wallet_connect.rs`: `async get_asset_coins(req: GetAssetCoins) -> Result<GetAssetCoinsResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/wallet_connect.rs`: `async send_transaction_immediately(req: SendTransactionImmediately) -> Result<SendTransactionImmediatelyResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/wallet_connect.rs`: `async sign_message_by_address(req: SignMessageByAddress) -> Result<SignMessageByAddressResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/endpoints/wallet_connect.rs`: `async sign_message_with_public_key(req: SignMessageWithPublicKey) -> Result<SignMessageWithPublicKeyResponse>`
  Notes: No doc comment extracted.
- `crates/sage/src/error.rs`: `kind() -> ErrorKind`
  Notes: No doc comment extracted.
- `crates/sage/src/peers.rs`: `from_bytes(bytes: &[u8]) -> bincode::Result<Self>`
  Notes: No doc comment extracted.
- `crates/sage/src/peers.rs`: `to_bytes() -> bincode::Result<Vec<u8>>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `async connect_to_database(fingerprint: u32) -> Result<SqlitePool>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `async initialize() -> Result<mpsc::Receiver<SyncEvent>>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `network() -> &Network`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `network_id() -> String`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `new(path: &Path, test: bool) -> Self`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `parse_address(input: String) -> Result<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `save_config() -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `save_keychain() -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `async save_peers() -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `async setup_peers() -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `async switch_network() -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `async switch_wallet() -> Result<()>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `wallet() -> Result<Arc<Wallet>>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `wallet_config() -> Option<&sage_config::Wallet>`
  Notes: No doc comment extracted.
- `crates/sage/src/sage.rs`: `wallet_db_path(fingerprint: u32) -> Result<PathBuf>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/cache.rs`: `async cache_cat(asset_id: Bytes32, hidden_puzzle_hash: Option<Bytes32>) -> Result<Asset>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/cache.rs`: `async cache_nft(allocator: &Allocator, launcher_id: Bytes32, nft_metadata: NodePtr, confirmation_info: &mut ConfirmationInfo) -> Result<Asset>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/cache.rs`: `async cache_option(launcher_id: Bytes32) -> Result<Asset>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/confirmation.rs`: `async extract_nft_data(db: Option<&Database>, onchain_metadata: Option<NftMetadata>, cache: &ConfirmationInfo) -> Result<ExtractedNftData>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/confirmation.rs`: `json_bundle(spend_bundle: &SpendBundle) -> SpendBundleJson`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/confirmation.rs`: `json_coin(coin: &Coin) -> CoinJson`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/confirmation.rs`: `json_spend(coin_spend: &CoinSpend) -> CoinSpendJson`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/confirmation.rs`: `rust_bundle(spend_bundle: SpendBundleJson) -> Result<SpendBundle>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/confirmation.rs`: `rust_coin(coin: CoinJson) -> Result<Coin>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/confirmation.rs`: `rust_spend(coin_spend: CoinSpendJson) -> Result<CoinSpend>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/conversions.rs`: `address_kind(p2_puzzle_hash: Option<Bytes32>) -> AddressKind`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/conversions.rs`: `encode_asset(asset: Asset) -> Result<sage_api::Asset>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/conversions.rs`: `encode_asset_id(hash: Bytes32, kind: AssetKind) -> Result<Option<String>>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/conversions.rs`: `encode_asset_kind(kind: AssetKind) -> sage_api::AssetKind`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/offer_status.rs`: `offer_expiration(allocator: &mut Allocator, offer: &Offer) -> Result<OfferExpiration>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_amount(input: Amount) -> Result<u64>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_any_asset_id(input: String) -> Result<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_asset_id(input: String) -> Result<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_coin_id(input: String) -> Result<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_coin_ids(input: Vec<String>) -> Result<Vec<Bytes32>>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_collection_id(input: String) -> Result<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_did_id(input: String) -> Result<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_hash(input: String) -> Result<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_memos(input: Vec<String>) -> Result<Vec<Bytes>>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_nft_id(input: String) -> Result<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_offer_id(input: String) -> Result<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_option_id(input: String) -> Result<Bytes32>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_program(input: String) -> Result<Program>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_public_key(input: String) -> Result<PublicKey>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_signature(input: String) -> Result<Signature>`
  Notes: No doc comment extracted.
- `crates/sage/src/utils/parse.rs`: `parse_signature_message(input: String) -> Result<Bytes>`
  Notes: Parse a signature message.  It takes a string and returns a Bytes object.  This function supports hex strings with or without a 0x prefix. It also supports non-hex strings.
- `src-tauri/src/app_state.rs`: `async initialize(app_handle: AppHandle, sage: &mut Sage) -> Result<()>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async default_wallet_config(state: State<'_) -> Result<WalletDefaults>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async download_cni_offercode(code: String) -> Result<String>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async endpoint(state: State<'_, req: Endpoint) -> Result<EndpointResponse>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async get_logs(state: State<'_) -> Result<Vec<LogFile>>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async get_rpc_run_on_startup(state: State<'_) -> Result<bool>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async initialize(app_handle: AppHandle, state: State<'_, initialized: State<'_, rpc_task: State<'_) -> Result<()>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async is_rpc_running(rpc_task: State<'_) -> Result<bool>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async move_key(state: State<'_, fingerprint: u32, index: u32) -> Result<()>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async network_config(state: State<'_) -> Result<NetworkConfig>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async set_rpc_run_on_startup(state: State<'_, run_on_startup: bool) -> Result<()>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async start_rpc_server(state: State<'_, rpc_task: State<'_) -> Result<()>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async stop_rpc_server(rpc_task: State<'_) -> Result<()>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async switch_wallet(state: State<'_) -> Result<()>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async validate_address(state: State<'_, address: String) -> Result<bool>`
  Notes: No doc comment extracted.
- `src-tauri/src/commands.rs`: `async wallet_config(state: State<'_, fingerprint: u32) -> Result<Option<Wallet>>`
  Notes: No doc comment extracted.
- `src-tauri/src/lib.rs`: `run() -> ()`
  Notes: No doc comment extracted.
- `tauri-plugin-sage/src/desktop.rs`: `get_ndef_payloads() -> crate::Result<GetNdefPayloadsResponse>`
  Notes: No doc comment extracted.
- `tauri-plugin-sage/src/desktop.rs`: `is_ndef_available() -> crate::Result<IsNdefAvailableResponse>`
  Notes: No doc comment extracted.
- `tauri-plugin-sage/src/mobile.rs`: `get_ndef_payloads() -> crate::Result<GetNdefPayloadsResponse>`
  Notes: No doc comment extracted.
- `tauri-plugin-sage/src/mobile.rs`: `is_ndef_available() -> crate::Result<IsNdefAvailableResponse>`
  Notes: No doc comment extracted.

## Exported TypeScript Function List
- `src/components/AddressItem.tsx`: `AddressItem({
  label,
  address,
  className = '',
  hideLabel = false,
  inputClassName,
  truncateMiddle = false,
}: AddressItemProps)`
- `src/components/AdvancedTransactionSummary.tsx`: `AdvancedTransactionSummary({
  summary,
}: AdvancedTransactionSummaryProps)`
- `src/components/AdvancedTransactionSummary.tsx`: `calculateTransaction(xch: Unit,
  summary: TransactionSummary,)`
- `src/components/AmountCell.tsx`: `AmountCell({ amount, assetKind, precision }: AmountCellProps)`
- `src/components/AssetCoin.tsx`: `AssetCoin({ asset, amount, coinId }: AssetCoinProps)`
- `src/components/AssetIcon.tsx`: `AssetIcon({
  asset,
  size = 'sm',
  className = '',
}: AssetIconProps)`
- `src/components/AssetLink.tsx`: `AssetLink({ asset, className = '' }: AssetLinkProps)`
- `src/components/Assets.tsx`: `Assets({ assets, catPresence = {} }: AssetsProps)`
- `src/components/AssignNftDialog.tsx`: `AssignNftDialog({
  title,
  open,
  setOpen,
  onSubmit,
  children,
}: PropsWithChildren<AssignNftDialogProps>)`
- `src/components/CardSizeToggle.tsx`: `CardSizeToggle({ size, onChange }: CardSizeToggleProps)`
- `src/components/ClawbackCoinsCard.tsx`: `ClawbackCoinsCard({
  asset,
  setResponse,
  selectedCoins,
  setSelectedCoins,
}: ClawbackCoinsCardProps)`
- `src/components/CopyBox.tsx`: `CopyBox(props: CopyBoxProps)`
- `src/components/CopyButton.tsx`: `CopyButton({
  value,
  className,
  onCopy,
  'aria-label': ariaLabel,
}: CopyButtonProps)`
- `src/components/EmojiPicker.tsx`: `EmojiPicker({
  value,
  onChange,
  disabled = false,
  placeholder = 'Choose emoji',
  className = '',
  open,
  onOpenChange,
  children,
}: EmojiPickerProps)`
- `src/components/FeeOnlyDialog.tsx`: `FeeOnlyDialog({
  title,
  open,
  setOpen,
  onSubmit,
  submitButtonLabel = t`Transfer`,
  children,
}: PropsWithChildren<FeeOnlyDialogProps>)`
- `src/components/LabeledItem.tsx`: `LabeledItem({
  label,
  className = '',
  content,
  onClick,
  children,
}: LabeledItemProps)`
- `src/components/Layout.tsx`: `FullLayout(props: LayoutProps)`
- `src/components/Loading.tsx`: `Loading({
  size = 24,
  text,
  className,
  ...props
}: LoadingProps)`
- `src/components/MarketplaceCard.tsx`: `MarketplaceCard({
  offer,
  offerId,
  offerSummary,
  network,
  marketplace,
}: MarketplaceCardProps)`
- `src/components/MultiSelectActions.tsx`: `MultiSelectActions({
  selected,
  nfts: propNfts,
  thumbnails: propThumbnails,
  onConfirm,
}: MultiSelectActionsProps)`
- `src/components/Nav.tsx`: `BottomNav({ isCollapsed }: NavProps)`
- `src/components/Nav.tsx`: `TopNav({ isCollapsed }: NavProps)`
- `src/components/NavLink.tsx`: `NavLink({
  url,
  children,
  isCollapsed,
  message,
  customTooltip,
  ariaCurrent,
}: NavLinkProps)`
- `src/components/NftCard.tsx`: `NftCard({ nft, updateNfts, selectionState }: NftCardProps)`
- `src/components/NftCardList.tsx`: `NftCardList({
  collectionId,
  ownerDid,
  minterDid,
  group,
  nfts,
  collections,
  ownerDids,
  minterDids,
  updateNfts,
  page,
  multiSelect = false,
  selected = [],
  setSelected,
  addError,
  children,
  cardSize = CardSize.Large,
  setSplitNftOffers,
}: NftCardListProps)`
- `src/components/NftGroupCard.tsx`: `NftGroupCard({
  type,
  groupMode,
  item,
  updateNfts,
  page,
  onToggleVisibility,
  isLoading,
  error,
  isPlaceHolder = false,
  setSplitNftOffers,
}: NftGroupCardProps)`
- `src/components/NftOptions.tsx`: `NftOptions({
  isCollection,
  params: { sort, group, showHidden, query, cardSize },
  setParams,
  multiSelect,
  setMultiSelect,
  className,
  onExport,
  renderPagination,
}: NftOptionsProps)`
- `src/components/NftPageTitle.tsx`: `NftPageTitle(props: NftPageTitleProps)`
- `src/components/NumberFormat.tsx`: `NumberFormat({
  value,
  style = 'decimal',
  currency,
  minimumFractionDigits,
  maximumFractionDigits,
}: NumberFormatProps)`
- `src/components/OfferCard.tsx`: `OfferCard({
  offerId,
  offer,
  status,
  creationTimestamp,
  summary: offerSummary,
  content,
}: OfferCardProps)`
- `src/components/OfferRowCard.tsx`: `OfferRowCard({ record, refresh }: OfferRowCardProps)`
- `src/components/OfferSummaryCard.tsx`: `OfferSummaryCard({ record, content }: OfferSummaryCardProps)`
- `src/components/OptionCard.tsx`: `OptionCard({ option, actionHandlers }: OptionCardProps)`
- `src/components/OptionColumns.tsx`: `columns(actionHandlers?: OptionActionHandlers,
): ColumnDef<OptionRecord>[] => [
  {
    accessorKey: 'name',
    header: ()`
- `src/components/OptionGridView.tsx`: `OptionGridView({
  options,
  updateOptions,
  showHidden,
}: OptionGridViewProps)`
- `src/components/OptionListView.tsx`: `OptionListView({
  options,
  actionHandlers,
}: OptionListViewProps)`
- `src/components/OptionOptions.tsx`: `OptionOptions({
  query,
  setQuery,
  viewMode,
  setViewMode,
  sortMode,
  setSortMode,
  ascending,
  setAscending,
  showHiddenOptions,
  setShowHiddenOptions,
  handleSearch,
  className,
  onExport,
}: OptionOptionsProps)`
- `src/components/OwnedCoinsCard.tsx`: `OwnedCoinsCard({
  asset,
  setResponse,
  selectedCoins,
  setSelectedCoins,
}: OwnedCoinsCardProps)`
- `src/components/Pagination.tsx`: `Pagination({
  page,
  total,
  canLoadMore,
  isLoading,
  onPageChange,
  pageSize,
  onPageSizeChange,
  pageSizeOptions = [8, 16, 32, 64],
  compact = false,
}: PaginationProps)`
- `src/components/QRCodeDialog.tsx`: `QRCodeDialog({
  isOpen,
  onClose,
  asset,
  qr_code_contents,
  title,
  description,
}: QRCodeDialogProps)`
- `src/components/ReceiveAddress.tsx`: `ReceiveAddress({ className }: { className?: string })`
- `src/components/SimplePagination.tsx`: `SimplePagination({
  currentPage,
  pageCount,
  setCurrentPage,
  className = '',
  size = 'default',
  align = 'between',
  actions,
}: SimplePaginationProps)`
- `src/components/ThemeCard.tsx`: `ThemeCard({
  theme,
  currentTheme,
  isSelected,
  onSelect,
  variant = 'default',
  className = '',
}: ThemeCardProps)`
- `src/components/ThemeSelector.tsx`: `ThemeSelector()`
- `src/components/ThemeSelector.tsx`: `ThemeSelectorSimple()`
- `src/components/TokenCard.tsx`: `TokenCard({
  asset,
  balanceInUsd,
  onRedownload,
  onVisibilityChange,
  onUpdate,
}: TokenCardProps)`
- `src/components/TokenColumns.tsx`: `columns(actionHandlers?: TokenActionHandlers,
): ColumnDef<PricedTokenRecord>[] => [
  {
    id: 'icon',
    enableSorting: false,
    header: ()`
- `src/components/TokenGridView.tsx`: `TokenGridView({ tokens, actionHandlers }: TokenGridViewProps)`
- `src/components/TokenListView.tsx`: `TokenListView({ tokens, actionHandlers }: TokenListViewProps)`
- `src/components/TokenOptions.tsx`: `TokenOptions({
  query,
  setQuery,
  viewMode,
  setViewMode,
  sortMode,
  setSortMode,
  showZeroBalanceTokens: showZeroBalances,
  setShowZeroBalanceTokens: setShowZeroBalances,
  handleSearch,
  showHiddenCats,
  setShowHiddenCats,
  className,
  onExport,
}: TokenOptionsProps)`
- `src/components/TransactionFailureTest.tsx`: `TransactionFailureTest()`
- `src/components/TransactionListView.tsx`: `TransactionListView({
  transactions,
  onSortingChange,
  isLoading = false,
  summarized = true,
}: {
  transactions: TransactionRecord[];
  onSortingChange?: (ascending: boolean)`
- `src/components/TransactionOptions.tsx`: `TransactionOptions({
  params,
  onParamsChange,
  className,
  renderPagination,
  onExport,
}: TransactionOptionsProps)`
- `src/components/TransferDialog.tsx`: `TransferDialog({
  title,
  open,
  setOpen,
  onSubmit,
  children,
}: PropsWithChildren<TransferDialogProps>)`
- `src/components/ViewToggle.tsx`: `ViewToggle({ view, onChange }: ViewToggleProps)`
- `src/components/WalletCard.tsx`: `WalletCard({
  draggable,
  info,
  keys,
  setKeys,
}: WalletCardProps)`
- `src/components/WalletSwitcher.tsx`: `WalletSwitcher({ isCollapsed, wallet }: WalletSwitcherProps)`
- `src/components/confirmations/AddUrlConfirmation.tsx`: `AddUrlConfirmation({
  nft,
  thumbnail,
  url,
  kind,
}: AddUrlConfirmationProps)`
- `src/components/confirmations/CancelOfferConfirmation.tsx`: `CancelOfferConfirmation({
  offers,
  fee,
}: CancelOfferConfirmationProps)`
- `src/components/confirmations/ConfirmationAlert.tsx`: `ConfirmationAlert({
  icon: Icon,
  title,
  children,
  variant = 'info',
}: ConfirmationAlertProps)`
- `src/components/confirmations/ConfirmationCard.tsx`: `ConfirmationCard({
  icon,
  title,
  children,
  className = '',
}: ConfirmationCardProps)`
- `src/components/confirmations/CreateProfileConfirmation.tsx`: `CreateProfileConfirmation({
  name,
}: CreateProfileConfirmationProps)`
- `src/components/confirmations/DidConfirmation.tsx`: `DidConfirmation({ type, dids, address }: DidConfirmationProps)`
- `src/components/confirmations/MintOptionConfirmation.tsx.tsx`: `MintOptionConfirmation({
  underlyingAsset,
  underlyingAmount,
  strikeAsset,
  strikeAmount,
  expirationSeconds,
}: MintOptionConfirmationProps)`
- `src/components/confirmations/NftConfirmation.tsx`: `NftConfirmation({
  type,
  nfts,
  thumbnails,
  address,
  profileId,
}: NftConfirmationProps)`
- `src/components/confirmations/OptionConfirmation.tsx`: `OptionConfirmation({
  type,
  options,
  address,
}: OptionConfirmationProps)`
- `src/components/confirmations/TakeOfferConfirmation.tsx`: `TakeOfferConfirmation({ offer }: TakeOfferConfirmationProps)`
- `src/components/confirmations/TokenConfirmation.tsx`: `TokenConfirmation({
  type,
  coins,
  outputCount,
  ticker,
  precision,
  name,
  amount,
  currentMemo,
}: TokenConfirmationProps)`
- `src/components/dialogs/CancelOfferDialog.tsx`: `CancelOfferDialog({
  open,
  onOpenChange,
  form,
  onSubmit,
  title,
  description,
  feeLabel,
}: CancelOfferDialogProps)`
- `src/components/dialogs/DeleteOfferDialog.tsx`: `DeleteOfferDialog({
  open,
  onOpenChange,
  onDelete,
  offerCount,
}: DeleteOfferDialogProps)`
- `src/components/dialogs/MakeOfferConfirmationDialog.tsx`: `MakeOfferConfirmationDialog({
  open,
  onOpenChange,
  onConfirm,
  offerState,
  splitNftOffers,
  fee,
  enabledMarketplaces,
  setEnabledMarketplaces,
}: MakeOfferConfirmationDialogProps)`
- `src/components/dialogs/MigrationDialog.tsx`: `MigrationDialog({
  open,
  onOpenChange,
  onCancel,
  onConfirm,
}: MigrationDialogProps)`
- `src/components/dialogs/NfcScanDialog.tsx`: `NfcScanDialog({ open, onOpenChange }: NfcScanDialogProps)`
- `src/components/dialogs/OfferCreationProgressDialog.tsx`: `OfferCreationProgressDialog({
  open,
  onOpenChange,
  offerState,
  splitNftOffers,
  enabledMarketplaces,
  clearOfferState,
  isSwap,
}: OfferCreationProgressDialogProps)`
- `src/components/dialogs/ResyncDialog.tsx`: `ResyncDialog({
  open,
  setOpen,
  networkId,
  submit,
}: ResyncDialogProps)`
- `src/components/dialogs/ViewOfferDialog.tsx`: `ViewOfferDialog({
  open,
  onOpenChange,
  offerString,
  setOfferString,
  onSubmit,
}: ViewOfferDialogProps)`
- `src/components/selectors/AssetSelector.tsx`: `AssetSelector({
  offering,
  prefix,
  assets,
  setAssets,
  splitNftOffers,
  setSplitNftOffers,
  fee,
}: AssetSelectorProps)`
- `src/components/selectors/NftSelector.tsx`: `NftSelector({
  value,
  onChange,
  disabled = [],
  className,
}: NftSelectorProps)`
- `src/components/selectors/OptionSelector.tsx`: `OptionSelector({
  value,
  onChange,
  disabled = [],
  className,
}: OptionSelectorProps)`
- `src/components/selectors/TokenSelector.tsx`: `TokenSelector({
  value,
  onChange,
  disabled = [],
  className,
  hideZeroBalance = false,
  showAllCats = false,
  includeXch = false,
}: TokenSelectorProps)`
- `src/contexts/BiometricContext.tsx`: `BiometricProvider({ children }: { children: ReactNode })`
- `src/contexts/ErrorContext.tsx`: `ErrorProvider({ children }: { children: ReactNode })`
- `src/contexts/LanguageContext.tsx`: `LanguageProvider({
  children,
  locale,
  setLocale,
}: {
  children: ReactNode;
  locale: SupportedLanguage;
  setLocale: (locale: SupportedLanguage)`
- `src/contexts/LanguageContext.tsx`: `getBrowserLanguage(): SupportedLanguage => {
  const browserLang = navigator.language;
  return SUPPORTED_LANGUAGES.includes(browserLang as SupportedLanguage)
    ? (browserLang as SupportedLanguage)
    : 'en-US';
};

export function LanguageProvider({
  children,
  locale,
  setLocale,
}: {
  children: ReactNode;
  locale: SupportedLanguage;
  setLocale: (locale: SupportedLanguage)`
- `src/contexts/LanguageContext.tsx`: `useLanguage()`
- `src/contexts/PeerContext.tsx`: `PeerProvider({ children }: { children: ReactNode })`
- `src/contexts/PriceContext.tsx`: `PriceProvider({ children }: { children: ReactNode })`
- `src/contexts/SafeAreaContext.tsx`: `SafeAreaProvider({ children }: { children: React.ReactNode })`
- `src/contexts/SafeAreaContext.tsx`: `useInsets()`
- `src/contexts/WalletConnectContext.tsx`: `WalletConnectProvider({ children }: { children: ReactNode })`
- `src/contexts/WalletContext.tsx`: `WalletProvider({ children }: { children: React.ReactNode })`
- `src/contexts/WalletContext.tsx`: `useWallet()`
- `src/hooks/useBiometric.ts`: `useBiometric()`
- `src/hooks/useDefaultClawback.ts`: `useDefaultClawback()`
- `src/hooks/useDefaultFee.ts`: `useDefaultFee()`
- `src/hooks/useDefaultOfferExpiry.ts`: `useDefaultOfferExpiry()`
- `src/hooks/useDerivationState.ts`: `useDerivationState(hardened = false)`
- `src/hooks/useDids.ts`: `useDids()`
- `src/hooks/useErrors.ts`: `useErrors()`
- `src/hooks/useIntersectionObserver.ts`: `useIntersectionObserver(elementRef: React.RefObject<Element>,
  callback: IntersectionObserverCallback,
  options: IntersectionObserverInit = { threshold: 0 },)`
- `src/hooks/useLongPress.ts`: `useLongPress(onLongPress: (event: React.MouseEvent | React.TouchEvent)`
- `src/hooks/useNftData.ts`: `useNftData(params: NftDataParams)`
- `src/hooks/useNftParams.ts`: `useNftParams()`
- `src/hooks/useOfferProcessor.ts`: `useOfferProcessor({
  offerState,
  splitNftOffers,
  onProcessingEnd,
  onProgress,
}: UseOfferProcessorProps)`
- `src/hooks/useOptionActions.tsx`: `useOptionActions(updateOptions: ()`
- `src/hooks/useOptionParams.ts`: `parseSortMode(mode: string)`
- `src/hooks/useOptionParams.ts`: `useOptionParams()`
- `src/hooks/usePeers.ts`: `usePeers()`
- `src/hooks/usePrices.ts`: `usePrices()`
- `src/hooks/useScannerOrClipboard.ts`: `useScannerOrClipboard(onScanResult: (text: string)`
- `src/hooks/useTokenParams.ts`: `parseSortMode(view: string)`
- `src/hooks/useTokenParams.ts`: `useTokenParams()`
- `src/hooks/useTransactionFailures.ts`: `useTransactionFailures()`
- `src/hooks/useTransactionsParams.ts`: `useTransactionsParams()`
- `src/hooks/useWalletConnect.ts`: `useWalletConnect()`
- `src/i18n.ts`: `formatNumber({
  value,
  style = 'decimal',
  currency,
  minimumFractionDigits,
  maximumFractionDigits,
}: NumberFormatProps)`
- `src/i18n.ts`: `loadCatalog(locale: string)`
- `src/lib/exportNfts.ts`: `exportNfts(params: ExportParams)`
- `src/lib/exportNfts.ts`: `queryNfts(params: ExportParams,
  limit: number,
  offset: number,)`
- `src/lib/exportOptions.ts`: `exportOptions(options: OptionRecord[])`
- `src/lib/exportText.ts`: `exportText(text: string,
  title: string,
  type: ExportType = ExportType.CSV,)`
- `src/lib/exportTokens.ts`: `exportTokens(tokens: PricedTokenRecord[])`
- `src/lib/exportTransactions.ts`: `exportTransactions(params: TransactionQueryParams)`
- `src/lib/exportTransactions.ts`: `queryTransactions(params: TransactionQueryParams,)`
- `src/lib/formTypes.ts`: `amount(precision: number)`
- `src/lib/formTypes.ts`: `positiveAmount(precision: number)`
- `src/lib/marketplaces.ts`: `getMintGardenProfile(did: string)`
- `src/lib/nftUri.ts`: `getBaseMimeType(mimeType: string | null)`
- `src/lib/nftUri.ts`: `isAudio(mimeType: string | null)`
- `src/lib/nftUri.ts`: `isImage(mimeType: string | null)`
- `src/lib/nftUri.ts`: `isJson(mimeType: string | null)`
- `src/lib/nftUri.ts`: `isText(mimeType: string | null)`
- `src/lib/nftUri.ts`: `isVideo(mimeType: string | null)`
- `src/lib/nftUri.ts`: `nftUri(mimeType: string | null, data: string | null)`
- `src/lib/offerData.ts`: `fetchOfferedDexieOffersFromNftId(id: string,
  network: string | null,)`
- `src/lib/offerData.ts`: `fetchRequestedDexieOffersFromNftId(id: string,
  network: string | null,)`
- `src/lib/offerData.ts`: `resolveOfferData(text: string)`
- `src/lib/offerUpload.ts`: `dexieLink(offerId: string, testnet: boolean)`
- `src/lib/offerUpload.ts`: `getOfferHash(offer: string)`
- `src/lib/offerUpload.ts`: `isDexieSupported(state: OfferState)`
- `src/lib/offerUpload.ts`: `isDexieSupportedForSummary(summary: OfferSummary)`
- `src/lib/offerUpload.ts`: `isMintGardenSupported(state: OfferState, isSplitting = false)`
- `src/lib/offerUpload.ts`: `isMintGardenSupportedForSummary(summary: OfferSummary)`
- `src/lib/offerUpload.ts`: `isOneSideOffer(summary: OfferSummary | OfferState)`
- `src/lib/offerUpload.ts`: `mintGardenLink(offerHash: string, testnet: boolean)`
- `src/lib/offerUpload.ts`: `offerIsOnDexie(offerId: string,
  isTestnet: boolean,)`
- `src/lib/offerUpload.ts`: `offerIsOnMintGarden(offer: string,
  isTestnet: boolean,)`
- `src/lib/offerUpload.ts`: `uploadToDexie(offer: string,
  testnet: boolean,)`
- `src/lib/offerUpload.ts`: `uploadToMintGarden(offer: string,
  testnet: boolean,)`
- `src/lib/themes.ts`: `discoverThemes()`
- `src/lib/themes.ts`: `hasTag(theme: Theme, tag: string)`
- `src/lib/themes.ts`: `resolveThemeImage(themeName: string,
  imagePath: string,)`
- `src/lib/utils.ts`: `addressInfo(address: string)`
- `src/lib/utils.ts`: `cn(...inputs: ClassValue[])`
- `src/lib/utils.ts`: `decodeHexMessage(hexMessage: string)`
- `src/lib/utils.ts`: `emptyNftRecord(nftId: string)`
- `src/lib/utils.ts`: `formatAddress(address: string,
  chars = 8,
  trailingChars: number = chars,)`
- `src/lib/utils.ts`: `formatTimestamp(timestamp: number | null,
  dateStyle = 'medium',
  timeStyle: string = dateStyle,)`
- `src/lib/utils.ts`: `formatUsdPrice(price: number)`
- `src/lib/utils.ts`: `fromMojos(amount: string | number | BigNumber,
  precision: number,)`
- `src/lib/utils.ts`: `getAssetDisplayName(name: string | null,
  ticker: string | null,
  kind: AssetKind,)`
- `src/lib/utils.ts`: `getOfferStatus(status: OfferRecordStatus)`
- `src/lib/utils.ts`: `isHex(str: string)`
- `src/lib/utils.ts`: `isValidAddress(address: string, prefix: string)`
- `src/lib/utils.ts`: `isValidAssetId(assetId: string)`
- `src/lib/utils.ts`: `isValidUrl(str: string)`
- `src/lib/utils.ts`: `puzzleHash(address: string)`
- `src/lib/utils.ts`: `toAddress(puzzleHash: string, prefix: string)`
- `src/lib/utils.ts`: `toDecimal(amount: string | number, precision: number)`
- `src/lib/utils.ts`: `toHex(bytes: Uint8Array)`
- `src/lib/utils.ts`: `toMojos(amount: string, precision: number)`
- `src/pages/DidList.tsx`: `DidList()`
- `src/pages/MakeOffer.tsx`: `MakeOffer()`
- `src/pages/MintOption.tsx`: `MintOption()`
- `src/pages/NftList.tsx`: `NftList()`
- `src/pages/Offer.tsx`: `Offer()`
- `src/pages/Offers.tsx`: `Offers()`
- `src/pages/OptionList.tsx`: `OptionList()`
- `src/pages/SavedOffer.tsx`: `SavedOffer()`
- `src/pages/Swap.tsx`: `Swap()`
- `src/pages/TokenList.tsx`: `TokenList()`
- `src/pages/Transactions.tsx`: `Transactions()`
- `src/state.ts`: `clearState()`
- `src/state.ts`: `defaultState()`
- `src/state.ts`: `fetchState()`
- `src/state.ts`: `initializeWalletState(setter: (wallet: KeyInfo | null)`
- `src/state.ts`: `loginAndUpdateState(fingerprint: number,
  onError?: (error: CustomError)`
- `src/state.ts`: `logoutAndUpdateState()`
- `src/state.ts`: `updateSyncStatus()`
- `src/validation.tsx`: `isValidU32(value: number, minimum = 0)`
- `src/walletconnect/commands/chip0002.ts`: `handleChainId()`
- `src/walletconnect/commands/chip0002.ts`: `handleConnect()`
- `src/walletconnect/commands/chip0002.ts`: `handleFilterUnlockedCoins(params: Params<'chip0002_filterUnlockedCoins'>,)`
- `src/walletconnect/commands/chip0002.ts`: `handleGetAssetBalance(params: Params<'chip0002_getAssetBalance'>,)`
- `src/walletconnect/commands/chip0002.ts`: `handleGetAssetCoins(params: Params<'chip0002_getAssetCoins'>,)`
- `src/walletconnect/commands/chip0002.ts`: `handleGetPublicKeys(params: Params<'chip0002_getPublicKeys'>,)`
- `src/walletconnect/commands/chip0002.ts`: `handleSendTransaction(params: Params<'chip0002_sendTransaction'>,)`
- `src/walletconnect/commands/chip0002.ts`: `handleSignCoinSpends(params: Params<'chip0002_signCoinSpends'>,
  context: HandlerContext,)`
- `src/walletconnect/commands/chip0002.ts`: `handleSignMessage(params: Params<'chip0002_signMessage'>,
  context: HandlerContext,)`
- `src/walletconnect/commands/high-level.ts`: `handleBulkMintNfts(params: Params<'chia_bulkMintNfts'>,
  context: HandlerContext,)`
- `src/walletconnect/commands/high-level.ts`: `handleGetAddress()`
- `src/walletconnect/commands/high-level.ts`: `handleGetNfts(params: Params<'chia_getNfts'>,)`
- `src/walletconnect/commands/high-level.ts`: `handleSend(params: Params<'chia_send'>,
  context: HandlerContext,)`
- `src/walletconnect/commands/high-level.ts`: `handleSignMessageByAddress(params: Params<'chia_signMessageByAddress'>,
  context: HandlerContext,)`
- `src/walletconnect/commands/offers.ts`: `handleCancelOffer(params: Params<'chia_cancelOffer'>,
  context: HandlerContext,)`
- `src/walletconnect/commands/offers.ts`: `handleCreateOffer(params: Params<'chia_createOffer'>,
  context: HandlerContext,)`
- `src/walletconnect/commands/offers.ts`: `handleTakeOffer(params: Params<'chia_takeOffer'>,
  context: HandlerContext,)`
- `src/walletconnect/handler.ts`: `handleCommand(command: WalletConnectCommand,
  params: unknown,
  context: HandlerContext,)`
- `tauri-plugin-sage/guest-js/index.ts`: `getNdefPayloads()`
- `tauri-plugin-sage/guest-js/index.ts`: `isNdefAvailable()`