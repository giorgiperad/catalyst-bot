# Sage Wallet RPC — Complete Endpoint Reference

**Last Updated:** March 17, 2026
**Source:** Sage wallet source code (github.com/xch-dev/sage), live testing, TypeScript bindings
**Port:** 9257 (vs Chia wallet port 9256)
**Protocol:** HTTPS with mutual TLS
**Enable:** Sage Settings → Advanced → Start RPC Client

---

## CRITICAL: Sage vs Chia Differences

| Aspect | Chia Wallet | Sage Wallet |
|--------|-------------|-------------|
| Port | 9256 | 9257 |
| Amounts | Integer mojos | **String mojos** (`"1000000000000"`) |
| Coin queries | `get_spendable_coins(wallet_id)` | `get_coins(asset_id, filter_mode)` |
| CAT identification | wallet_id numbers | asset_id hex strings directly |
| Offer creation | `create_offer_for_ids` | `make_offer` |
| Offer listing | `get_all_offers` | `get_offers` |
| Offer view | N/A | `view_offer` (parse bech32) |
| Coin splitting | Custom via transactions | Native `split` endpoint |
| Coin joining | Custom via transactions | Native `combine` endpoint |
| Auto-combine | N/A | `auto_combine_xch` / `auto_combine_cat` |
| Full node needed | YES | NO (peer-to-peer light wallet) |
| Sync time | Hours/days | Minutes |

---

## Connection Setup

```python
import requests
import urllib3
urllib3.disable_warnings()

SAGE_URL = "https://127.0.0.1:9257"
SAGE_CERT = "/path/to/cert.crt"
SAGE_KEY = "/path/to/cert.key"

def rpc(endpoint, payload, timeout=10):
    """Call Sage RPC endpoint."""
    resp = requests.post(
        f"{SAGE_URL}/{endpoint}",
        json=payload,
        cert=(SAGE_CERT, SAGE_KEY),
        verify=False,
        timeout=timeout
    )
    if resp.status_code == 404:
        return None  # Endpoint not found or resource missing
    return resp.json()
```

### Certificate Locations
- **Windows:** `%APPDATA%\com.sage.wallet\ssl\` (daemon.crt + daemon.key)
- **macOS:** `~/Library/Application Support/com.sage.wallet/ssl/`
- **Linux:** `~/.local/share/com.sage.wallet/ssl/`

Configure via .env:
```
SAGE_RPC_URL=https://127.0.0.1:9257
SAGE_CERT_PATH=C:/Users/<user>/AppData/Roaming/com.sage.wallet/ssl/daemon.crt
SAGE_KEY_PATH=C:/Users/<user>/AppData/Roaming/com.sage.wallet/ssl/daemon.key
```

---

## Complete Endpoint Catalog

### 1. Key Management

**`get_keys`** — List all key fingerprints
```json
POST {} → { "keys": [{ "fingerprint": 1234567890, "name": "My Wallet", "has_secrets": true }] }
```

**`get_key`** — Get details for current key
```json
POST {} → { "fingerprint": 1234567890, "name": "...", "public_key": "0x...", "secret_key": "..." }
```

**`login`** — Switch to a different key
```json
POST { "fingerprint": 1234567890 } → { "success": true }
```

**`logout`** — Logout current key
```json
POST {} → { "success": true }
```

**`resync`** — Force full resync of wallet data
```json
POST {} → { "success": true }
```

### 2. Sync & Health

**`get_sync_status`** — Wallet sync state
```json
POST {} → {
  "balance": { "xch": "84700000000000", "cats": { "asset_id_hex": "500000000" } },
  "unit": { "ticker": "XCH", "decimals": 12 },
  "synced": true,
  "receive_address": "xch1...",
  "burn_address": "xch1..."
}
```
Note: This is a combined endpoint — returns sync status AND balance in one call.

**`get_version`** — Sage version string
```json
POST {} → { "version": "0.10.2" }
```

### 3. Coin Queries — THE KEY ENDPOINTS

#### `get_coins` — Universal coin query (MOST IMPORTANT)

This single endpoint replaces multiple Chia endpoints. The `filter_mode` parameter controls what coins are returned.

```json
POST {
  "asset_id": null,           // null = XCH, "hex_string" = CAT
  "offset": 0,
  "limit": 500,
  "filter_mode": "selectable" // "selectable" | "owned" | "spendable" | "spent"
}
```

**Filter Modes (from Sage SQL views):**

| Mode | What It Returns | SQL Definition |
|------|----------------|----------------|
| `selectable` | Free coins ready for offers | `created_height IS NOT NULL AND spent_height IS NULL AND mempool_item_hash IS NULL AND offer_hash IS NULL` |
| `owned` | All coins you own (including offer-locked) | `spent_height IS NULL AND mempool_item_hash IS NULL` (NO offer_hash filter) |
| `spendable` | Similar to selectable, different clawback handling | Same as selectable + different clawback rules |
| `spent` | Coins that have been spent | `spent_height IS NOT NULL OR mempool_item_hash IS NOT NULL` |

**Response:**
```json
{
  "coins": [
    {
      "coin_id": "0xabc123...",
      "amount": "1000000000000",
      "offer_id": "0xdef456...",      // ← KEY FIELD: null if free, offer_hash if locked
      "created_height": 5000000,
      "spent_height": null,
      "transaction_id": "0x...",
      "parent_coin_info": "0x...",
      "puzzle_hash": "0x..."
    }
  ],
  "total_count": 42
}
```

**CRITICAL — The `offer_id` field:**
- `null` → Coin is free (selectable, spendable)
- `"0xhash..."` → Coin is locked by an offer with that offer_hash
- This is the key to solving reconciliation: you know EXACTLY which coins are locked and by which offer

**Practical usage:**
```python
# Get free XCH coins
selectable = rpc("get_coins", {"asset_id": None, "offset": 0, "limit": 500, "filter_mode": "selectable"})

