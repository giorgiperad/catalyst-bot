# Chia Blockchain Development Guide
## For Market Maker Bot Development

This is the definitive reference for building on the Chia blockchain. Read this before writing any Chia-related code.

---

## 1. The Coin Set Model (Not UTXO, Not Accounts)

Chia doesn't use accounts or balances. Everything is a **coin**. When you "have 10 XCH," you actually have several coins that add up to 10 XCH.

### What Is A Coin?

Every coin has exactly three properties (all immutable):

| Property | Type | What It Is |
|----------|------|-----------|
| `parent_coin_info` | bytes32 | The coin ID of the parent coin that created this one |
| `puzzle_hash` | bytes32 | Hash of the program that locks this coin (like an address) |
| `amount` | uint64 | Amount in mojos |

A coin's ID is: `sha256(parent_coin_info + puzzle_hash + amount)`

Since the ID is a hash of its properties, coins can never be changed — only created and destroyed.

### How Spending Works

When you spend a coin:
1. The original coin is **destroyed** (removed from the coin set)
2. One or more **new coins** are created with potentially different amounts
3. The spent coin becomes the parent of the new coins

This is why coin management matters so much for market making — every offer, every fill, every split changes which coins exist.

### Why This Matters For Market Making

- **Offers lock specific coins.** When you create an offer for 0.2 XCH, a specific 0.2 XCH coin gets locked. You can't use it for anything else.
- **Fills destroy and create coins.** When someone takes your offer, your locked coin is destroyed and new coins appear. The IDs change completely.
- **You need pre-split coins.** If you have one 10 XCH coin but want 50 offers of 0.2 XCH, you first need to split that coin into 50 smaller ones.
- **Cancelling offers creates change.** Secure cancel spends the locked coin and creates a new one — fragmenting your coins.

---

## 2. Units and Conversions

### XCH (Chia)
```
1 XCH = 1,000,000,000,000 mojos (1 trillion, 1e12)

xch_to_mojos:  int(amount_xch * 1_000_000_000_000)
mojos_to_xch:  mojos / 1_000_000_000_000
```

### CAT Tokens (Chia Asset Tokens)
```
CAT amounts use 10^decimals, NOT 1e12!

For a CAT with 3 decimals:
  1 token = 1,000 mojos (10^3)

cat_to_mojos:  int(amount_cat * (10 ** decimals))
mojos_to_cat:  mojos / (10 ** decimals)
```

**CRITICAL: Never confuse CAT mojos with XCH mojos.** A CAT with 3 decimals uses 1,000 mojos per token. XCH uses 1,000,000,000,000 mojos per unit. Mixing these up produces wildly wrong offer amounts.

### Decimal Handling
Always use Python's `Decimal` type for amounts, never `float`. Floating point arithmetic introduces rounding errors that compound across many offers.

```python
from decimal import Decimal, ROUND_DOWN

def xch_to_mojos(amount_xch: Decimal) -> int:
    return int((amount_xch * Decimal("1000000000000")).to_integral_value(ROUND_DOWN))

def cat_to_mojos(amount: Decimal, decimals: int) -> int:
    scale = Decimal(10) ** Decimal(decimals)
    return int((amount * scale).to_integral_value(ROUND_DOWN))
```

---

## 3. Wallet RPC API

### Connection Setup

The Chia wallet exposes an RPC API over HTTPS with mutual TLS authentication.

