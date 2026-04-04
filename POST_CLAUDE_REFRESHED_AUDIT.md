# Post-Claude Refreshed Audit

## Purpose

This document captures the current review state after Claude's recent fixes. It is meant to be read alongside the original handoff documents, not as a replacement for them.

It focuses on:
- issues that are still confirmed in the current codebase
- improvements that have already landed
- updated implementation priority
- Sage-specific risks informed by the repository-local Sage research in `sage_docs/`

## What Improved

- [api_server.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/api_server.py) now binds to `127.0.0.1` by default.
- [api_server.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/api_server.py) `api_config_update()` now blocks dangerous endpoint URL keys such as `DEXIE_API_BASE`, `TIBET_API_BASE`, `COINSET_API_URL`, `SPLASH_SUBMIT_URL`, and `SPACESCAN_*`.
- [wallet_sage.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) now uses documented Sage endpoints for:
  - `get_pending_transactions()`
  - `get_spendable_coin_count()`
- [wallet_sage.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) now blocks signing for watch-only wallets.
- [wallet_sage.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) now rejects unsupported `validate_only=True` offer creation and rejects request-only offers that are not supported by the current fee handling.
- [wallet_sage.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py) no longer promotes `synced=None` to synced/ready.

## Confirmed Current Findings

### High Severity

1. Unauthenticated local control API is still exposed
- File: [api_server.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/api_server.py)
- Confirmed routes include:
  - `/api/events`
  - `/api/bot/start`
  - `/api/bot/stop`
  - `/api/shutdown`
  - `/api/offers/cancel_all`
  - `/api/coin-prep/trigger`
  - `/api/chia/daemon/start`
  - `/api/chia/daemon/stop`
  - `/api/db/backup`
  - `/api/logs/download`
- Current state:
  - localhost-only binding is in place
  - no visible auth/token/permission layer is present
- Why it matters:
  - any local process can still drive the bot and node control plane
  - this is still a meaningful security issue even after removing LAN exposure

2. `api_config_live()` can still bypass the config hardening
- File: [api_server.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/api_server.py)
- Function: `api_config_live()`
- Current state:
  - only a small set of keys is blocked
  - it does not block dangerous endpoint URL keys that `api_config_update()` now blocks
- Why it matters:
  - this leaves a remaining config mutation path for outbound service endpoints
  - the hardening is incomplete unless both config write paths enforce the same rules

3. `AppBridge` still contains broken runtime contracts
- File: [app_bridge.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/app_bridge.py)
- Confirmed broken targets still include:
  - `database.get_recent_fills`
  - `database.get_pnl_summary`
  - `bot.get_dashboard_data()`
  - `bot.risk_manager.get_inventory_summary()`
  - `bot.risk_manager.get_spread_info()`
  - `bot.coin_manager.get_coin_status()`
  - `bot.coin_manager.trigger_topup()`
  - `bot.market_intel.get_summary()`
- Why it matters:
  - the desktop bridge remains unsafe to call
  - this is still a direct runtime failure surface

4. `/api/status` still performs live work and logging while being polled
- File: [api_server.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/api_server.py)
- Function: `api_status()`
- Current state:
  - still performs live Tibet/Dexie price lookups in the request path
  - still calls `log_event()` during status generation
- Runtime evidence:
  - repeated `[STATUS] TibetSwap fallback price: ...` lines during normal operation
- Why it matters:
  - status polling is still not read-only
  - this increases load and creates DB/event noise

5. Duplicate public functions still exist outside the Sage adapter
- Files:
  - [database.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/database.py)
  - [wallet_chia.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_chia.py)
- Confirmed duplicates:
  - `database.get_all_coins_state()`
  - `wallet_chia.count_suitable_coins()`
- Why it matters:
  - later definitions silently override earlier ones
  - behavior remains ambiguous and fragile

6. Polling and DB access patterns are still too expensive
- Files:
  - [api_server.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/api_server.py)
  - [bot_loop.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/bot_loop.py)
  - [coin_manager.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/coin_manager.py)
- Runtime evidence:
  - repeated `price_history` reads around 8-9 seconds
  - repeated `offers WHERE status='open' ...` reads around 8 seconds
  - repeated coin-watcher reads around 20 seconds
  - `update_coin_counts` around 12.6 seconds
  - `_startup_sync` around 29 seconds
  - `_create_offers_if_needed` around 297 seconds
- Why it matters:
  - this now affects correctness and market freshness, not just performance polish