# Get ALL owned XCH coins (including locked)
owned = rpc("get_coins", {"asset_id": None, "offset": 0, "limit": 500, "filter_mode": "owned"})

# Get CAT coins by asset_id
cat_owned = rpc("get_coins", {"asset_id": "abc123hex", "offset": 0, "limit": 500, "filter_mode": "owned"})

# Derive locked coins: owned - selectable
# Or just check offer_id field on owned coins
```

#### `get_coins_by_ids` — Look up specific coins

```json
POST { "coin_ids": ["abc123", "def456"] }
→ {
  "coins": [
    {
      "coin_id": "0xabc123...",
      "amount": "1000000000000",
      "offer_id": null,
      "created_height": 5000000,
      "spent_height": null,
      "transaction_id": "0x..."
    }
  ]
}
```
Note: Sage expects coin IDs WITHOUT "0x" prefix in the request. Strip it before sending.

#### `get_are_coins_spendable` — Quick spendability check

```json
POST { "coin_ids": ["abc123", "def456"] }
→ { "spendable": true }
```
Returns `true` only if ALL provided coins are spendable. Returns `false` if any one is locked/spent/missing.

#### `get_spendable_coin_count` — Count of spendable coins

```json
POST { "asset_id": null }    // null = XCH
POST { "asset_id": "hex..." }  // specific CAT
→ { "count": 42 }
```

### 4. Coin Operations

**`split`** — Split a coin into multiple smaller coins
```json
POST {
  "coin_id": "abc123",       // Coin to split (without 0x prefix)
  "output_count": 10,        // Number of output coins
  "fee": "0"                 // Fee in string mojos
}
→ { "transaction_ids": ["0x..."] }
```

**`combine`** — Combine multiple coins into one
```json
POST {
  "coin_ids": ["abc123", "def456"],  // Coins to combine
  "fee": "0"
}
→ { "transaction_ids": ["0x..."] }
```

**`auto_combine_xch`** — Automatic XCH coin consolidation
```json
POST { "max_coins": 500, "fee": "0" }
→ { "transaction_ids": ["0x..."] }
```

**`auto_combine_cat`** — Automatic CAT coin consolidation
```json
POST { "asset_id": "hex...", "max_coins": 500, "fee": "0" }
→ { "transaction_ids": ["0x..."] }
```

### 5. Sending Transactions

**`send_xch`** — Send XCH
```json
POST {
  "address": "xch1...",
  "amount": "1000000000000",  // String mojos
  "fee": "0"
}
→ { "transaction_ids": ["0x..."] }
```

**`send_cat`** — Send CAT tokens
```json
POST {
  "asset_id": "hex...",
  "address": "xch1...",
  "amount": "1000000",  // String mojos in CAT denomination
  "fee": "0"
}
→ { "transaction_ids": ["0x..."] }
```

**`multi_send`** — Send to multiple recipients in one transaction
```json
POST {
  "payments": [
    { "address": "xch1...", "amount": "1000000000000" },
    { "address": "xch1...", "amount": "2000000000000" }
  ],
  "fee": "0"
}
→ { "transaction_ids": ["0x..."] }
```

### 6. Offer Management

**`make_offer`** — Create a new offer
```json
POST {
  "offered_assets": {
    "xch": "1000000000000",           // String mojos for XCH
    "cat:asset_id_hex": "1000000"     // String mojos for CAT
  },
  "requested_assets": {
    "cat:asset_id_hex": "500000000"   // What you want in return
  },
  "fee": "0",
  "auto_submit": true,
  "expires_at_second": 1710604800     // Unix timestamp for expiry (optional)
}
→ {
  "offer_id": "0xhash...",           // The offer_hash (used for cancellation)
  "offer": "offer1qr58pe3w...",      // Bech32 offer string for posting
  "trade_id": "0x..."                // Internal trade identifier
}
```

**`get_offers`** — List all offers
```json
POST {
  "include_completed": true,
  "offset": 0,
  "limit": 50,
  "sort_key": "date_created",
  "ascending": false
}
→ {
  "offers": [
    {
      "offer_id": "0x...",
      "status": "active",
      "offered": { "xch": "1000000000000" },
      "requested": { "asset_id": "500000000" },
      "date_created": 1710600000,
      "expiry": 1710686400,
      "is_my_offer": true,
      "offer_string": "offer1..."
    }
  ]
}
```

**Sage Offer Statuses:**
| Status | Meaning | Equivalent Chia Status |
|--------|---------|----------------------|
| `active` | Open, waiting for taker | PENDING_ACCEPT |
| `pending` | In mempool, being confirmed | PENDING_CONFIRM |
| `completed` | Filled and confirmed | CONFIRMED |
| `cancelled` | Cancelled by maker | CANCELLED |
| `expired` | Past expiry timestamp | (Chia reports as PENDING_ACCEPT — BUG) |

**`get_offer`** — Get single offer details
```json
POST { "offer_id": "0xhash..." }
→ { "offer_id": "0x...", "status": "active", ... }
```
Returns 404 if offer doesn't exist (already gone from wallet).

**`cancel_offer`** — Cancel an offer
```json
POST {
  "offer_id": "0xhash...",
  "fee": "0",
  "secure": true              // true = on-chain cancel, false = just remove from wallet
}
→ { "success": true }
```

**CRITICAL — 404 Handling:**
If the offer is already gone (cancelled, filled, expired), Sage returns HTTP 404 with "Missing offer". This should be treated as a successful cancel — the offer is already gone.

**`view_offer`** — Parse a bech32 offer string without taking it
```json
POST { "offer": "offer1qr58pe3w..." }
→ {
  "offered": { "xch": "1000000000000" },
  "requested": { "asset_id_hex": "500000000" },
  "fee": "50000000",
  "valid": true
}
```

**`take_offer`** — Accept someone else's offer (not listed in our wallet_sage.py but exists in Sage)
```json
POST { "offer": "offer1qr58pe3w...", "fee": "0" }
→ { "transaction_ids": ["0x..."] }
```

### 7. Transaction History

**`get_transactions`** — List transactions
```json
POST {
  "wallet_id": 1,    // Or use asset_id
  "offset": 0,
  "limit": 50
}
→ { "transactions": [...], "total_count": 100 }
```

**`get_transaction`** — Get single transaction
```json
POST { "transaction_id": "0xhash..." }
→ { "transaction": { "confirmed": true, "confirmed_at_height": 5000001, ... } }
```

**`get_pending_transactions`** — Unconfirmed transactions only
```json
POST {}
→ { "transactions": [...] }
```

### 8. Wallet/CAT Info

**`get_cats`** — List all CAT tokens in wallet
```json
POST {}
→ {
  "cats": [
    { "asset_id": "hex...", "name": "HVST", "ticker": "HVST", "balance": "50000000000" }
  ]
}
```

### 9. Network/Peer Info

**`get_peers`** — Connected peer list
```json
POST {}
→ { "peers": [{ "ip": "1.2.3.4", "port": 8444, "protocol_version": "..." }] }
```

---

## SQL View Definitions (from Sage source: migrations/0002_options.sql)

These are the actual SQL definitions that determine what each filter mode returns. Understanding these is essential for debugging reconciliation issues.

### `selectable_coins` view
```sql
SELECT * FROM wallet_coins
WHERE created_height IS NOT NULL       -- Must be confirmed on-chain
  AND spent_height IS NULL             -- Not spent
  AND mempool_item_hash IS NULL        -- Not in mempool
  AND offer_hash IS NULL               -- NOT locked by any offer
  AND NOT EXISTS (                     -- Not being spent in pending tx
    SELECT 1 FROM mempool_coins
    WHERE mempool_coins.coin_id = wallet_coins.coin_id
  )
  -- Plus clawback/options checks
