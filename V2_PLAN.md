# Chia CAT Market Maker V2 — "The Smart One"
## Full Architecture Plan & Build Roadmap

---

## What This Document Is

This is the complete plan for rebuilding the market maker bot. Nothing gets coded until you (Tim) approve this plan. Every section explains the **what** and the **why** in plain language, with technical details included for reference during the build.

---

## The Big Picture

V1 works. It survived 72 restarts, handled 47+ fills, and runs unattended. But it has two problems:

1. **The monolith problem** — `api_server.py` is 7,500 lines doing everything. Changing one thing risks breaking something unrelated.
2. **The "dumb" problem** — The bot places orders at fixed distances from a price. It doesn't know or care about its inventory, doesn't adjust to volatility, and can't tell you if it's making money.

V2 fixes both: break the monolith into clean modules, then add the smart features on top.

---

## Architecture: The New Module Structure

Instead of one massive file, V2 has **8 focused modules** plus a thin API layer. Each module does one job and has a clear interface.

```
┌──────────────────────────────────────────────────────┐
│                    bot_gui.html                       │
│              (Web dashboard — WebSocket)              │
└───────────────────────┬──────────────────────────────┘
                        │ WebSocket + REST
┌───────────────────────▼──────────────────────────────┐
│                   api_server.py                       │
│          (Thin Flask layer — routes only)             │
└───┬───────┬───────┬───────┬───────┬───────┬──────────┘
    │       │       │       │       │       │
    ▼       ▼       ▼       ▼       ▼       ▼
┌───────┐┌───────┐┌───────┐┌───────┐┌───────┐┌────────┐
│ Price ││Offer  ││ Fill  ││ Coin  ││Dexie  ││ Risk   │
│Engine ││Manager││Tracker││Manager││Manager││Manager │
└───┬───┘└───┬───┘└───┬───┘└───┬───┘└───┬───┘└───┬────┘
    │       │       │       │       │       │
    └───────┴───────┴───┬───┴───────┴───────┘
                        │
              ┌─────────▼──────────┐
              │     wallet.py      │
              │  (RPC — unchanged) │
              └─────────┬──────────┘
                        │
              ┌─────────▼──────────┐
              │   SQLite Database  │
              │  (Single source    │
              │   of truth)        │
              └────────────────────┘
```

### Module Breakdown

| Module | File | What It Does | Lines (est.) |
|--------|------|-------------|-------------|
| **Price Engine** | `price_engine.py` | Fetches prices from Dexie + TibetSwap, calculates combined price, tracks volatility history, detects arbitrage | ~400 |
| **Offer Manager** | `offer_manager.py` | Creates offer ladders, handles requoting when price moves, manages expiry, cancels stale offers | ~600 |
| **Fill Tracker** | `fill_tracker.py` | Detects fills by comparing offer snapshots, records to database, matches buy/sell into round-trips for PnL | ~400 |
| **Coin Manager** | `coin_manager.py` | Monitors coin counts, triggers splitting when low, manages the coin prep subprocess, handles "Close the Gap" | ~500 |
| **Dexie Manager** | `dexie_manager.py` | Posts offers to Dexie orderbook, tracks which offers are posted, prevents duplicates, persistent queue that survives restarts | ~300 |
| **Risk Manager** | `risk_manager.py` | NEW — Tracks inventory position, calculates dynamic spreads, enforces risk limits, circuit breakers | ~500 |
| **Bot Loop** | `bot_loop.py` | The orchestrator — calls modules in sequence each cycle, handles startup/shutdown, event coordination | ~400 |
| **API Server** | `api_server.py` | Thin Flask layer — just routes HTTP/WebSocket calls to the right module. No business logic. | ~500 |
| **Database** | `database.py` | SQLite wrapper — all state reads/writes go through here. Atomic transactions, proper schema. | ~300 |
| **Config** | `config.py` | Loads .env, validates settings, provides typed access to all config values | ~200 |

**Total estimated: ~4,200 lines** (down from 7,500 in `api_server.py` alone — because clean modules eliminate duplication)

### What Stays The Same

These V1 modules are already well-structured and will be carried forward with minimal changes:

