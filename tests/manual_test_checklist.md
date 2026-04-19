# CATalyst — Manual Test Checklist

One-page script for a new Claude (or human) session to verify every user-facing
flow against the running bot. Designed to be re-used after any significant
change — see the **"Feature-specific smoke tests"** section at the bottom for
the subset that matches a recent commit.

> **Setup preamble** (30 seconds)
> * Make sure Sage wallet is open with RPC enabled (`Settings → Advanced → Start RPC Client`)
> * Launch: `python desktop_app.py --flask` (or the desktop shortcut)
> * Open `http://127.0.0.1:5000` in a browser (or via the Preview MCP:
>   `preview_start` with the `bot-gui` config in `.claude/launch.json`)
> * Click through: **Continue** → **Connect to Sage** → pick Test Wallet 6
>   (fingerprint `2981073251`) → **Skip** the Splash P2P prompt → **Continue with
>   Configured Key** on the Spacescan prompt
> * You should land on the Dashboard

---

## Table of contents

1. [Dashboard tab](#dashboard)
2. [Settings tab](#settings)
3. [Liquidity Mode feature](#liquidity-mode)
4. [Smart Settings (Auto-Fill)](#smart-settings)
5. [Coin Prep flow](#coin-prep)
6. [PnL tab](#pnl)
7. [Offers tab](#offers)
8. [Logs tab](#logs)
9. [Live controls (mid-run)](#live-controls)
10. [Reserve + topup behaviour](#reserves)
11. [Shutdown and restart](#shutdown)
12. [API smoke tests (curl)](#api-smoke)
13. [Feature-specific smoke tests](#feature-smokes)

---

<a id="dashboard"></a>
## 1. Dashboard tab

| # | Test | Expected |
|---|---|---|
| 1.1 | Status badge shows "◯ Stopped" in the titlebar area when bot not running | yes |
| 1.2 | Wallet balance card populates with XCH total + CAT total | ≤ 10 s after Sage connect |
| 1.3 | Coin inventory card shows `xch_total_coins`, `cat_total_coins` | non-zero after wallet sync |
| 1.4 | Trading Pair selector lists all MZ_XCH and other CAT pools from TibetSwap | refresh button works |
| 1.5 | After picking a pair, Mid Price chart starts filling | ~5 s per sample, 240-point history |
| 1.6 | Start Bot button enabled when: wallet synced + trading pair picked + settings saved + coins prepped | red disabled states with tooltips when not |

<a id="settings"></a>
## 2. Settings tab

| # | Test | Expected |
|---|---|---|
| 2.1 | Trading Pair card shows current CAT + "Change Pair" button works | existing pair loads into both selectors |
| 2.2 | "Settings locked while bot is running" banner appears when `bot.running=true` | banner disappears after Stop |
| 2.3 | Reserves: XCH slider + manual input stay in sync | 5/10/25/50% preset buttons all work |
| 2.4 | Reserves: CAT slider respects `cat_reserve_balance` (current CAT balance) | |
| 2.5 | Base Trade Size propagates to tier sizes via `updateTierSizesFromBase` | inner = 2×, outer = 0.5×, extreme = 0.2× |
| 2.6 | Enable Tiered Sizing toggle → shows/hides tier size grid, count section, spare section | 3 sections appear/disappear together |
| 2.7 | Reverse Buy Ladder toggle swaps buy-inner ↔ buy-extreme field values | on toggle, XCH row flips orientation |
| 2.8 | Dry Run Mode checkbox + hint | when on, offers are logged but not sent |
| 2.9 | Save button writes to `.env` + shows toast | ~200 ms round trip |
| 2.10 | Export .env dumps a timestamped file | downloads as attachment |
| 2.11 | Pending-changes banner appears when any field is dirty | clears after Save |

<a id="liquidity-mode"></a>
## 3. Liquidity Mode feature *(shipped 2026-04-19, commits `1192045` + `0dbbcf3`)*

Located at the top of Settings, just under Trading Pair.

| # | Test | Expected |
|---|---|---|
| 3.1 | Three cards render: Two-Sided, Buy Only (Accumulate), Sell Only (Distribute) | icons `📈📉 / 📈 / 📉` |
| 3.2 | Currently-selected card has coloured highlight (blue / green / red) | click another → highlight moves |
| 3.3 | While bot is running, cards have `.disabled` class and inline hint appears | clicking is a no-op + toast "Stop the bot..." |
| 3.4 | After clicking **Buy Only**: Max Sell, Sell ladder sizes, CAT count row, CAT spare row, Sell prep column all hide | body class `liquidity-mode-buy-only` is set |
| 3.5 | After clicking **Sell Only**: Max Buy, Buy ladder sizes, XCH count row, XCH spare row, Buy prep column, Reverse Buy Ladder toggle all hide | body class `liquidity-mode-sell-only` |
| 3.6 | Inventory Management section hides in both single-sided modes | skew is meaningless one-sided |
| 3.7 | Sniper config (size / prep count / re-arm fields + hint) hides and is replaced by "🎯 Sniper unavailable in single-sided mode" banner | banner has grey background |
| 3.8 | Auto-Fill title switches: `Auto-Fill Settings` → `Auto-Fill — Accumulation Plan` / `— Distribution Plan` | subtitle also mode-specific |
| 3.9 | **Coin Prep Summary** Buy/Sell columns collapse to single column in single-sided mode | only active side's counts+sizes shown |
| 3.10 | Wallet-aware hint appears when wallet is ≥92% one asset | "Apply suggestion" button auto-switches mode |

<a id="smart-settings"></a>
## 4. Smart Settings (Auto-Fill)

| # | Test | Expected |
|---|---|---|
| 4.1 | Risk Profile tri-selector (Conservative / Balanced / Aggressive) picks one at a time | visually toggles |
| 4.2 | Set XCH reserve to 5 → click Smart Settings → no error toast | completes in ~3-8 s |
| 4.3 | Form populates: Max Buy, Max Sell, tier sizes (buy + sell rows), tier counts, spare counts, topup pools | all fields filled |
| 4.4 | Capital plan message shows strategy string | e.g. "standard 4-tier ladder · 24B/23S offers · 87.40 XCH trading (85%)" |
| 4.5 | **Liquidity Mode: Buy Only** + Smart Settings → `max_active_sell=0`, all `sell_*_size_xch=null`, `sniper_enabled=false`, `topup_pool_cat=0` | verify via: `fetch('/api/smart-defaults?liquidity_mode=buy_only&...').then(r=>r.json())` |
| 4.6 | **Liquidity Mode: Sell Only** + Smart Settings → `max_active_buy=0`, all `buy_*_size_xch=null`, `sniper_enabled=false`, `topup_pool_xch=0`, `buy_ladder_reversed=false` | similar |
| 4.7 | Under Reverse Buy Ladder + Two-Sided, tier sizes follow the reverse orientation (inner smaller than extreme) | (per 2026-04-19 ea0d1b5 fix) |
| 4.8 | Clicking Smart Settings twice in a row with same inputs → same output | idempotent |

<a id="coin-prep"></a>
## 5. Coin Prep flow

| # | Test | Expected |
|---|---|---|
| 5.1 | Coin Prep Summary card shows Buy and Sell columns side-by-side under two-sided mode | totals appear in amber |
| 5.2 | "Coin prep impossible" banner appears in red when totals > wallet balance + 0.5% tolerance | scrolls into view |
| 5.3 | Clicking "Prepare Coins" button with no history (fresh run) → confirm modal → progress view | skips history-choice modal |
| 5.4 | Clicking "Prepare Coins" with ≥1 fill OR ≥1 round-trip → **history-choice modal** appears first: "Keep your trading history?" with three buttons | (shipped 2026-04-19 in `095a80d`) |
| 5.5 | History modal shows exact counts: fills, round trips, PnL XCH, net position | live counts from `/api/pnl/reset-preview` |
| 5.6 | **Keep history** → proceeds with `full_reset=false`; fills/round-trips/position survive | coin prep still rebuilds coins |
| 5.7 | **Start fresh** → proceeds with `full_reset=true`; everything wiped | match pre-2026-04-19 behaviour |
| 5.8 | **Cancel** → modal closes, nothing changes | prep does not run |
| 5.9 | Progress view: percentage bar, phase label, XCH/CAT coin counts live-update | worker emits phase transitions |
| 5.10 | If worker fails: Coin Prep Failed modal shows specific reason (e.g. "pool_exceeds_avail"), not just "❌ failed" | (shipped 2026-04-19 in `46f7844`) |
| 5.11 | After success: Done button → returns to Dashboard, Start Bot is enabled | |

<a id="pnl"></a>
## 6. PnL tab

| # | Test | Expected |
|---|---|---|
| 6.1 | Session/Round Trips/Total Fills hero cards populate live | updates on each fill |
| 6.2 | Volume breakdown row: Bought, Sold, Net Flow with signed XCH | + green / − red |
| 6.3 | Cumulative PnL chart shows per-fill bars | "Collecting data..." until ≥1 fill |
| 6.4 | Inventory Position panel: gauge bar, Net Position (CAT), Position Limit (XCH) | gauge centred at 50% |
| 6.5 | Position drift mini-chart | renders as line/area |
| 6.6 | **Single-sided mode banner** at top of PnL tab when mode ≠ two_sided | shows avg price + notional vs mid |
| 6.7 | **Reset Position** button: confirm → `/api/fills/purge` → clears fills | (existing legacy behaviour) |
| 6.8 | **⚠ Reset All Stats** button: confirm modal with full scope detail → `/api/pnl/reset` with `{confirm:"RESET"}` | full wipe (including runtime stats) |
| 6.9 | Current Spreads card + Sniper Stats card both update | buy/sell spread % live |

<a id="offers"></a>
## 7. Offers tab

| # | Test | Expected |
|---|---|---|
| 7.1 | Open Offers table lists each live offer | price, size, tier, Dexie link |
| 7.2 | "Dexie ✅" badge on each if `dexie_posted=true` | |
| 7.3 | Dexie link opens in external browser frame | not in-tab |
| 7.4 | Filter-by-side (Buy only / Sell only / All) works | |
| 7.5 | Cancel button on a single row → confirm → offer disappears from list within ~3 s | Sage logs show cancel |
| 7.6 | Cancel All button (when bot is stopped) | shows bulk-cancel confirm |
| 7.7 | Recently Filled section below shows last ~20 fills | filled_at timestamp + Dexie link |

<a id="logs"></a>
## 8. Logs tab

| # | Test | Expected |
|---|---|---|
| 8.1 | Live log feed scrolls automatically | "Auto-scroll" toggle pauses it |
| 8.2 | Severity filter (info / success / warning / error) | chips filter in place |
| 8.3 | Search box filters by substring | case-insensitive |
| 8.4 | Export logs downloads `.log` file | timestamped filename |
| 8.5 | Coin prep subsections visually distinct | colour-coded |

<a id="live-controls"></a>
## 9. Live controls (mid-run)

While the bot is running, these should take effect without restart:

| # | Control | Expected |
|---|---|---|
| 9.1 | Base Spread slider (%) | next cycle uses new spread |
| 9.2 | Requote Threshold (bps) | next requote decision |
| 9.3 | Inventory skew intensity | only in two-sided |
| 9.4 | Max active buy / sell | clamps ladder next cycle |
| 9.5 | Dry Run toggle | flips without requiring stop |

Anything that's *capital allocation* (trade size, tier sizes, Liquidity Mode)
requires **stop first**.

<a id="reserves"></a>
## 10. Reserves and topup behaviour

| # | Test | Expected |
|---|---|---|
| 10.1 | XCH reserve > 0 → that amount is excluded from trading budget | visible in Smart Settings breakdown |
| 10.2 | Topup pool reserve = residual of (balance − tiers − reserve − headroom) | Inventory Position panel shows it |
| 10.3 | In buy_only, only XCH topup pool is tracked | CAT topup = 0 |
| 10.4 | In sell_only, only CAT topup pool is tracked | XCH topup = 0 |

<a id="shutdown"></a>
## 11. Shutdown and restart

| # | Test | Expected |
|---|---|---|
| 11.1 | Stop Bot button → cancels all open offers with confirm modal | offers go to "Cancelling" state then disappear |
| 11.2 | If cancel takes >60 s, `position_hard_guard_blocked` warning is rate-limited to 1/min | (shipped 2026-04-18 in `f083abe`) |
| 11.3 | Close app button → triggers shutdown sequence | PyWebView quits; Flask server also terminates |
| 11.4 | Restart app → previous settings load; offers state is respected (resumes without duplicate-creating) | |
| 11.5 | On next restart, Liquidity Mode loads from env correctly (checkbox / card matches) | (shipped 2026-04-19 in `0826ba2`) |

<a id="api-smoke"></a>
## 12. API smoke tests (curl / devtools console)

Drop these into a shell with the bot running:

```bash
# Core status — should always return JSON
curl -s http://127.0.0.1:5000/api/status | jq '.running, .liquidity, .stats'

# Config dump — includes LIQUIDITY_MODE
curl -s http://127.0.0.1:5000/api/config | jq '.LIQUIDITY_MODE, .ENABLE_BUY, .ENABLE_SELL, .BUY_LADDER_REVERSED'

# Smart Settings in each mode — verify zero'd fields
for m in two_sided buy_only sell_only; do
  echo "=== $m ==="
  curl -s "http://127.0.0.1:5000/api/smart-defaults?xch_reserve=5&cat_reserve=10000&risk_profile=balanced&liquidity_mode=$m" | \
    jq '{liquidity_mode, max_active_buy, max_active_sell, sniper_enabled, buy_ladder_reversed}'
done

# PnL preview — what Reset All Stats would clear
curl -s http://127.0.0.1:5000/api/pnl/reset-preview | jq .

# PnL — live stats
curl -s http://127.0.0.1:5000/api/pnl | jq '{realised_pnl_xch, total_fills, round_trips, net_position_cat}'
```

<a id="feature-smokes"></a>
## 13. Feature-specific smoke tests

Use when verifying a specific recent commit:

### Liquidity Mode (`1192045` + `0dbbcf3`)
- 3.1 – 3.10 (all Liquidity Mode UI)
- 4.5, 4.6 (smart-defaults mode branching)
- 5.1 (coin-prep summary adapts)
- 6.6 (PnL banner in single-sided)
- 10.3, 10.4 (topup pool)

### PnL reset + coin-prep history choice (`095a80d`)
- 5.3, 5.4, 5.5, 5.6, 5.7, 5.8
- 6.7, 6.8

### Reverse-buy storage revert (`ea0d1b5` + `0826ba2`)
- 2.7 (toggle swap)
- 4.7 (Smart Settings reverse-buy math)
- 11.5 (env round-trip)

### Coin prep failure surfacing (`46f7844`)
- 5.10 (specific reason in failed modal)

### Position-hard-guard rate limit (`f083abe`)
- 11.2 (once-per-60s log rate)

### Sage RPC startup hint (`5206ef6`)
- Startup flow step 4 (on wallet-not-detected path)

---

## Quick pass/fail script

If you only have 5 minutes, run this minimum viable set:

1. Startup flow → Dashboard renders
2. Settings → Liquidity Mode cards render, switching updates body class
3. Settings → Smart Settings → form populates
4. Click "Prepare Coins" → confirm modal shows coin plan
5. `/api/status` returns a `liquidity` block
6. `/api/smart-defaults?liquidity_mode=buy_only` zeroes sell fields

If any of those six fail, dig into the corresponding section above.