```

### `owned_coins` view
```sql
SELECT * FROM wallet_coins
WHERE spent_height IS NULL             -- Not spent
  AND mempool_item_hash IS NULL        -- Not in mempool
  -- NO offer_hash filter (includes offer-locked coins!)
  -- NO created_height check (includes unconfirmed coins!)
  -- Plus clawback/options checks
```

### `spent_coins` view
```sql
SELECT * FROM wallet_coins
WHERE spent_height IS NOT NULL         -- Has been spent
   OR mempool_item_hash IS NOT NULL    -- Or is being spent in mempool
```

### Key Insight: owned - selectable = ?
The difference between owned and selectable coins includes:
1. Coins with `offer_hash IS NOT NULL` (locked by offers)
2. Coins with `created_height IS NULL` (unconfirmed — not yet on-chain)
3. Coins in mempool_coins table (being spent in pending tx)

This is why `owned_count - selectable_count` equals the number of locked + unconfirmed coins.

---

## Reconciliation Strategy (Bot-Specific)

### The Right Way (using get_owned_coins_detailed)

```python
def reconcile_sage():
    """Single-query reconciliation using offer_id field."""
    for asset_type, asset_id in [("xch", None), ("cat", CAT_ASSET_ID)]:
        # ONE query gets everything we need
        result = rpc("get_coins", {
            "asset_id": asset_id,
            "offset": 0, "limit": 500,
            "filter_mode": "owned"
        })

        owned_map = {}
        selectable_map = {}
        offer_id_map = {}  # coin_id → offer_hash

        for coin in result["coins"]:
            cid = normalize_coin_id(coin["coin_id"])
            amount = int(coin["amount"])
            offer_id = coin.get("offer_id")

            owned_map[cid] = amount

            if offer_id:
                # Coin is locked by this offer
                offer_id_map[cid] = offer_id
            else:
                # Coin is free
                selectable_map[cid] = amount

        # Now reconcile: DB should match owned_map
        # Locked coins should have trade_ids from offer_id_map
        # Free coins should be in selectable_map
        reconcile_coins_with_wallet(
            wallet_selectable=selectable_map,
            wallet_owned=owned_map,
            wallet_type=asset_type
        )

        # Direct linking: use offer_id_map to assign trade_ids
        # This replaces unreliable amount-based matching
        for coin_id, offer_hash in offer_id_map.items():
            link_coin_to_offer(coin_id, offer_hash)