- **wallet.py** — Already a clean RPC abstraction. Keep as-is, maybe add a few helper functions.
- **dexie.py** — Simple price fetcher. Gets absorbed into price_engine.py.
- **tibet_integration.py** — Clean pricing module. Gets absorbed into price_engine.py.
- **coin_prep_worker.py** — Subprocess model works well. Keep the parallel optimization.
- **bot_gui.html** — GUI design is good. Upgrade from polling to WebSocket, add PnL dashboard tab.

---

## The Database: SQLite Replaces JSON + CSV

The single biggest quality-of-life improvement. Instead of `offers_state.json` (142KB of tangled data) + `fills.csv` + scattered global variables, everything lives in one SQLite database.

### Why SQLite

- **Atomic writes** — No more half-written JSON files if the bot crashes mid-save
- **Queryable** — "Show me all fills from the last 24 hours where I bought" is one line, not a CSV parse
- **Survives restarts** — All state persists automatically
- **trade_id is always the key** — No more keying by dexie_id (the bug that hit us three times)

### Database Schema

```
TABLE offers
─────────────────────────────────────────────────
trade_id        TEXT PRIMARY KEY    -- Chia trade ID (universal key)
side            TEXT                -- 'buy' or 'sell'
price_xch       REAL                -- Price in XCH per CAT
size_xch        REAL                -- Offer size in XCH
size_cat        REAL                -- Offer size in CAT
tier            TEXT                -- 'inner', 'mid', 'outer', 'extreme'
status          TEXT                -- 'open', 'filled', 'cancelled', 'expired'
dexie_id        TEXT                -- Dexie offer ID (nullable)
dexie_posted    INTEGER             -- 1 if successfully posted to Dexie
created_at      TEXT                -- ISO timestamp
filled_at       TEXT                -- ISO timestamp (nullable)
cancelled_at    TEXT                -- ISO timestamp (nullable)
expires_at      TEXT                -- ISO timestamp
cat_asset_id    TEXT                -- Which CAT pair this offer is for

TABLE fills
─────────────────────────────────────────────────
fill_id         INTEGER PRIMARY KEY AUTOINCREMENT
trade_id        TEXT                -- Links to offers table
side            TEXT                -- 'buy' or 'sell'
price_xch       REAL                -- Fill price
size_xch        REAL                -- Fill size in XCH
size_cat        REAL                -- Fill size in CAT
filled_at       TEXT                -- ISO timestamp
round_trip_id   INTEGER             -- Links buy+sell into a pair (nullable)
pnl_xch         REAL                -- Profit/loss for this fill's round trip (nullable)
cat_asset_id    TEXT                -- Which CAT pair

TABLE inventory
─────────────────────────────────────────────────
id              INTEGER PRIMARY KEY AUTOINCREMENT
timestamp       TEXT                -- ISO timestamp
cat_asset_id    TEXT                -- Which CAT pair
net_position    REAL                -- Running total: + means long CAT, - means short
xch_balance     REAL                -- XCH balance at this point
cat_balance     REAL                -- CAT balance at this point
mid_price       REAL                -- Reference price at this point

TABLE price_history
─────────────────────────────────────────────────
id              INTEGER PRIMARY KEY AUTOINCREMENT
timestamp       TEXT                -- ISO timestamp
cat_asset_id    TEXT
dexie_price     REAL
tibet_price     REAL
combined_price  REAL
strategy_used   TEXT

TABLE events
─────────────────────────────────────────────────
id              INTEGER PRIMARY KEY AUTOINCREMENT
timestamp       TEXT                -- ISO timestamp
event_type      TEXT                -- 'fill', 'offer_created', 'price_change', 'error', 'coin_prep', etc.
severity        TEXT                -- 'info', 'warning', 'error'
message         TEXT                -- Human-readable description
data            TEXT                -- JSON blob for structured data

TABLE config_history
─────────────────────────────────────────────────
id              INTEGER PRIMARY KEY AUTOINCREMENT
timestamp       TEXT
key             TEXT
old_value       TEXT
new_value       TEXT
```

---

## Smart Feature #1: Inventory Tracking & Skewed Quoting

### What It Does (Plain Language)

Right now, the bot doesn't know if it's accumulated a mountain of CAT tokens from buy fills while nothing sold. It just keeps quoting the same prices both ways.

With inventory tracking, the bot knows its "position" — how much it's leaning to one side. If it's bought way more than it's sold (long CAT), it makes sells cheaper (to attract buyers) and buys more expensive (to discourage more buying). This naturally rebalances without you having to intervene.