7. Sage coin-state handling is still degrading under load
- Files:
  - [wallet_sage.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
  - [coin_manager.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/coin_manager.py)
- Runtime evidence:
  - repeated log lines such as:
    - `"[Sage workaround] N XCH coins were hidden by selectable bug ..."`
    - `"[Sage workaround] N CAT coins were hidden by selectable bug ..."`
  - hidden counts grow as offer volume increases
- Why it matters:
  - the current owned/selectable workaround is still doing critical work under real load
  - the integration is not yet stable around Sage coin visibility and lock attribution

### Medium Severity

8. Desktop notification wiring is still broken
- Files:
  - [desktop_app.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/desktop_app.py)
  - [api_server.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/api_server.py)
- Current state:
  - `desktop_app._wire_notifications()` still calls `bus.subscribe("fill", on_fill)`
  - `EventBus.subscribe()` still returns a queue and does not accept callbacks
  - wiring errors are still swallowed
- Why it matters:
  - notifications are still not trustworthy in desktop mode

9. Sage lifecycle handling is still short of the documented model
- Files:
  - [wallet_sage.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
  - [chia_node.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py)
- Current state:
  - `get_version` reachability check was added
  - startup still effectively treats RPC reachability plus `resync + login` as the session lifecycle
- Why it matters:
  - repository-local Sage research still identifies explicit initialization handling as a required lifecycle check
  - this should be resolved or explicitly justified during implementation

10. Sage send-path validation is still only partial
- File: [wallet_sage.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
- Current state:
  - `send_transaction()` has basic `xch1` / `txch1` prefix validation
  - multi-send paths do not clearly apply equivalent per-destination validation
  - active-network validation is still not clearly enforced caller-side
- Why it matters:
  - the Sage review rules require caller-side network/address validation
  - partial validation is better than none, but still incomplete

### Low Severity

11. `api_server.py` still documents itself inaccurately
- File: [api_server.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/api_server.py)
- Current state:
  - header comments still describe a much smaller, thinner module than the file actually is
- Why it matters:
  - this is misleading for future maintainers

12. Duplicate agent-instruction files exist
- Files:
  - [AGENTS.md](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/AGENTS.md)
  - [AGENTS.md.txt](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/AGENTS.md.txt)
- Why it matters:
  - this is minor, but it creates ambiguity about which file is authoritative

## Sage-Specific Current Assessment

The Sage integration is in a better state than before, but it is not yet complete.

### Confirmed Sage Improvements
- documented pending transaction endpoint is now used
- documented spendable coin count endpoint is now used
- watch-only wallets are now blocked from signing flows
- `create_offer()` no longer silently accepts unsupported `validate_only=True`
- request-only offers are no longer silently accepted with the current fee assumptions
- `synced=None` is no longer treated as synced

### Confirmed Sage Gaps Still Relevant
- lifecycle still needs a documented `initialize` review, or an explicit implementation note explaining why it is intentionally not required in this deployment
- send-path address/network validation is still incomplete
- coin visibility and lock attribution remain unstable under real offer load

### Sage Rule Set To Apply During Further Fixes
- use the rules in [sage_docs/SAGE_V4_REVIEW_RULES.md](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_V4_REVIEW_RULES.md)
- keep [sage_docs/SAGE_MASTER_HANDOFF_FOR_CLAUDE.md](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_MASTER_HANDOFF_FOR_CLAUDE.md) as the deep Sage reference

## Updated Priority Order

1. Add local auth/authorization to all operational API routes
2. Apply the same config hardening rules to `api_config_live()`
3. Remove or repair the broken `AppBridge` surface
4. Make `/api/status` and other polling/read paths read-only and cheap
5. Remove duplicate public definitions in `database.py` and `wallet_chia.py`
6. Investigate and stabilize Sage coin-state reconciliation under load
7. Fix desktop notification wiring
8. Tighten Sage lifecycle and send-path validation to match the documented rules
9. Clean up misleading documentation and stray duplicate instruction files

## Recommended Next Implementation Batches

### Batch A: Local API hardening
- Files:
  - [api_server.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/api_server.py)
  - [config.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/config.py)
- Scope:
  - add auth/authorization
  - align `api_config_live()` with `api_config_update()`
- Why first:
  - highest risk reduction for smallest code surface

### Batch B: Broken contract cleanup
- Files:
  - [app_bridge.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/app_bridge.py)
  - [desktop_app.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/desktop_app.py)
  - [database.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/database.py)
  - [wallet_chia.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_chia.py)
- Scope:
  - remove broken bridge methods or remap them to real APIs
  - fix notification wiring
  - remove duplicate public function definitions

### Batch C: Polling and query cost reduction
- Files:
  - [api_server.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/api_server.py)
  - [bot_loop.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/bot_loop.py)
  - [coin_manager.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/coin_manager.py)
  - [database.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/database.py)
- Scope:
  - make read endpoints cheaper
  - reduce repeated heavy queries
  - add indexes or caching where clearly justified

### Batch D: Sage runtime stabilization
- Files:
  - [wallet_sage.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/wallet_sage.py)
  - [coin_manager.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/coin_manager.py)
  - [chia_node.py](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/chia_node.py)
- Scope:
  - address lifecycle/documented-init question
  - tighten send-path validation
  - reduce dependence on the selectable workaround under real load

## Tests To Prioritize Now

1. API auth tests
- unauthenticated local POSTs to control routes must fail
- authenticated requests must succeed

2. Config hardening tests
- both `api_config_update()` and `api_config_live()` must reject endpoint/base URL mutations

3. Bridge parity tests
- every exposed `AppBridge` method must map to a real callable or be removed

4. Status endpoint regression tests
- `/api/status` must not write events/log rows during polling
- `/api/status` must not perform live external fetches in the request path

5. Duplicate-definition regression tests
- `database.get_all_coins_state`
- `wallet_chia.count_suitable_coins`

6. Sage runtime tests
- watch-only wallets cannot sign
- send-path validation rejects wrong-network destinations
- coin reconciliation remains stable while offers are created

## How To Use This Document

- Use this as the current-state audit after Claude's first round of fixes.
- Keep the original master handoff for broader context:
  - [CLAUDE_COWORK_MASTER_HANDOFF.md](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/CLAUDE_COWORK_MASTER_HANDOFF.md)
- Keep the Sage master handoff for Sage-specific depth:
  - [sage_docs/SAGE_MASTER_HANDOFF_FOR_CLAUDE.md](C:/Users/t_you/Pictures/01%20Monkeyzoo/chia_liquidity_bot_v2/v4/sage_docs/SAGE_MASTER_HANDOFF_FOR_CLAUDE.md)

The safest next move is to hand Claude one batch at a time, starting with Batch A.