```

### The Wrong Way (causes tug-of-war)
1. ❌ Using separate `get_coins(selectable)` and `get_coins(owned)` calls — race condition
2. ❌ Amount-based matching for locked coins — unreliable when multiple coins have same amount
3. ❌ Freeing orphaned locked coins without checking wallet state — breaks reconciliation

---

## Amount Conversion Helpers

```python
def sage_amount_to_int(s):
    """Convert Sage string amount to integer mojos."""
    if isinstance(s, str):
        return int(s)
    return int(s)

def int_to_sage_amount(n):
    """Convert integer mojos to Sage string format."""
    return str(int(n))

# XCH: 1 XCH = 10^12 mojos = "1000000000000"
# CAT: 1 token = 10^3 mojos = "1000" (for most CATs with 3 decimals)
```

---

## Error Handling Patterns

### HTTP 404 — Resource Not Found
Sage returns 404 for missing resources. Common cases:
- `cancel_offer` on already-gone offer → Treat as success
- `get_offer` on non-existent offer → Return None
- `get_coins_by_ids` with invalid ID → Returns empty result

```python
def safe_cancel(offer_id):
    try:
        result = rpc("cancel_offer", {"offer_id": offer_id})
        return {"success": True}
    except Exception as e:
        if "404" in str(e) or "Missing offer" in str(e):
            return {"success": True, "already_gone": True}
        raise
