# Sage Edge Cases

## Scope

This document collects:

- explicit rare paths
- fallback logic
- silent/no-op paths
- missing or weak handling

Detailed execution-path inventory:

- `sage_execution_paths.md`

## Handled Edge Cases

### Input and Parsing

- key import supports mnemonic, secret key hex, and public key hex
- mnemonic validation distinguishes wrong word count, unknown word, and invalid checksum
- signature message parsing accepts plain text, raw hex, and `0x`-prefixed hex
- DID/NFT/option/collection parsers reject wrong prefixes early

### Graceful Empty Results

- `get_key` can return `None`
- `get_secret_key` can return `None`
- `get_option` can return `None`
- `get_nft` can return `None`
- `get_nft_data` can return `None`
- `get_nft_icon` can return `None`
- `get_nft_thumbnail` can return `None`
- `get_user_theme` can return `None`
- `delete_user_theme` can no-op for missing targets

### Optional / Default Flows

- `auto_submit` defaults to false in most transaction-like requests
- `save_secrets` defaults to true for key import
- `login` defaults to true for key import
- `hardened` and `unhardened` often default to true when omitted
- `get_nft_collection(None)` returns an uncategorized synthetic collection
- `get_nfts` supports `"none"` sentinels for group search

### Network and External Fetches

- NFT mint/import paths can fetch missing hashes from URIs with timeout protection
- CAT resync fetches metadata from Dexie
- WalletConnect immediate-send distinguishes `Pending`, `Failed`, and `Unknown`

## Rare and Alternative Paths

- watch-only wallets can be imported and queried but fail signing flows with `NoSigningKey`
- request-only offers are allowed only with a fee
- offered/requested offer assets branch by detected id format
- auto-combine flows filter and sort eligible coins before combining
- grouped NFT queries allow exactly one grouping dimension

## Fallback Logic

- `get_key` uses explicit fingerprint if provided, else active fingerprint
- wallet config often falls back with `unwrap_or_default()`
- peer restore falls back to default snapshot if stored peer file fails to parse
- malformed NFT metadata is often tolerated and degraded into partial/empty output
- `transact_with` supports construct-only or submit-and-return behavior

## Missing Or Weak Handling

### Initialization and Lifecycle

- `initialize` sets initialized flag before init succeeds
- failed first init may block later retries
- `start_rpc_server` has no duplicate-start guard

### Network Configuration

- `set_network` and `set_network_override` persist arbitrary names without validating them
- `network()` later uses `expect("network not found")`

### State Restoration

- `resync` clears active fingerprint before destructive work
- if a later step fails, previous login state may not be restored

### Unsafe / Weak Validation

- `move_key` can panic on invalid index
- `check_address` does not enforce active network prefix
- parser support for `0x` vs `0X` is inconsistent
- `parse_signature_message` treats hex-looking text like `cafe` as bytes

### Theme Handling

- `save_user_theme` can return success without actually writing a theme
- `get_user_themes` swallows per-file read failures and only logs to stderr

### Database / File Cleanup

- `delete_database` removes only the main sqlite file, not explicit sidecars
- `get_logs` errors if the log directory is missing

### Suspicious Logic

- `import_offer` appears to push requested options into `nft_rows` instead of `option_rows`

## Defensive Caller Recommendations

- validate `move_key` indices before calling
- validate network names against `get_networks`
- normalize hex casing/prefixes before parser-bound calls
- treat theme save/read behavior as potentially partial
- treat `check_address` as partial helper, not full validator
- distinguish watch-only from hot wallets in the caller
