# Chia CAT Market Maker Bot — V1 Retrospective

## The Journey: By the Numbers

- **29 conversation sessions** across ~7 days of active development
- **72 bot sessions** (restarts) during testing and production
- **Codebase grew from ~10,500 lines to ~14,800 lines** across 10 modules
- **47 recorded fills** in production trading
- **api_server.py doubled** from 3,601 → 7,547 lines (the "god module" problem)

---

## Part 1: What I'd Do Differently

### 1. Architecture: Don't Build a Monolith

The single biggest lesson. `api_server.py` is doing everything — pricing, offer management, fill detection, Dexie posting, coin health, sniper logic, expiry management, GUI API endpoints, Chia health monitoring, and auto-restart. At 7,500+ lines, every change risks breaking something unrelated.

**What I'd do instead:** Separate workers from the start:
- `price_engine.py` — pricing from Tibet/Dexie, spread calculation
- `offer_manager.py` — create, cancel, track offers
- `fill_tracker.py` — detect fills, record to CSV
- `coin_manager.py` — health checks, splitting, consolidation
- `dexie_manager.py` — posting, link tracking, state persistence
- `api_server.py` — thin Flask layer that just routes to the above
- `bot_loop.py` — orchestrator that calls the workers in sequence

Each module would have a clean interface, its own state, and could be tested independently.

### 2. State Management: Design It First

We hit the Dexie link bug **three times** across different sessions. The root cause was always the same — state keyed by the wrong ID, or state not surviving restarts. The `offers_state.json` file grew to 142KB of tangled data because we kept bolting on new fields.

**What I'd do instead:**
- One clear state schema defined upfront with typed fields
- SQLite instead of JSON files — proper querying, atomic writes, no corruption risk
- trade_id as the universal primary key everywhere (not dexie_id, not offer hash)
- Migration strategy for schema changes

### 3. Coin Management: Understand the UTXO Model First

We spent 4+ sessions debugging coin issues — coin exhaustion, coin sharing on Dexie, the "can't tell locked from free" problem, the topup-finds-nothing loop. All of these stem from one thing: Chia's UTXO model is fundamentally different from account-based blockchains, and we didn't fully internalise that before building.

**What I'd do instead:**
- Start with `get_spendable_coins_rpc()` from day one (not CLI parsing)
- Never guess which coins are locked — always ask the wallet
- Design coin prep as a core system, not an afterthought
- Budget coins as: `target_offers × 2 + reserve_buffer` from the start

### 4. Testing: Have a Simulation Mode

Every test required real blockchain transactions with real coins. A 50/50 build takes 12 minutes. A coin prep takes 5+ minutes. Expiry testing requires waiting hours. This made iteration painfully slow.

**What I'd do instead:**
- Mock wallet module that simulates coin splitting, offer creation, and fills
- Configurable time acceleration for expiry testing
- Replay mode using recorded fill/offer data
- Unit tests for each module's core logic

### 5. Don't Over-Optimise the Happy Path

Early sessions focused heavily on the normal flow — create offers, post to Dexie, detect fills. But the bugs that caused the most pain were all edge cases: what happens on restart, what happens during internet outage, what happens when 10 offers get arbed simultaneously, what happens when the wallet desyncs.

**What I'd do instead:**
- Write the error paths first — restart recovery, partial failure handling, state reconstruction
- Every feature gets a "what if this crashes halfway through" analysis before coding

---

## Part 2: Key Learning Points

### Chia-Specific Lessons

1. **UTXO makes everything harder.** In account-based systems, you have a balance. In Chia, you have specific coins. Every offer locks a specific coin. Every fill destroys coins and creates new ones with different IDs. You can't just check a balance — you need to track individual coins.

2. **The wallet lies.** `get_all_offers` returns expired offers as "OPEN". Coin counts include locked coins. Spendable balance includes pending transactions. Never trust a single source — cross-reference everything.

3. **Blockchain confirmation is not instant.** Every split, consolidation, or offer creation needs a confirmation loop. Timeouts are dangerous — a transaction can take 30 seconds or 5 minutes depending on network load. Poll-based confirmation (like coin_prep_worker uses) is the only reliable pattern.