```

### Timeout Handling
Sage is generally faster than Chia wallet, but some operations can be slow:
- Coin splitting: 15-30s
- Offer creation: 10-20s
- Coin queries: 2-5s
- Cancel: 5-10s (on-chain), instant (insecure)

### Balance Gotcha
`get_sync_status` returns total owned balance, NOT spendable balance. For a market maker with 100 offers, owned >> spendable. Example: owned = 84.7 XCH, spendable = 1.2 XCH. This is NORMAL — most coins are locked by active offers.

---

## Bot Integration: wallet_sage.py Function Map

| Bot Function | Sage RPC Call | Notes |
|-------------|--------------|-------|
| `get_owned_coins(wallet_id)` | `get_coins(asset_id, filter_mode="owned")` | Returns `{coin_id: amount}` |
| `get_owned_coins_detailed(wallet_id)` | `get_coins(asset_id, filter_mode="owned")` | Returns `{coin_id: {amount, offer_id, ...}}` |
| `get_selectable_coins_map(wallet_id)` | `get_coins(asset_id, filter_mode="selectable")` | Returns `{coin_id: amount}` for free coins |
| `get_spendable_coins_rpc(wallet_id)` | `get_coins(asset_id, filter_mode="selectable")` | Alias for selectable |
| `get_coins_by_ids(coin_ids)` | `get_coins_by_ids(coin_ids)` | Strip 0x prefix! |
| `are_coins_spendable(coin_ids)` | `get_are_coins_spendable(coin_ids)` | Returns single boolean |
| `get_spendable_coin_count(wallet_id)` | `get_spendable_coin_count(asset_id)` | Integer count |
| `get_wallet_balance(wallet_id)` | `get_sync_status` + `get_coins(selectable)` | Compute from coins |
| `create_offer(...)` | `make_offer(...)` | Different param names |
| `cancel_offer(trade_id)` | `cancel_offer(offer_id)` | Handle 404 as success |
| `get_all_offers(...)` | `get_offers(...)` | Different response format |
| `split_coins_rpc(...)` | `split(coin_id, output_count, fee)` | Native splitting |
| `combine_coins(...)` | `combine(coin_ids, fee)` | Native combining |
| `send_transaction(...)` | `send_xch(address, amount, fee)` | String amounts |
| `send_cat_multi(...)` | `send_cat(asset_id, address, amount, fee)` | String amounts |

---

## Endpoint Quick Reference (Alphabetical)

| Endpoint | Category | Purpose |
|----------|----------|---------|
| `auto_combine_cat` | Coins | Auto-consolidate CAT coins |
| `auto_combine_xch` | Coins | Auto-consolidate XCH coins |
| `cancel_offer` | Offers | Cancel an active offer |
| `combine` | Coins | Combine specific coins into one |
| `get_are_coins_spendable` | Coins | Check if all given coins are spendable |
| `get_cats` | Wallet | List all CAT tokens in wallet |
| `get_coins` | Coins | Universal coin query with filter modes |
| `get_coins_by_ids` | Coins | Look up specific coins by ID |
| `get_key` | Keys | Get current key details |
| `get_keys` | Keys | List all key fingerprints |
| `get_offer` | Offers | Get single offer details |
| `get_offers` | Offers | List all offers |
| `get_peers` | Network | Connected peer list |
| `get_pending_transactions` | Transactions | Unconfirmed transactions |
| `get_spendable_coin_count` | Coins | Count of spendable coins |
| `get_sync_status` | Health | Sync state + balance |
| `get_transaction` | Transactions | Single transaction details |
| `get_transactions` | Transactions | Transaction history |
| `get_version` | Health | Sage version string |
| `login` | Keys | Switch to different key |
| `logout` | Keys | Logout current key |
| `make_offer` | Offers | Create a new offer |
| `multi_send` | Transactions | Send to multiple recipients |
| `resync` | Health | Force full wallet resync |
| `send_cat` | Transactions | Send CAT tokens |
| `send_xch` | Transactions | Send XCH |
| `split` | Coins | Split a coin into multiple |
| `take_offer` | Offers | Accept someone else's offer |
| `view_offer` | Offers | Parse bech32 offer string |

**Total: 28 documented endpoints**

---

## Debugging Checklist

When something goes wrong with Sage integration:

1. **Is RPC enabled?** Settings → Advanced → Start RPC Client must be ON
2. **Is wallet synced?** Check `get_sync_status` → `synced: true`
3. **Correct port?** 9257, not 9256 (Chia)
4. **Amounts as strings?** Sage uses `"1000000000000"` not `1000000000000`
5. **Coin ID format?** Strip `0x` prefix for `get_coins_by_ids` and `get_are_coins_spendable`
6. **404 on cancel?** Offer already gone — treat as success
7. **Owned >> spendable?** Normal for market maker — most coins locked by offers
8. **Reconciliation drift?** Use `get_coins(owned)` + `offer_id` field, not separate queries
9. **offer_id vs trade_id?** `offer_id` = offer_hash (from wallet), `trade_id` = our internal identifier
10. **SSL cert paths correct?** Check SAGE_CERT_PATH and SAGE_KEY_PATH in .env