| Setting | Value |
|---------|-------|
| Wallet RPC URL | `https://localhost:9256` |
| Full Node RPC URL | `https://localhost:8555` |
| TLS Certificates | `~/.chia/mainnet/config/ssl/wallet/` |
| TLS Verification | `verify=False` (Chia self-signed certs don't include localhost in SAN) |

**Timeout Strategy:** Use tuple timeouts `(connect, read)`. Connect should be fast for localhost (3s), read depends on the operation.

**Retry Strategy:** Set `connect=0` (no retries on connection refused). When Chia is down, retrying wastes 10+ seconds per call. Let the bot loop handle recovery instead.

```python
session = requests.Session()
retries = Retry(total=2, connect=0, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=1, pool_maxsize=5))
```

### Key RPC Endpoints

| Endpoint | Purpose | Recommended Timeout |
|----------|---------|-------------------|
| `get_sync_status` | Check if wallet is synced | 5s |
| `get_wallet_balance` | Get XCH or CAT balance | 10s |
| `get_spendable_coins` | List available coins (with size filtering) | 15s |
| `get_wallets` | List all wallet IDs | 10s |
| `get_next_address` | Get receive address | 10s |
| `split_coins` | Split one coin into many (single tx!) | 30s |
| `send_transaction` | Send coins | 10s |
| `create_offer_for_ids` | Create a trade offer | 15s |
| `get_all_offers` | List all offers | 8s |
| `get_offer` | Get specific offer (with bech32 string) | 10s |
| `cancel_offer` | Cancel an offer | 60s |
| `get_blockchain_state` | Full node sync status | 5s |

### RPC Response Format

All responses include `"success": true/false`. Always check this field.

The `get_all_offers` response is particularly tricky — different Chia versions use different field names:
```python
# Handle multiple response formats
offers_list = res.get("trades")
if offers_list is None:
    offers_list = res.get("offers")
if offers_list is None:
    offers_list = res.get("trade_records")
```

### Wallet ID vs Asset ID

- **Wallet ID**: Local number (1 = XCH, 2+ = CATs). Used in RPC calls.
- **Asset ID**: Blockchain-wide hex identifier for a CAT token. Used to identify which token.
- You need the wallet ID for RPC calls, the asset ID for identifying the token across the network.

---

## 4. Offers — The Core of Market Making

### Offer Dictionary Format

This is how you tell the Chia wallet what to trade:

```python
# Format: {str(wallet_id): amount_in_mojos}
# NEGATIVE amount = we are SPENDING (offering)
# POSITIVE amount = we are RECEIVING (requesting)

# BUY offer: Spend XCH, receive CAT
buy_offer = {
    str(WALLET_ID_XCH): -int(xch_mojos),     # Negative: we give XCH
    str(cat_wallet_id): int(cat_mojos)         # Positive: we want CAT
}

# SELL offer: Spend CAT, receive XCH
sell_offer = {
    str(cat_wallet_id): -int(cat_mojos),       # Negative: we give CAT
    str(WALLET_ID_XCH): int(xch_mojos)         # Positive: we want XCH
}
```

### Offer Lifecycle

```
PENDING_ACCEPT  →  Someone creates the offer, coins are locked locally
PENDING_CONFIRM →  Someone accepted, spend bundle sent to mempool
CONFIRMED       →  Trade completed on blockchain, coins transferred
CANCELLED       →  Maker cancelled, coins unlocked
FAILED          →  Something went wrong, coins unlocked
```

### The Wallet Lies About Expired Offers

**This is the single most important Chia gotcha for market making.**

The Chia wallet does NOT auto-transition expired offers from PENDING_ACCEPT to EXPIRED. An offer past its `max_time` still shows as "open" in the wallet. You MUST check `valid_times.max_time` manually:

```python
def is_offer_time_expired(offer: dict) -> bool:
    valid_times = offer.get("valid_times") or {}
    max_time = valid_times.get("max_time", 0)
    if max_time and max_time > 0:
        return int(time.time()) > max_time
    return False
```

### Offer Expiry Staggering

If all 50 offers expire at the same time, you get a mass-expiry cascade. Stagger them:

```python
# Each offer gets a slightly different expiry
total_expiry = OFFER_EXPIRY_SECS + (slot_index * stagger_seconds)
offer_max_time = int(time.time()) + total_expiry
```

### Secure vs Insecure Cancel

- **Secure** (`secure=True`): Spends the coin on-chain, creating a new coin. The offer can never be taken, even if copies exist elsewhere. Costs a blockchain transaction.
- **Insecure** (`secure=False`): Just un-reserves the coin locally. If someone has a copy of the offer, they can still take it. Free and instant.

Use secure cancel for offers posted to Dexie. Use insecure for offers that never left your wallet.

### Batch Cancellation — Always Sequential

Parallel cancellations overwhelm the wallet RPC and cause failures. Always cancel one at a time with delays:

```python
for trade_id in trade_ids:
    cancel_offer(trade_id, secure=True)
    time.sleep(1.0)  # Let the wallet breathe
```

### Classifying Offers as Buy or Sell

```python
summary = offer.get("summary", {})
offered = summary.get("offered", {})     # What we give
requested = summary.get("requested", {}) # What we want

# BUY: XCH in offered, CAT in requested
if "xch" in offered and any(k != "xch" for k in requested):
    side = "buy"

# SELL: CAT in offered, XCH in requested
if any(k != "xch" for k in offered) and "xch" in requested:
    side = "sell"
```

---

## 5. Fill Detection

Fills are detected by comparing the set of open offer IDs between two consecutive bot loop iterations:

```
Previous loop: {offer_A, offer_B, offer_C, offer_D}
Current loop:  {offer_A, offer_C, offer_D}

Disappeared:   {offer_B}  →  Likely filled!
```

### Mass Disappearance Guard

If >50% of offers vanish in one loop, it's almost certainly a wallet sync blip (RPC returned incomplete results), not real fills. Require 3 consecutive detections before treating them as genuine:

```python
if total_disappeared > (total_previous * 0.5):
    mass_disappearance_count += 1
    if mass_disappearance_count < 3:
        return  # Skip — probably wallet blip
```

### Bot-Cancelled vs Externally Filled

Track which offers YOU cancelled (requoting, cleanup) vs ones that disappeared because someone took them:

```python
if offer_id in bot_cancelled_ids:
    status = "CANCELLED"  # We did this
    bot_cancelled_ids.discard(offer_id)
else:
    status = "FILLED"  # External fill!
```

---

## 6. Coin Management

### Coin ID Calculation

```python
import hashlib

parent_bytes = bytes.fromhex(parent.replace("0x", ""))
puzzle_bytes = bytes.fromhex(puzzle.replace("0x", ""))
amount_bytes = amount.to_bytes(8, 'big')

coin_id = "0x" + hashlib.sha256(parent_bytes + puzzle_bytes + amount_bytes).hexdigest()
```

### Counting Coins by Size

Use `get_spendable_coins` with min/max filters to count coins suitable for offers:

```python
def count_suitable_coins(wallet_id, target_mojos, tolerance=0.25):
    min_mojos = int(target_mojos * (1 - tolerance))
    max_mojos = int(target_mojos * (1 + tolerance))
    result = rpc("get_spendable_coins", {
        "wallet_id": wallet_id,
        "min_coin_amount": str(min_mojos),
        "max_coin_amount": str(max_mojos)
    })
    return len(result.get("records", []))
```

### Coin Splitting (Native RPC — Fast)

The `split_coins` RPC creates many coins in a single blockchain transaction:

```python
result = rpc("split_coins", {
    "wallet_id": wallet_id,
    "target_coin_id": coin_id,
    "number_of_coins": 50,
    "amount_per_coin": 200000000000,  # 0.2 XCH in mojos
    "fee": 0
}, timeout=30)
```

For CATs, `amount_per_coin` is the token amount (e.g., 3575 for 3575 tokens), NOT mojos.

### Coin Confirmation Polling

After splitting, coins take time to confirm on the blockchain. Never use fixed timeouts — poll:

```python
while time.time() - start < max_wait:
    confirmed = count_suitable_coins(wallet_id, target_size, tolerance)
    if confirmed >= target_count:
        return True
    time.sleep(10)  # Poll every 10 seconds
```

### Coins Locked by Offers

Active offers lock specific coins. Always exclude them when counting available coins:

```python
locked_coin_ids = get_coins_used_by_offers(active_offers)
available = [c for c in all_coins if c["coin_id"] not in locked_coin_ids]
```

### The Spare Coin Pattern

Coin prep leaves one large "spare" coin (~30% of balance) for future expansion (the "Close the Gap" button). This coin gets split in two stages when needed:

1. Stage 1: Spare coin → allocation coin + new spare coin
2. Stage 2: Allocation coin → N offer-sized coins

---

## 7. Dexie Integration

### Posting Offers

```python
response = requests.post(
    "https://api.dexie.space/v1/offers",
    json={"offer": offer_bech32_string},
    headers={"x-bot-tag": "MZ_MM_BOT"}
)
```

### Rate Limits
- 50 requests per 10 seconds
- Use fingerprint deduplication to avoid reposting unchanged offers
- Implement exponential backoff on rate limit responses

### State Persistence
Always key Dexie state by `trade_id` (Chia's offer identifier), never by `dexie_id`. This was the bug that hit us three times in V1.

### Getting the Bech32 Offer String

To post to Dexie, you need the `offer1...` string:

```python
res = rpc("get_offer", {"trade_id": trade_id, "file_contents": True})
offer_string = res.get("offer")  # or nested in trade_record
```

---

## 8. TibetSwap Integration

### Price from Reserves

TibetSwap is a constant-product AMM: `x × y = k`

```
price_per_token = xch_reserve / token_reserve
```

### API

```
GET https://api.v2.tibetswap.io/pairs?skip=0&limit=100
```

Returns pairs with `asset_id`, `xch_reserve`, `token_reserve`.

### Pricing Strategies

| Strategy | Formula |
|----------|---------|
| `dexie_only` | Use Dexie price only |
| `tibet_only` | Use TibetSwap pool price only |
| `average` | `(dexie + tibet) / 2` |
| `weighted` | `dexie × (1 - weight) + tibet × weight` |

### Arbitrage Detection

When Dexie and TibetSwap prices diverge beyond a threshold (in basis points), there's an arb opportunity. The "sniper" feature creates aggressive offers to close the gap.

---

## 9. Performance Characteristics

| Operation | Typical Duration |
|-----------|-----------------|
| Offer creation | 1-2 seconds |
| Offer cancellation | 1-3 seconds per offer (sequential) |
| Coin split confirmation | 30-60 seconds (blockchain dependent) |
| Fill detection loop | <1 second |
| Coin prep full run | 1.7-3 minutes (with parallel optimization) |
| Mass offer creation (30) | 2-3 minutes |
| Average block time | 18.75 seconds |
| Finality threshold | 32 blocks (~10 minutes) |

---

## 10. Known Issues & Workarounds

### Wallet Doesn't Auto-Expire Offers
Always check `valid_times.max_time` manually. See Section 4.

### "Wallet Needs To Be Fully Synced" Error
Transient during heavy operations. Retry with escalating backoff: 5s, 10s, etc.

### Parallel Cancellations Break The Wallet
Always cancel sequentially with 0.5-1s delays between each.

### Coin Fragmentation From Cancellations
Secure cancel creates change coins. Consolidate after mass cancellations.

### Mass Disappearance False Positives
If >50% of offers vanish in one check, require 3 confirmations before treating as fills.

### RPC Response Format Varies By Chia Version
Check multiple field names (`trades`, `offers`, `trade_records`) for offer lists.

### CLI and RPC Disagree
The CLI and RPC return different formats, field names, and sometimes different data. Always prefer RPC for programmatic access.

### Protected Offers During Coin Prep
Save "core offers" to a protected file before coin prep so they survive the cancellation step, maintaining market liquidity during migration.

---

## 11. V1 Bugs — Never Repeat These

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Dexie links lost on restart (3 times!) | State keyed by `dexie_id` instead of `trade_id` | Always use `trade_id` as the universal key |
| Topup worker triggers but skips | Checking total coins instead of free coins | Always use `get_spendable_coins` |
| Truncated offer lists | Using `end=50` when there are 100 offers | Always fetch with large enough `end` parameter |
| GUI event loop blocked | Using `confirm()` browser dialogs | Use styled modals instead |
| Wrong coin counts | CLI includes locked coins | Use `get_spendable_coins_rpc()` only |
| Cooldowns don't match thresholds | Health check at 30%, topup at 50% | Same mental model everywhere |

---

## 12. Code Conventions

- Python: `snake_case` for functions/variables, `UPPER_CASE` for constants
- Always use `Decimal` for financial amounts, never `float`
- Always add `add_log()` calls for important operations (GUI depends on these)
- Catch specific exceptions, never bare `except:`
- All wallet RPC calls go through `wallet.py`, never direct HTTP from other modules
- `pip install` always needs `--break-system-packages` flag
- Verify syntax after every edit: `python -c "import ast; ast.parse(open('file.py').read())"`
- The `.env` file contains wallet keys — DO NOT read or modify it
