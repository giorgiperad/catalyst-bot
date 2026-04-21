# CATalyst — Partial Offers Integration Plan

## What This Is

A surgical integration of CHIP-0052 partial offer support directly into the existing CATalyst codebase, controlled by a single feature flag (`OFFER_MODE`). The bot continues to run exactly as it does today in `standard` mode. When `OFFER_MODE=partial` is set (once Sage wallet supports it), it switches to a fundamentally different market-making model: instead of a ladder of many small full offers, it manages a small number of on-chain partial coins — one per price level — that any counterparty can chip away at incrementally.

No fork needed. No parallel codebase to maintain. One bot, two modes.

---

## Why This Approach

- Standard mode keeps working untouched — zero regression risk
- The feature flag means V2 can ship before Sage adds support, with the new code dormant
- The architecture of CATalyst (modular, typed, SQLite-backed) is already perfectly suited for this — the new code slots in cleanly
- When CHIP-0052 is ratified and Sage adds the RPC call, activation is a one-line config change

---

## How Partial Offer Market-Making Works (vs Standard)

| | Standard Mode (today) | Partial Mode (new) |
|---|---|---|
| Order book | 5–10 separate offer coins per side | 1 partial coin per price level |
| Fill behaviour | Offer disappears when taken | Coin reduces in size, persists on-chain |
| Requoting | Detect disappearance → cancel + recreate | Detect price drift → cancel partial coin + create new one |
| Coin usage | 1 UTXO per offer slot | 1 partial coin per price level |
| Fill detection | Offer ID disappears from Sage | On-chain coin spend → successor coin |
| Discoverability | Only via Dexie / Splash | Blockchain-native (wallet hints) |
| Multiple takers | One taker takes all | Any number of takers, any size |

---

## What Changes vs What Stays the Same

### Untouched (zero changes needed)
- `price_engine.py` — price oracle is the same
- `risk_manager.py` — circuit breakers, spread logic unchanged
- `dexie_manager.py` — still posts offer strings to Dexie (partial coins generate offer strings too)
- `splash_manager.py` / `splash_node.py` — P2P broadcast unchanged
- `sniper.py` — arb probing unchanged
- `desktop_app.py` / `bot_gui.html` — GUI gets small additions, not a rewrite
- `tx_fees.py`, `super_log.py`, `notification_manager.py` — unchanged