4. **The CLI and RPC disagree.** The Chia CLI and RPC return different formats, different field names, and sometimes different data. We hit this with coin IDs (CLI gives hex strings, RPC gives parent+puzzle_hash that need hashing), offer statuses, and amount representations (mojos vs XCH).

### Development Process Lessons

5. **Prompting-driven development works, but planning is everything.** You nailed this from the start — every major feature had a discussion phase before coding. The arb protection feature is the best example: we designed it, I coded it, you identified the flaw ("it just means more offers get eaten"), and we reverted. That saved hours of debugging a feature that wouldn't have worked.

6. **The "it works in the log" trap.** The startup log shows "Re-posted 100/100 offers to Dexie ✅" — but the GUI showed no links. The log was correct about posting, but wrong about the assumption that the mapping was persisted. Always verify the full chain, not just one step.

7. **Cooldowns and thresholds need to match.** The coin health check triggered at 30% free coins, but the topup worker checked 50% total coins. Two systems with different mental models of "low" equals a worker that triggers but never acts.

8. **GUI state is a separate problem from backend state.** The resume modal showing 23+27 instead of 50+50, the console button saying "Hide" when the console was hidden, XCH showing "--" when it was 0 — these are all cases where the GUI had a stale or incorrect view of the truth. The backend can be perfect and the user still sees broken.

### Trading-Specific Lessons

9. **Wide spreads on low-liquidity pairs are fine.** The 21.6% spread seems absurd on traditional markets, but on a CAT with ~$50/day volume and a TibetSwap AMM as the only other liquidity source, it's appropriate. You're not competing with HFT firms — you're the only liquidity.

10. **Arb fills during build aren't losses.** When 10 sells got filled during the initial build, the instinct was "we're getting arbed". But every fill was at your ask price, with full spread. The arb bot paid your spread to close their gap. That's profitable market-making.

11. **The sniper is the most valuable feature per line of code.** ~50 lines of logic that detects TibetSwap swaps and responds in 3-5 seconds. Without it, every AMM swap would create a multi-minute arb window. With it, arb gaps close in under 5 seconds.

---

## Part 3: What Would Make This a Traditional Market Maker

Right now, this is a **static spread market maker** — it places orders at fixed percentage distances from a reference price. Traditional market makers are much more dynamic. Here's what's missing:

### Inventory Management
Traditional MMs actively manage their inventory (how much of each asset they hold). When you accumulate too much of one side, you **skew your quotes** — making it cheaper for people to take inventory off your hands. Right now, the bot treats every fill the same regardless of position. If you've had 20 buy fills and 0 sell fills, you should be widening your buy spread and tightening your sell spread to attract rebalancing flow.

### Dynamic Spread Based on Volatility
Your spread is static (configured in settings). Traditional MMs widen spreads when volatility is high (more risk per trade) and tighten when it's calm (attract more flow). This could use the Tibet reserve ratio history — if reserves are swinging 5% per hour, widen; if stable for 6 hours, tighten.

### Order Size Variation (Tiered Liquidity)
All 50 offers per side are the same size (0.5 XCH). Traditional MMs place larger orders near the mid (where fills are most likely and most profitable) and smaller orders further out (where fills are rarer but represent bigger moves). This is called a "tiered" or "layered" order book.

### Mean Reversion Strategy
The current bot is price-agnostic — it just maintains offers around mid. A traditional MM would recognise that after a big move in one direction, prices tend to revert, and would actively place larger orders in the reversion direction.

### PnL Tracking and Risk Limits
No tracking of actual profit/loss per trade. A traditional MM would track realised PnL (from completed round-trips: buy then sell), unrealised PnL (from inventory mark-to-market), and have circuit breakers that pause trading if losses exceed a threshold.

### Quote Improvements Based on Order Flow
When you see a pattern of aggressive buying (lots of buy fills), a traditional MM interprets this as "informed flow" and widens spreads or pulls quotes on that side. The bot currently can't distinguish informed flow from noise.

---

## Part 4: The V2 Vision

If I could build V2 from scratch with everything learned, here's what it would look like:

