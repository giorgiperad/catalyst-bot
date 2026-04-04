# Operator Runbook

Quick reference for operating the Chia CAT Market Maker bot.

---

## 1. First Setup

### Prerequisites
- Python 3.10+
- Sage wallet installed and running (port 9257)
- `.env` file configured with at minimum:
  - `CAT_ASSET_ID` — the token you're market-making
  - `CAT_TICKER_ID` — for Dexie/Tibet lookups
  - `WALLET_TYPE=sage`

### First Start
```bash
pip install pywebview pystray plyer Pillow --break-system-packages
python desktop_app.py
```

### Verify Readiness
The bot runs a **preflight check** before starting. View the report at:
- GUI: Dashboard status bar shows preflight summary
- API: `GET /api/doctor`
- API: `GET /api/doctor?force=true` (bypass 30s cache)

A preflight report lists each check as `pass`, `warn`, `fail`, or `skip`.
The bot will not start if any check is `fail`.

---

## 2. Normal Operations

### Cycle Anatomy
Each bot cycle (default 90s) runs these steps in order:
1. Fetch prices (TibetSwap + Dexie)
2. Circuit breaker checks
3. Wallet sync (fetch live offers)
4. Fill detection (before/after snapshot comparison)
5. Round-trip PnL matching
6. Inventory snapshot
7. Requote stale offers
8. Create new offers (fill gaps in ladder)
9. Post to Dexie
10. Coin management
11. Housekeeping

### What to Watch
- **Dashboard**: Open offers, mid price, fill count, uptime
- **Runtime Monitor**: Wallet sync, Dexie visibility, coin headroom
- **Advisor panel**: Active conditions and automated actions
- **API health**: `GET /api/health` for live wallet status

---

## 3. Doctor / Preflight

### Interpreting the Report

| Check | Category | What it Means |
|-------|----------|---------------|
| `database_health` | database | DB readable, writable, required tables exist |
| `config_validation` | config | No dangerous config contradictions |
| `cat_identity` | config | CAT_ASSET_ID is set and valid |
| `wallet_reachable` | wallet | Sage/Chia RPC responds |
| `wallet_synced` | wallet | Wallet reports synced (documented signals only) |
| `wallet_signing` | wallet | Wallet has secrets (not watch-only) |
| `cat_wallet_mapping` | wallet | Configured CAT found in wallet |
| `dexie_reachable` | exchange | Dexie API responds |
| `tibet_reachable` | exchange | TibetSwap API responds |
| `splash_reachable` | network | Splash node responds (if enabled) |
| `spacescan_setup` | network | API key present if needed |

### Common Blockers
- **wallet_signing=fail**: You're using a watch-only wallet. Switch to a wallet with secrets.
- **wallet_synced=fail**: Wallet is still syncing. Wait for sync to complete.
- **config_validation=fail**: Check `GET /api/config/validate` for details.
- **cat_identity=fail**: Set `CAT_ASSET_ID` in your `.env` file.

---

## 4. Offer Lifecycle

### State Diagram
```
                                  +---> MEMPOOL_OBSERVED --+
                                  |                         |
  OPEN ---> REFRESH_DUE ---> CANCELLED (via refresh)       |
    |            |                                          v
    |            +---> EXPIRED                           FILLED
    |                                                      |
    +---> CANCEL_REQUESTED ---> CANCELLED                  +---> PHANTOM_REJECTED
    |            |                   |                            (self-spend)
    |            +---> OPEN (cancel failed, revert)
    |
    +---> FILLED (disappeared, not our cancel)
    |
    +---> EXPIRED (time expired)
```

### State Meanings

| State | Terminal? | Meaning |
|-------|-----------|---------|
| `open` | No | Live on wallet, tradeable |
| `refresh_due` | No | Approaching expiry, needs requote |
| `cancel_requested` | No | Cancel RPC sent, awaiting confirmation |
| `mempool_observed` | No | Potential take seen in mempool |
| `cancelled` | Yes | Confirmed cancelled |
| `filled` | Yes | Fill detected and verified |
| `expired` | Yes | Time expired |
| `phantom_rejected` | Yes | Self-spend / false fill rejected |

### Backward Compatibility
The legacy `status` column (open/filled/cancelled/expired) is always kept in sync.
The extended `lifecycle_state` column provides finer detail.