### How It Works

```
Net Position = Total CAT bought - Total CAT sold

If position > 0 (long CAT, accumulated too much):
  → Tighten sell spread (make it easier to sell)
  → Widen buy spread (less eager to buy more)

If position < 0 (short CAT, running low):
  → Tighten buy spread (attract more buying)
  → Widen sell spread (less eager to sell more)

If position ≈ 0 (balanced):
  → Use normal symmetric spread
```

### The Skew Formula

```
inventory_ratio = net_position / max_position    (ranges from -1 to +1)
skew_factor = inventory_ratio × SKEW_INTENSITY   (configurable, default 0.5)

buy_spread  = base_spread × (1 + skew_factor)
sell_spread = base_spread × (1 - skew_factor)
```

Example: If you're 60% long and SKEW_INTENSITY is 0.5:
- `inventory_ratio = 0.6`
- `skew_factor = 0.3`
- Buy spread becomes 30% wider (less eager to buy more)
- Sell spread becomes 30% tighter (encouraging sells)

### Settings You Control

| Setting | Default | What It Does |
|---------|---------|-------------|
| `SKEW_INTENSITY` | 0.5 | How aggressively to skew (0 = off, 1 = very aggressive) |
| `MAX_POSITION_XCH` | 5.0 | Position size that triggers maximum skew |
| `INVENTORY_ENABLED` | true | On/off switch for the whole feature |

---

## Smart Feature #2: Dynamic Spreads

### What It Does (Plain Language)

Instead of a fixed spread (like the current 21.6%), the spread adjusts automatically based on market conditions. When things are volatile (price swinging around), spreads widen to protect you. When things are calm, spreads tighten to attract more trades.

### Spread Inputs

The dynamic spread considers four things:

1. **Volatility** — How much has the price moved in the last 1h/4h/24h?
2. **Inventory skew** — Are we leaning too far to one side? (from Feature #1)
3. **Fill rate** — Are we getting hammered with fills? (might mean informed flow)
4. **Arb gap** — Is there a big gap between Dexie and TibetSwap prices?

### The Formula

```
effective_spread = BASE_SPREAD
                 × volatility_multiplier      (1.0 to 3.0)
                 × (1 + inventory_skew)        (from Feature #1)
                 + arb_buffer                  (0 to 5%)
                 + fill_rate_buffer            (0 to 2%)

Clamped between MIN_SPREAD and MAX_SPREAD (safety bounds)
```

### Volatility Calculation

```
volatility = standard_deviation(price_changes over last N hours)
           / average_price

If volatility < 2%:  multiplier = 1.0  (calm — tight spreads)
If volatility 2-5%:  multiplier = 1.5  (moderate — widen a bit)
If volatility 5-10%: multiplier = 2.0  (volatile — widen significantly)
If volatility > 10%: multiplier = 3.0  (extreme — maximum protection)
```

### Settings You Control

| Setting | Default | What It Does |
|---------|---------|-------------|
| `BASE_SPREAD` | 0.10 (10%) | Starting spread before adjustments |
| `MIN_SPREAD` | 0.05 (5%) | Spread never goes below this |
| `MAX_SPREAD` | 0.30 (30%) | Spread never exceeds this |
| `VOLATILITY_WINDOW_HOURS` | 4 | How far back to look for volatility |
| `DYNAMIC_SPREAD_ENABLED` | true | On/off switch |

---

## Smart Feature #3: Tiered Order Book

### What It Does (Plain Language)

Instead of 50 identical offers per side (all 0.5 XCH), V2 places different-sized offers at different distances from the mid price. Bigger offers near the middle (where fills are most likely and most profitable), smaller offers further out (to catch big moves with less risk).

### The Tiers

| Tier | Distance from Mid | Size per Offer | Count per Side | XCH Committed | Purpose |
|------|-------------------|---------------|----------------|---------------|---------|
| **Inner** | 2-5% | 1.0 XCH | 5 | 5.0 XCH | Most likely to fill, best price |
| **Mid** | 5-10% | 0.5 XCH | 15 | 7.5 XCH | Bread and butter |
| **Outer** | 10-15% | 0.25 XCH | 20 | 5.0 XCH | Catch bigger moves |
| **Extreme** | 15-25% | 0.1 XCH | 10 | 1.0 XCH | Black swan protection |
| **Total** | | | **50** | **18.5 XCH** | |

### Why This Is Better

In V1, all 50 offers at 0.5 XCH means 25 XCH committed per side, spread evenly. Most fills happen near the mid price, so most of your capital sits in the outer tiers doing nothing.

With tiers, 5 XCH sits in the inner tier where fills actually happen (27% of capital at the best prices), while only 1 XCH sits at the extremes as insurance.

### Settings You Control

| Setting | Default | What It Does |
|---------|---------|-------------|
| `TIER_ENABLED` | true | On/off (falls back to flat sizing if off) |
| `INNER_SIZE_XCH` | 1.0 | Size of inner tier offers |
| `MID_SIZE_XCH` | 0.5 | Size of mid tier offers |
| `OUTER_SIZE_XCH` | 0.25 | Size of outer tier offers |
| `EXTREME_SIZE_XCH` | 0.1 | Size of extreme tier offers |
| Tier boundaries | 5%, 10%, 15% | Where each tier starts |

---

## Smart Feature #4: PnL Dashboard

### What It Does (Plain Language)

Finally answers the question: "Am I actually making money?" V1 records fills but doesn't track profit. V2 matches every buy with a corresponding sell to calculate actual profit per round-trip.

### Round-Trip Matching

```
Buy 1000 MZ at 0.00006 XCH each  (cost: 0.06 XCH)
Sell 1000 MZ at 0.000065 XCH each (received: 0.065 XCH)

Round-trip PnL = 0.065 - 0.06 = 0.005 XCH profit (8.3%)
```

The system uses FIFO (first in, first out) matching — the oldest unmatched buy gets paired with the next sell.

### What The Dashboard Shows

1. **Realised PnL** — Profit from completed round-trips (buy then sell, or sell then buy)
2. **Unrealised PnL** — Current inventory valued at market price vs what you paid
3. **Total PnL** — Realised + Unrealised
4. **Spread Capture** — What spread you actually earned vs what you quoted
5. **Win Rate** — What percentage of round-trips were profitable
6. **Inventory Over Time** — Chart showing how your position has changed

### GUI Addition

New "PnL" tab in the dashboard showing:
- Summary cards (total PnL, today's PnL, win rate)
- Round-trip history table (each buy-sell pair with profit)
- Inventory chart (line graph of net position over time)
- Spread capture chart (theoretical vs actual)

---

## Smart Feature #5: Sniper V2

### What Changes

The V1 sniper (~50 lines) detects TibetSwap swaps and responds in 3-5 seconds. V2 keeps this but makes it smarter:

1. **Size awareness** — Sniper offer size based on the arb gap size (bigger gap = bigger offer)
2. **Inventory awareness** — Won't snipe if it would push inventory too far in one direction
3. **Cooldown** — Configurable minimum time between snipes to avoid over-trading
4. **PnL tracking** — Sniper fills get their own PnL category so you can see how profitable sniping is

---

## WebSocket GUI Upgrade

### Why

V1's GUI polls the API every 2-5 seconds. This means:
- Fills can be 5 seconds old before you see them
- Multiple parallel HTTP requests every few seconds
- Timing bugs where GUI shows stale data

### What Changes

The bot pushes updates to the GUI instantly via WebSocket:
- Fill happens → GUI shows it immediately
- Price changes → Prices update in real-time
- Offer created/cancelled → Offer list updates instantly
- No more polling loops in the JavaScript

### What Stays The Same

- Same dark theme design
- Same layout and controls
- Same HTML file approach (no build tools needed)
- REST API still available for non-real-time operations (config changes, manual actions)

---

## Build Phases

The build is split into 5 phases. Each phase produces a **working bot** — you can test and run it after each phase. We never have a broken bot between phases.

### Phase 1: Foundation (The Boring But Critical Bit)
**Goal:** Break up the monolith, add SQLite, keep existing behaviour identical.

| Step | What | Why |
|------|------|-----|
| 1.1 | Create `database.py` with full schema | Single source of truth from day one |
| 1.2 | Create `config.py` to load .env | Clean config access everywhere |
| 1.3 | Extract `price_engine.py` from api_server | Absorbs dexie.py + tibet_integration.py |
| 1.4 | Extract `offer_manager.py` | All offer create/cancel/track/expiry logic |
| 1.5 | Extract `fill_tracker.py` | Fill detection + recording to SQLite |
| 1.6 | Extract `dexie_manager.py` | Dexie posting with persistent queue in SQLite |
| 1.7 | Extract `coin_manager.py` | Coin health + prep subprocess management |
| 1.8 | Create `bot_loop.py` orchestrator | Calls modules in sequence |
| 1.9 | Slim down `api_server.py` to thin Flask layer | Just routes, no logic |
| 1.10 | Test: bot runs identically to V1 | Same behaviour, new structure |

**Estimated effort:** Largest phase. This is the foundation everything else builds on.
**Risk:** Regressions. We test after every extraction step.
**Deliverable:** Bot runs exactly like V1 but with clean modules and SQLite.

### Phase 2: Inventory & Dynamic Spreads
**Goal:** Make the bot inventory-aware and dynamically adjust spreads.

| Step | What | Why |
|------|------|-----|
| 2.1 | Create `risk_manager.py` | Home for inventory + spread logic |
| 2.2 | Add inventory tracking to fill_tracker | Track net position on every fill |
| 2.3 | Implement spread skewing | Inventory-aware bid/ask adjustment |
| 2.4 | Add volatility tracking to price_engine | Store price history, calculate vol |
| 2.5 | Implement dynamic spread formula | Combine vol + inventory + arb gap |
| 2.6 | Add GUI controls for new settings | Toggle inventory/dynamic spread, set params |
| 2.7 | Test with conservative defaults | Start cautious, tune later |

**Estimated effort:** Medium. Logic is new but modules are clean.
**Risk:** Spread too tight or too wide. Safety bounds (MIN/MAX_SPREAD) prevent disasters.
**Deliverable:** Bot adjusts spreads based on market conditions and inventory.

### Phase 3: Tiered Orders & PnL
**Goal:** Smarter order sizing and real profit tracking.

| Step | What | Why |
|------|------|-----|
| 3.1 | Add tier logic to offer_manager | Create different-sized offers at different distances |
| 3.2 | Update coin_manager for tiered coin sizes | Need different coin denominations for different tiers |
| 3.3 | Implement round-trip matching in fill_tracker | FIFO pairing of buys and sells |
| 3.4 | Calculate realised + unrealised PnL | The "am I making money?" answer |
| 3.5 | Build PnL dashboard section in GUI | Summary cards + charts |
| 3.6 | Add spread capture tracking | Theoretical vs actual spread earned |
| 3.7 | Test with real fills | Verify PnL calculations are accurate |

**Estimated effort:** Medium. Tier logic needs careful coin preparation.
**Risk:** Coin prep for mixed sizes is more complex. Solve in 3.2.
**Deliverable:** Bot places tiered orders and shows real PnL.

### Phase 4: WebSocket GUI & Sniper V2
**Goal:** Real-time GUI updates and smarter sniping.

| Step | What | Why |
|------|------|-----|
| 4.1 | Add Flask-SocketIO to api_server | WebSocket support |
| 4.2 | Emit events from all modules | Price, fill, offer, coin events pushed to GUI |
| 4.3 | Update bot_gui.html to use WebSocket | Replace polling with event listeners |
| 4.4 | Keep REST API for manual actions | Config changes, start/stop don't need WebSocket |
| 4.5 | Upgrade sniper with size/inventory awareness | Smarter arb response |
| 4.6 | Add sniper PnL category | Track sniper profit separately |
| 4.7 | Full integration test | Everything working together |

**Estimated effort:** Medium. WebSocket is well-supported in Flask.
**Risk:** WebSocket disconnects need graceful fallback. Keep REST as backup.
**Deliverable:** Instant GUI updates and smarter sniping.

### Phase 5: Multi-Pair & Backtesting (Future)
**Goal:** Trade multiple CAT pairs and test strategies on historical data.

| Step | What | Why |
|------|------|-----|
| 5.1 | Add pair-scoped config and state | Each pair has independent settings |
| 5.2 | Update coin_manager for multi-wallet | Separate coin pools per pair |
| 5.3 | Pair selector in GUI with per-pair dashboards | Monitor all pairs from one screen |
| 5.4 | Build backtesting engine | Replay price history through spread logic |
| 5.5 | "What if" simulator in GUI | Test parameter changes before deploying |

**Estimated effort:** Large. Multi-pair is a significant expansion.
**Note:** This phase is optional/future. Phases 1-4 deliver a complete "smart" market maker.

---

## Testing Strategy

V1 had no automated tests. V2 will have a practical testing approach that works for our prompting-based development:

### Syntax Verification (Every Change)
```bash
python -c "import ast; ast.parse(open('module.py').read())"
```
Run after every file edit. Catches typos and syntax errors immediately.

### Module Import Test (Every New Module)
```bash
python -c "from price_engine import PriceEngine; print('OK')"
```
Verify each module imports without errors.

### Startup Test (After Each Phase)
```
Start bot → verify all modules load → check GUI connects → verify offers display
```
The same manual test from V1, but now we know exactly which module to check if something fails.

### Mock Wallet (Phase 2+)
A fake wallet module that simulates:
- Coin balances (configurable)
- Offer creation (instant, no blockchain)
- Fills (triggered manually or on timer)

This lets us test inventory tracking, PnL calculation, and dynamic spreads without waiting for real blockchain transactions.

---

## Files That Get Created

### New Files
| File | Purpose |
|------|---------|
| `database.py` | SQLite wrapper, schema, migrations |
| `config.py` | Typed config loading from .env |
| `price_engine.py` | Combined Dexie + Tibet pricing + volatility |
| `offer_manager.py` | Offer lifecycle management |
| `fill_tracker.py` | Fill detection + round-trip PnL |
| `dexie_manager.py` | Dexie posting with persistent queue |
| `coin_manager.py` | Coin health + prep orchestration |
| `risk_manager.py` | Inventory + dynamic spreads + circuit breakers |
| `bot_loop.py` | Main orchestrator |
| `bot.db` | SQLite database file (auto-created) |

### Modified Files
| File | Changes |
|------|---------|
| `api_server.py` | Slimmed to ~500 lines — just Flask routes + WebSocket |
| `bot_gui.html` | WebSocket support, PnL tab, tier display, inventory indicator |
| `wallet.py` | Minor additions only — already well-structured |
| `coin_prep_worker.py` | Minor — support mixed coin sizes for tiers |
| `CLAUDE.md` | Updated with V2 architecture and conventions |

### Removed/Replaced
| File | Replaced By |
|------|------------|
| `offers_state.json` | SQLite `offers` table |
| `fills.csv` | SQLite `fills` table |
| `dexie.py` | Absorbed into `price_engine.py` |
| `tibet_integration.py` | Absorbed into `price_engine.py` |
| `coin_management.py` | Absorbed into `coin_manager.py` |
| `spacescan.py` | Absorbed into `price_engine.py` (if needed) |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Regression during monolith breakup | Test after every extraction step. Keep V1 as backup. |
| Dynamic spread too aggressive | MIN_SPREAD and MAX_SPREAD safety bounds. Start conservative. |
| Inventory skew over-corrects | SKEW_INTENSITY starts at 0.3 (gentle). Increase after observation. |
| SQLite corruption | WAL mode for safe concurrent reads. Backup on startup. |
| WebSocket disconnects | REST API always available as fallback. Auto-reconnect in GUI. |
| Coin prep for mixed tier sizes | Solve in Phase 3 step 3.2 specifically. Test before enabling tiers. |
| State migration from V1 | Import existing fills.csv and offers_state.json into SQLite on first V2 startup. |

---

## How We'll Work Together

Based on what worked well in V1:

1. **You describe what you want** → I explain what I'll do and why
2. **I code in small steps** → Each step is testable, you can verify
3. **I explain every change** → No mystery code. You should always understand what the bot is doing.
4. **We test after every change** → Syntax check, import check, startup check
5. **Planning before coding** → Every new feature gets discussed before implementation
6. **Your decision on trade-offs** — When there's a choice (tighter spreads vs safety, complexity vs simplicity), I present the options and you decide

---

## What To Approve

Before we start coding, please confirm:

1. **Phase order** — Are you happy starting with Phase 1 (foundation) first?
2. **Module structure** — Does the 8-module breakdown make sense?
3. **Smart features** — Are inventory, dynamic spreads, tiers, and PnL the right priorities?
4. **Database** — Happy with SQLite replacing JSON/CSV?
5. **Anything missing?** — Features or concerns not covered here?

Once you approve, we start Phase 1, Step 1.1: creating the database module.