### Modified (targeted additions, no rewrites)
- `config.py` — add `OFFER_MODE` flag + 4 new partial-specific settings
- `wallet_sage.py` — add 2 new stub functions: `create_partial_offer()`, `cancel_partial_offer()`
- `database.py` — add `partial_offers` table (schema migration, existing tables untouched)
- `bot_loop.py` — add mode-switching at cycle start (an if/else around the offer create/track block)
- `fill_tracker.py` — extend to handle partial fill records (doesn't break standard path)
- `bot_gui.html` — add a "Partial Offers" panel to the dashboard (collapsed by default)

### New Files (additions only)
- `partial_offer_manager.py` — creates, tracks, requotes, and cancels partial coins
- `partial_fill_tracker.py` — detects partial fills via on-chain coin lineage
- `partial_coin_monitor.py` — background thread polling blockchain for partial coin state

---

## Technical Architecture

### The Feature Flag

In `.env`:
```
OFFER_MODE=standard   # "standard" (default, current behaviour) or "partial"
```

In `config.py`, four new settings are added alongside it:
```
PARTIAL_PRECISION=1000         # Scale factor for the offered asset
PARTIAL_PRICE_PRECISION=1000   # Exchange rate scale factor (encodes the price)
PARTIAL_SIDES=both             # "buy", "sell", or "both" — which sides use partial offers
PARTIAL_LEVELS=3               # How many price levels to maintain as partial coins
```

### The New `partial_offers` Database Table

```sql
CREATE TABLE partial_offers (
    id              TEXT PRIMARY KEY,   -- partial coin ID (changes with each fill)
    original_id     TEXT,               -- first coin ID in this lineage (stable identifier)
    side            TEXT,               -- "buy" or "sell"
    price_level     INTEGER,            -- which ladder rung (0 = innermost)
    offered_asset   TEXT,               -- "xch" or CAT asset_id
    requested_asset TEXT,               -- "xch" or CAT asset_id
    initial_amount  INTEGER,            -- original amount in mojos
    remaining_amount INTEGER,           -- current remaining amount in mojos
    price           TEXT,               -- encoded exchange rate (Decimal)
    precision       INTEGER,
    price_precision INTEGER,
    status          TEXT DEFAULT 'active', -- active, cancelled, filled, requoting
    created_at      INTEGER,
    last_fill_at    INTEGER,
    fill_count      INTEGER DEFAULT 0,
    total_filled    INTEGER DEFAULT 0
);
```

Existing `offers`, `fills`, `events`, `coins` tables are completely untouched.

### `partial_offer_manager.py` (new file)

Mirrors the structure of `offer_manager.py` but for partial coins. Key methods:

```
PartialOfferManager
├── create_partial_ladder(mid_price, side)   — creates partial coins for each price level
├── check_requotes(current_price)            — cancels + recreates stale partial coins
├── cancel_partial_offer(coin_id)            — maker spends the partial coin to cancel
├── get_active_partials(side)                — returns live partial coins from DB
└── _compute_price_precision(price)          — encodes price into PRECISION parameters
```

The `create_partial_offer()` call in here routes to `wallet_sage.py` which is a **stub** until Sage adds support. The stub logs a clear message and returns a graceful no-op so the rest of the bot runs normally.

### `partial_fill_tracker.py` (new file)

Detects fills by monitoring the blockchain for partial coin spends:

```
PartialFillTracker
├── poll_partial_coins()       — checks coinset/Spacescan for spent partial coins
├── detect_partial_fill(coin)  — confirms a spend, extracts fill amount
├── record_partial_fill(...)   — writes to fills table + updates partial_offers table
└── follow_lineage(coin_id)    — finds the new successor partial coin after a fill
```

The key difference from standard fill detection: instead of "offer ID disappeared from Sage", this watches for "partial coin ID spent on-chain → new coin created with same puzzle". The successor coin ID becomes the new tracked ID for that price level.

### `partial_coin_monitor.py` (new file)

A lightweight background thread (runs every 30s) that:
1. Fetches all active partial coin IDs from the DB
2. Queries Spacescan or coinset for their current state
3. If a coin shows as spent, calls `partial_fill_tracker.detect_partial_fill()`
4. Updates the DB with the successor coin ID

This is separate from the main bot loop so fills are detected even if the main loop is paused.

### `bot_loop.py` change

The main cycle gains a mode branch around steps 3–6:

```python
if cfg.OFFER_MODE == "partial":
    # Partial path
    partial_fills = self.partial_fill_tracker.detect_fills()
    self.partial_offer_manager.check_requotes(current_price)
    self.partial_offer_manager.create_partial_ladder(...)
else:
    # Standard path (existing code, completely unchanged)
    fills = self.fill_tracker.detect_fills(...)
    self.offer_manager.check_requotes(...)
    self.offer_manager.create_ladder(...)
```

---

## Build Phases

### Phase 1 — Foundation (no behaviour change, just scaffolding)
- [ ] Add `OFFER_MODE` and 4 partial settings to `config.py`
- [ ] Add `partial_offers` table migration to `database.py` (runs silently if table exists)
- [ ] Add `create_partial_offer()` and `cancel_partial_offer()` **stubs** to `wallet_sage.py`
  - Stubs log "Partial offers not yet supported by Sage" and return gracefully
- [ ] Add `get_partial_offers()` stub to `wallet_sage.py` (returns empty list)
- [ ] Add `add_partial_offer()`, `update_partial_offer()`, `get_active_partials()` to `database.py`
- [ ] Wire `OFFER_MODE` check into `bot_loop.py` (the if/else branch — both sides call stubs so nothing breaks)

**Result:** Bot runs exactly as today. No new behaviour. All the wiring exists.
**Risk:** Zero — stubs never execute in standard mode.

---

### Phase 2 — Partial Offer Manager
- [ ] Create `partial_offer_manager.py`
  - `create_partial_ladder()` — computes price levels, calls wallet stub, writes to DB
  - `check_requotes()` — detects price drift beyond threshold, cancels + recreates
  - `cancel_partial_offer()` — calls wallet stub, marks DB row as cancelled
  - `get_active_partials()` — reads from DB, returns live coin state
  - `_compute_price_precision()` — encodes a Decimal price into PRECISION / PRICE_PRECISION integer pair
- [ ] Wire into `bot_loop.py` partial branch

**Result:** In partial mode, the bot attempts to create/manage partial offers — but the wallet stubs no-op. DB rows are created and managed. All logic is exercised except the actual Sage RPC call.
**Testing:** Can be verified by enabling `OFFER_MODE=partial` and watching logs — DB entries appear, stubs fire, no actual coins created.

---

### Phase 3 — Partial Fill Tracker & Coin Monitor
- [ ] Create `partial_fill_tracker.py`
  - `poll_partial_coins()` — queries Spacescan for coin state
  - `detect_partial_fill()` — confirms fill, extracts amount, finds successor coin
  - `record_partial_fill()` — writes fill record to `fills` table
  - `follow_lineage()` — updates DB with new successor coin ID
- [ ] Create `partial_coin_monitor.py`
  - Background thread, 30s poll interval
  - Calls `partial_fill_tracker.poll_partial_coins()` on each tick
  - Handles errors gracefully (logs + continues)
- [ ] Start monitor thread in `bot_loop.py` when `OFFER_MODE=partial`

**Result:** If a partial coin were spent on-chain, the bot would detect it and record the fill. Still waiting on Sage for actual coin creation.

---

### Phase 4 — GUI Updates
- [ ] Add "Partial Offers" panel to `bot_gui.html`
  - Shows active partial coins (price level, remaining amount, fill count)
  - Shows recent partial fills (amount, timestamp)
  - Mode indicator in header ("Standard Mode" / "Partial Mode")
- [ ] Add `/api/partial_offers` endpoint to `api_server.py`
- [ ] Add `/api/partial_fills` endpoint to `api_server.py`

**Result:** Dashboard shows partial offer state. Panel is hidden/collapsed in standard mode.

---

### Phase 5 — Sage Activation (blocked on Sage + CHIP-0052)
When Sage adds `create_partial_offer` and `cancel_partial_offer` to its RPC:
- [ ] Replace stubs in `wallet_sage.py` with real RPC calls
- [ ] Test on Chia testnet with small amounts
- [ ] Verify fill detection end-to-end (create → partial fill → successor coin → detect)
- [ ] Verify cancellation (maker spends coin → DB marks cancelled)
- [ ] Enable `OFFER_MODE=partial` in production `.env`

**Result:** Full partial offer market-making live.

---

## Risks & Things to Watch

**Sage RPC shape is unknown** — We don't know yet what Sage's `create_partial_offer` endpoint will look like (what parameters, what it returns). The stubs are designed to be drop-in replacements when the spec is published. When Sage adds support, Phase 5 is straightforward.

**Coin lineage tracking complexity** — Following a chain of partial coin spends (original → fill 1 → fill 2 → ...) requires reliable on-chain querying. Spacescan is the current fallback; coinset is the primary. Both are already used in CATalyst. The 30s monitor thread gives a reasonable latency for detecting fills.

**CHIP-0052 spec may change** — Specifically the PRECISION/PRICE_PRECISION encoding. The `_compute_price_precision()` function should be kept isolated so it's a single-function update if the spec shifts before ratification.

**Dexie/Splash compatibility** — Partial offer coins do generate offer strings (for broadcasting). Whether Dexie's indexer handles partial offer strings the same as standard ones is unknown until Dexie adds support. For Phase 2–4, the Dexie posting can be disabled for partial mode offers.

---

## Decisions Already Made

- **Single codebase, feature flag** — not a fork. Cleaner to maintain.
- **One partial coin per price level** — matches how the standard ladder works conceptually; simpler than one big partial coin for the whole side.
- **Spacescan + coinset for fill detection** — same sources CATalyst already uses; no new external dependencies.
- **Stubs return gracefully** — the bot doesn't crash or degrade when stubs fire; it logs and continues in standard mode for that cycle.
- **DB migration is additive** — new table only, no changes to existing schema.

---

## Next Steps

Say **"let's build Phase 1"** to start with the foundation — config, database, stubs, and the bot_loop branch. That's the lowest-risk phase and gets all the wiring in place so every subsequent phase is just filling in the blanks.