---

## 5. Incident Triage

### Wallet Unreachable
- Check Sage is running: `curl -k https://127.0.0.1:9257/`
- Check cert paths in `.env`
- Restart Sage if needed

### No Price Available
- Check TibetSwap: `curl https://api.v2.tibetswap.io/tokens`
- Check Dexie: `curl https://api.dexie.space/v1/offers`
- Both down? Bot skips cycles until price returns.

### Mass Disappearance Guard
- If many offers disappear simultaneously, the bot pauses fill detection.
- This prevents false fills from wallet RPC blips.
- Normal operation resumes after 3 consecutive clean cycles.

### Circuit Breaker Tripped
- All offers cancelled as a safety measure.
- Check risk manager conditions in runtime monitor.
- Bot must be manually restarted after investigation.

### Coin Shortage
- Check `GET /api/coin-prep/status` for coin inventory.
- Enable `ENABLE_COIN_PREP=True` for automatic top-ups.
- Manual split: use Sage wallet UI to split coins.

### Stuck Offers
- Check `GET /api/status` for open offers with old `created_at`.
- Cancel All from GUI if needed.
- Check `lifecycle_state` — `cancel_requested` means cancel is pending.

---

## 6. Config Reference

### Dangerous Settings (validated by config_validator)
| Setting | Danger | Safe Default |
|---------|--------|-------------|
| `MIN_TRADE_XCH > MAX_TRADE_XCH` | Inverted range | 0.005 / 0.050 |
| `SPREAD_BPS <= 0` | Zero/negative spread | 800 |
| `OFFER_EXPIRY_SECS < 300` | Offers expire too fast | 86400 |
| `ENABLE_BUY=False + ENABLE_SELL=False` | Nothing to do | Both True |
| `CAT_ASSET_ID empty` | No token configured | Must be set |

### Risky but Allowed (warnings)
| Setting | Risk | Default |
|---------|------|---------|
| `LOOP_SECONDS < 30` | Wallet contention | 90 |
| `REQUOTE_COOLDOWN_SECS < 10` | Excessive requoting | 60 |
| `MAX_ACTIVE_* > 50 each` | Wallet strain | 25 each |
| `LADDER_CREATE_PARALLELISM > 20` | RPC overwhelm | 5 |

---

## 7. Recovery

### After a Crash
1. Start the bot — it runs startup sync automatically.
2. Startup sync recovers unknown offers from wallet.
3. Stale DB offers are marked cancelled.
4. Fill detection baseline is re-established.
5. Reservation leases from previous runtime are expired.

### After Config Changes
1. Hot-reload: most settings apply on next cycle.
2. Some settings (wallet URLs, CAT_ASSET_ID) require restart.
3. Run `GET /api/config/validate` to check for issues.

### Recovery Mode
- Bot enters recovery mode after 4+ cycles with persistent issues.
- During recovery: probing, requotes, and top-ups are paused.
- Exits after 2 clean cycles.
- Visible in runtime monitor and advisor panel.

---

## 8. Event Categories

Events are categorized for filtering and routing:

| Category | Examples |
|----------|---------|
| `lifecycle` | bot_starting, startup_sync_done, cycle_complete |
| `offer` | offer_created, fills_detected, requoting, batched_cancel |
| `pricing` | price_found, no_price, tibet_swap_detected |
| `wallet` | wallet_sync, chia_unhealthy, health_monitor |
| `exchange` | dexie_flush_result, splash_repost_done |
| `risk` | circuit_breaker, recovery_mode_enter, mass_disappearance_guard |
| `system` | db_migration, config_error, trading_pace |
| `coin` | coin_prep_started, topup_trigger, coin_reconciliation |

Filter events by category via the events API.

---

## 9. Capacity Reservations

The reservation system prevents over-allocation during parallel offer creation.

### How it Works
- Before creating an offer, the bot acquires a capacity reservation.
- Reservations have a TTL (default 120s) and auto-expire.
- All reservations from previous runtimes are cleared on startup.
- View active reservations: `GET /api/reservations`

### Troubleshooting
- If offers fail to create with "insufficient capacity", check reservations.
- Stale reservations are cleaned at every cycle start.
- Manual check: `GET /api/reservations` shows active leases.
