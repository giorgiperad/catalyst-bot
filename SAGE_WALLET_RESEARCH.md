# Sage Wallet Research — Compatibility Assessment for V2 Bot

**Date:** February 2026
**Purpose:** Evaluate whether Sage wallet can be used as an alternative to the official Chia wallet for our market maker bot.

## What is Sage?

Sage is a high-performance light wallet for Chia built in Rust (backend) with a TypeScript/React frontend via Tauri v2. It connects directly to Chia network peers rather than requiring a full node sync, making it much faster to set up and lighter on resources.

It's developed by Rigidity (xch-dev) and built on top of chia_rs, clvm_rs, and the Chia Wallet SDK.

**Official site:** https://sagewallet.net/
**GitHub:** https://github.com/xch-dev/sage

## RPC API — Does It Have What We Need?

**Yes — Sage has a full RPC API on port 9257** (vs Chia's port 9256).

To enable it: Settings → Advanced → Start RPC Client.

### Bot-Critical Endpoints — All Present

| What We Need | Chia RPC (current) | Sage RPC Equivalent | Status |
|---|---|---|---|
| Create offers | `create_offer_for_ids` | `create_offer` / `Build-SageOffer` | ✅ Available |
| Cancel offers | `cancel_offer` | `cancel_offer` / `Revoke-SageOffer` | ✅ Available (v0.8.6+) |
| List offers | `get_all_offers` | `get_offers` / `Get-SageOffers` | ✅ Available |
| Get offer detail | `get_offer` | `get_offer` / `Get-SageOffer` | ✅ Available |
| Get spendable XCH coins | `get_spendable_coins` | `get_xch_coins` / `Get-SageXchCoins` | ✅ Available |
| Get spendable CAT coins | `get_spendable_coins` | `get_cat_coins` / `Get-SageCatCoins` | ✅ Available |
| Split XCH coins | `cat_spend` (custom) | `split_xch_coin` / `Split-SageXchCoin` | ✅ Available |
| Split CAT coins | N/A (custom) | `split_cat_coins` / `Split-SageCatCoins` | ✅ Available |
| Join/consolidate coins | N/A (custom) | `join_xch_coins` / `join_cat_coins` | ✅ Available |
| Wallet balance | `get_wallet_balance` | Available via coin queries | ✅ Available |
| Send XCH | `send_transaction` | `send_xch` / `Send-SageXch` | ✅ Available |
| Bulk send | N/A | `send_xch_bulk` / `Send-SageXchBulk` | ✅ Bonus feature |
| Combine offers | N/A | `combine_offers` (v0.9.4+) | ✅ Bonus feature |
| Sync status | `get_sync_status` | `get_sync_status` | ✅ Available |

### Key Differences From Chia Wallet RPC

1. **Port:** Sage uses `https://127.0.0.1:9257` (Chia uses `9256`)
2. **Amounts as strings:** Sage uses string mojos (e.g., `"1000000000000"`) where Chia uses integers
3. **SSL certs:** Sage has its own cert/key paths (different location from Chia's)
4. **Coin endpoints are separate:** `get_xch_coins` and `get_cat_coins` are separate endpoints (Chia uses `get_spendable_coins` with wallet_id parameter)
5. **Native coin splitting:** Sage has dedicated `split_xch_coin` and `split_cat_coins` endpoints — cleaner than Chia's approach
6. **No wallet_id system:** Sage identifies CATs by asset_id directly, not wallet_id numbers
7. **Auto-combine:** Sage v0.10.0+ has auto-combine RPCs (useful for coin management)

## Verdict: Can We Use Sage?

**YES — Sage has every RPC endpoint we need.** In fact, Sage's API is arguably better-designed for our use case because it has dedicated coin splitting/joining endpoints and separates XCH/CAT coin queries.

### What Would Need to Change

The bot currently uses `wallet.py` which talks to the Chia wallet RPC. To support Sage, we'd need:

1. **Abstract the wallet layer** — Create a `WalletInterface` that both `ChiaWallet` and `SageWallet` implement
2. **Handle amount format differences** — Sage uses string mojos, Chia uses int mojos
3. **Different coin query pattern** — Sage separates `get_xch_coins`/`get_cat_coins` instead of `get_spendable_coins(wallet_id)`
4. **Different offer format** — Sage may structure offer dicts differently (by asset_id, not wallet_id)
5. **Config additions** — `WALLET_TYPE=chia|sage`, `SAGE_RPC_URL`, `SAGE_CERT_PATH`, `SAGE_KEY_PATH`
6. **SSL cert paths** — Sage stores certs in a different location

### Recommended Approach

**Phase 1 (now):** Keep using Chia wallet as-is. The V2 bot works.

**Phase 2 (future):** Create a wallet abstraction layer:
```
wallet_interface.py  — Abstract base class
wallet_chia.py       — Current wallet.py refactored
wallet_sage.py       — New Sage implementation
```

The user would set `WALLET_TYPE=sage` in `.env` and the bot would use the appropriate implementation.

### Advantages of Sage for Our Bot

- **No full node needed** — Light wallet syncs in minutes, not hours/days
- **Faster startup** — Bot can start trading much sooner after setup
- **Better coin management** — Native split/join endpoints are cleaner than our custom approach
- **Active development** — Regular releases (v0.12.0 as of late 2025)
- **Lower resource usage** — No full node = less disk/CPU/RAM

### Risks

- **Newer/less battle-tested** than official Chia wallet
- **RPC is opt-in** — User must manually enable it in settings
- **Light wallet limitations** — May have slower offer detection since it doesn't have full mempool visibility
- **API differences** — The offer dict format might not be identical to Chia's, requiring careful mapping
- **Documentation is sparse** — No official API docs page yet (PowerSage wrapper is the best reference)

## Resources

- Sage GitHub: https://github.com/xch-dev/sage
- Sage Website: https://sagewallet.net/
- PowerSage (PowerShell RPC wrapper, shows all endpoints): https://github.com/AbandonedLand/PowerSage
- Chia Wallet SDK (Sage's foundation): https://github.com/xch-dev/chia-wallet-sdk