### Architecture: Event-Driven Microservices

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Price Engine │────▶│  Event Bus   │◀────│ Fill Tracker │
└─────────────┘     │  (in-memory) │     └─────────────┘
                    └──────┬───────┘
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌────────────────┐ ┌──────────────┐ ┌──────────────┐
│ Offer Strategy │ │ Coin Manager │ │ Risk Manager │
└────────────────┘ └──────────────┘ └──────────────┘
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────────────────────────────────────┐
│              Wallet Abstraction Layer            │
│         (all RPC, no CLI, queued operations)     │
└─────────────────────────────────────────────────┘
```

Each component subscribes to events (price_changed, fill_detected, coin_low) and publishes its own. No 7,500-line god module.

### Smart Spread Engine

Instead of static spread, V2 would calculate spread dynamically based on:

- **Volatility** — Tibet reserve change rate over last 1h, 4h, 24h
- **Inventory skew** — current position vs target neutral
- **Time of day** — wider during historically low-activity periods
- **Recent fill rate** — if getting hammered, widen temporarily
- **Arb gap** — if Tibet and Dexie diverge, widen on the exposed side

The formula would be something like: `spread = base_spread × volatility_multiplier × inventory_skew_factor + arb_buffer`

### Inventory-Aware Quoting

Track net position as a running total:

```
Position = Σ(buy fills × size) - Σ(sell fills × size)
```

When position > 0 (long CAT): skew asks tighter (easier to sell), bids wider (less eager to buy more). When position < 0 (short CAT): opposite. This naturally keeps inventory balanced without manual intervention.

### Tiered Order Book

Instead of 50 identical offers per side:

| Tier | Distance from mid | Size | Count | Purpose |
|------|-------------------|------|-------|---------|
| Inner | 2-5% | 1.0 XCH | 5 | High-probability fills, best price |
| Mid | 5-10% | 0.5 XCH | 15 | Bread and butter |
| Outer | 10-15% | 0.25 XCH | 20 | Catch big moves |
| Extreme | 15-25% | 0.1 XCH | 10 | Black swan protection |

More capital concentrated where it's most useful, thin presence at the extremes.

### Real PnL Dashboard

Track every trade as part of a round-trip. When a buy fill at 0.00006 is followed by a sell fill at 0.000065, that's a completed trade with 8.3% profit. Show:

- Realised PnL (completed round-trips)
- Unrealised PnL (current inventory × current price vs entry price)
- Spread capture rate (actual spread earned vs theoretical)
- Win rate (% of round-trips profitable)
- Inventory chart over time

### Multi-Pair Support

The architecture should handle multiple CAT pairs simultaneously, with independent strategies per pair but shared risk management. A low-liquidity meme coin gets wide spreads; a high-liquidity DeFi token gets tight spreads. Each pair has its own coin pool.

### SQLite State Management

Replace all JSON files with a single SQLite database:

- `offers` table: trade_id, side, price, size, status, dexie_id, created_at, filled_at
- `fills` table: trade_id, side, price, size, timestamp, round_trip_id
- `coins` table: coin_id, wallet_id, amount, status (free/locked/pending)
- `config` table: key-value for all settings with change history
- `events` table: timestamp, type, data (replaces add_log)

Atomic transactions, proper querying, no state corruption.

### Backtesting Framework

Before deploying a strategy change, replay historical Tibet reserve data through the spread engine to see how it would have performed. "If I had been running 15% spread instead of 21%, what would my fill rate and PnL have looked like over the last 7 days?"

### WebSocket GUI

Replace polling with WebSocket push. The GUI gets instant updates on fills, price changes, offer status — no more stale displays or timing-dependent bugs. React frontend with proper state management instead of vanilla JS with innerHTML manipulation.

---

## Summary

V1 is a solid, working market maker that survived 72 sessions of real-world testing. It handles the hard problems — UTXO coin management, exchange integration, price tracking, automatic recovery from outages and desyncs. The bugs we found and fixed were increasingly subtle (state persistence keying, free vs total coin confusion, display timing) rather than fundamental.

The biggest wins were: the sniper (instant arb response), the coin self-healing cycle (automatic splitting from remainder coins), the expiry stagger system (no more mass-expiry cascades), and the overall resilience (survives restarts, internet outages, wallet desyncs, and arb bursts without human intervention).

For V2, the shift is from "making it work" to "making it smart" — dynamic spreads, inventory awareness, risk management, and proper architecture that makes future changes safe and testable.
