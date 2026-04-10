# Chia Market Maker — V4 Desktop Application

## Project Overview
Automated market maker for Chia blockchain CAT tokens on the Dexie exchange. V4 is the desktop application rebuild — wrapping the complete V3 trading engine in a native desktop window with system tray, native notifications, and cross-platform builds.

**Status:** Phase 1 complete (desktop shell). Flask runs internally, PyWebView wraps it in a native window.

## CRITICAL: Read These First
- **DESKTOP_MIGRATION_PLAN.md** — Full migration roadmap (6 phases + design overhaul)
- **DESIGN_SPEC.md** — Complete visual design system (tokens, components, layout, wireframes)
- **CHIA_DEV_GUIDE.md** — Chia blockchain reference (coin model, RPC API, offer system)
- **CODEBASE_AUDIT.md** — Complete inventory of all modules (55K+ lines across 30+ files)

## Important Context
The developer (Tim) is not a coder — all development is done through prompting. Always explain what you're doing and why. When making changes, prefer small, testable increments. Always verify syntax after edits (`python -c "import ast; ast.parse(open('file.py').read())"`)

## Working Style (PERMANENT — apply across all sessions)

**Research the codebase before editing. Never change code you haven't read.**

**Default to honest pushback, not agreement.**
- Read the actual code before making claims about behaviour. Never describe what code "probably does" — check.
- If Tim's stated goal conflicts with what the bot actually does, flag it clearly before implementing anything.
- If a proposed change has a real downside, say so. Don't soften it. Tim explicitly prefers direct, accurate feedback over comfortable agreement.
- If something is working well, say that too. Pushback is not contrarianism — it's accuracy.

**When reviewing any change Tim proposes:**
1. Ask: does this conflict with any existing system? Name the conflict specifically.
2. Ask: what is the failure mode? Describe it concretely.
3. Ask: is there a simpler solution? Propose it if yes.
4. Only then implement.

**Decision log — record key architectural decisions here** so future sessions don't re-litigate them:

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-01 | Bot is a **symmetric market maker**, not a price support tool | Price support and arb are separate future projects. Market maker profits from spread capture, not direction. Optimise for that. |
| 2026-04-01 | ~~Probe-on-fill = positive signal~~ **REVERSED 2026-04-05** | ~~Treat fill as confirmation~~ → A filled probe means the safe edge hasn't been found yet. Always widen and retry. Ladder only deploys after probes **survive** on the book. Fill = overshot, not confirmation. |
| 2026-04-01 | ~~Topup threshold = `MAX_BUY_OFFERS + MAX_SELL_OFFERS` spare coins~~ **SUPERSEDED 2026-04-08** | Actual rule in `coin_manager.needs_topup` is per-tier: `TIER_TRIGGER_PCT_*` percentages of `prep_target × pace_scale`, scaled by trading pace (busy=1.4×, slow=0.7×). Fires earlier than the simple sum, which is more defensive. Legacy non-tiered branch still uses the multiplier rule. Tune via `TIER_TRIGGER_PCT_INNER/MID/OUTER/EXTREME` in `.env`. |
| 2026-04-01 | Topup backoff = exponential starting at 5 min, max 60 min | 2-hour fixed backoff is too long. Ladder degrades during the wait. Exponential gives fast retry on transient failures. |
| 2026-04-01 | Circuit breaker must NOT halt the correcting side | If CB trips because position is over-long, sell offers must continue. Halting everything when you should be selling is wrong. |
| 2026-04-01 | ~~Smart Settings must write both new + legacy MAX_MID/MIN_MID keys~~ **REVERSED 2026-04-08** | Legacy keys are silent fallbacks for `HARD_MIN/MAX_PRICE_XCH`. Writing both creates two sources of truth and the legacy values can override the new ones unexpectedly. Smart Settings now **clears** the legacy keys (sets to "") so the new HARD rails are the only source. `MAX_MID_MOVE_BPS` was never consumed by trading code and was removed from config + GUI. |
| 2026-04-08 | Price-rail breach (`HARD_MAX/MIN`, dynamic band, step) → trip price CB → cancel ALL offers → skip cycle | Previous behaviour silently returned from the cycle leaving stale offers exposed at the wrong mid. Now `_apply_safety_guards` records the breach direction and `bot_loop` routes the rail breach through `risk_manager.trip_price_rail_breach()` so the existing CB safeguard cancels the book. |
| 2026-04-08 | `_handle_requoting` must check `risk_manager.should_enable_side` and stale-wallet streak | Was the second road to creating offers and bypassed the position-CB blocked-side check, defeating the partial-halt CB. Now mirrors the gates already used by `_create_offers_if_needed`. |
| 2026-04-08 | `MAX_STEP_CHANGE_FRACTION` default = 0.10 (was 0); `REQUOTE_BPS` default = 30 (was 0); `DYNAMIC_SPREAD_ENABLED` default = True (was False) | The off-by-default settings made the safety/efficiency machinery inert in fresh installs. Step guard at 10% blocks corrupted Tibet responses inside the ±50% dynamic band; 30 bps requote hysteresis prevents every-cycle churn; dynamic spread enables the volatility/depth scaling the dashboard already advertises. |
| 2026-04-08 | Silent fill-loss events get a per-hour rate alert | `mass_disappearance_guard`, `offer_closed_unverified`, and `fill_unverified` each log a single warning per occurrence — easy to miss when the bot is dropping real fills from PnL. `FillTracker._record_silent_loss_event` now keeps a per-event 1-hour bucket and emits an `error`-severity `silent_loss_rate_exceeded` event (with 10-min anti-spam cooldown) when the per-hour count exceeds 5. |
| 2026-04-08 | Mass-disappearance guard boundary = `>= 0.5` (was `> 0.5`) | Exactly 50% of the visible book vanishing in one cycle is symmetric with 51% — both deserve the 3-strike guard. Previously a 4-of-8 cycle slipped through unprotected. Still gated on `disappeared > 1` so single fills in tiny books are unaffected. |
| 2026-04-08 | `fills.trade_id` has a UNIQUE index (`uniq_fills_trade_id`) | Defense-in-depth backstop against double-counting if `record_fill` ever races between SELECT pre-check and INSERT. Migration is idempotent and skips gracefully if pre-existing duplicates would block the index. `record_fill` now catches `IntegrityError` specifically and returns the existing `fill_id` so a race becomes an idempotent no-op. |

## How to Run

### Desktop Mode (default)
```bash
pip install pywebview pystray plyer Pillow --break-system-packages
python desktop_app.py
```
This opens a native desktop window with the dashboard, plus a system tray icon.

### Flask-Only Mode (fallback / debugging)
```bash
python desktop_app.py --flask
# Or the old way:
python api_server.py
```
Opens in your browser at http://localhost:5000/

### Dev Mode (desktop window + browser access)
```bash
python desktop_app.py --dev
```

## Architecture

### V4 Desktop Layer (NEW)
```
desktop_app.py          → Main entry point (replaces running api_server.py directly)
                           Starts Flask in background thread
                           Creates PyWebView window pointing at Flask
                           Manages system tray + notifications

app_bridge.py           → JS ↔ Python bridge (Phase 2: replaces HTTP calls)
                           Exposes bot methods as window.pywebview.api.*()
                           Currently ~20 core endpoints, expanding to all 80+

tray_manager.py         → System tray icon (pystray)
                           Dynamic colour (green/amber/red/grey)
                           Quick actions: show, pause, resume, exit

notification_manager.py → Native OS notifications (plyer)
                           Per-category enable/disable
                           Rate limiting to prevent spam
```

### Trading Engine (UNCHANGED from V3)
All 12 core trading modules carry over without modification:
- `database.py`, `config.py`, `price_engine.py`, `offer_manager.py`
- `fill_tracker.py`, `risk_manager.py`, `coin_manager.py`, `market_intel.py`
- `sniper.py`, `boost_manager.py`, `coinset_client.py`, `splash_manager.py`
- `wallet.py` (adapter) → `wallet_chia.py` / `wallet_sage.py`
- `bot_loop.py`, `api_server.py` (Flask still runs internally)

### GUI (MODIFIED)
- `bot_gui.html` — Added custom titlebar, design tokens (CSS variables), desktop mode detection, dual-mode apiFetch wrapper. All original v3 functionality preserved.

## Dual-Mode Design
The GUI works in BOTH desktop and browser mode:

```javascript
const IS_DESKTOP = typeof window.pywebview !== 'undefined';
// In desktop mode: uses PyWebView bridge
// In browser mode: uses Flask HTTP API (fetch)
```

Custom titlebar only shows in desktop mode (`body.desktop-mode` CSS class). Browser mode works exactly like V3.

## Migration Phases (from DESKTOP_MIGRATION_PLAN.md)

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Desktop Shell | ✅ DONE | PyWebView window wraps Flask, tray icon, notifications |
| Phase 2: JS Bridge | NEXT | Replace fetch() with bridge calls, remove Flask dependency |
| Phase 2.5: Design Overhaul | PLANNED | Full visual redesign per DESIGN_SPEC.md |
| Phase 3: Native Features | PLANNED | Guided startup, full tray, notification categories |
| Phase 4: Testing Framework | PLANNED | Visual test panel + automated test runner |
| Phase 5: Packaging | PLANNED | PyInstaller builds for Windows/macOS/Linux |
| Phase 6: Polish | PLANNED | Error recovery, auto-update, about dialog |

## Design System (from DESIGN_SPEC.md)
V4 introduces CSS design tokens as `:root` variables in bot_gui.html:
- Colours: `--bg-app`, `--accent-primary`, `--status-success`, etc.
- Typography: Inter (UI) + JetBrains Mono (data)
- Spacing: 8pt grid (`--space-1` through `--space-12`)
- Animations: `v4-fadeIn`, `v4-slideUp`, `v4-scaleIn`, `v4-shimmer`
- Components: Defined in DESIGN_SPEC.md, built incrementally during Phase 2.5

## Tech Stack
- **Language:** Python 3.x (system Python on Windows)
- **Desktop:** PyWebView (native OS webview), pystray (tray), plyer (notifications)
- **Web framework:** Flask (runs internally, serves API + GUI)
- **Frontend:** Single-file HTML/CSS/JS (bot_gui.html)
- **Blockchain:** Chia wallet RPC / Sage wallet RPC
- **Exchange:** Dexie.space API
- **Price source:** TibetSwap v2 AMM API
- **State:** SQLite (WAL mode)
- **Packaging:** PyInstaller (Phase 5)

## File Structure
```
v4/
├── desktop_app.py          ← NEW: Main entry point
├── app_bridge.py           ← NEW: JS ↔ Python bridge
├── tray_manager.py         ← NEW: System tray
├── notification_manager.py ← NEW: Native notifications
│
├── api_server.py           ← Kept (runs internally / fallback mode)
├── bot_loop.py             ← Kept (orchestrator)
├── bot_gui.html            ← MODIFIED (titlebar, tokens, dual-mode JS)
├── bot_console.html        ← Kept
│
├── database.py             ← Unchanged from V3
├── config.py               ← Unchanged
├── price_engine.py         ← Unchanged
├── offer_manager.py        ← Unchanged
├── fill_tracker.py         ← Unchanged
├── risk_manager.py         ← Unchanged
├── coin_manager.py         ← Unchanged
├── market_intel.py         ← Unchanged
├── sniper.py               ← Unchanged
├── boost_manager.py        ← Unchanged
├── coinset_client.py       ← Unchanged
├── splash_manager.py       ← Unchanged
├── splash_node.py          ← Unchanged
├── splash_setup.py         ← Unchanged
├── dexie_manager.py        ← Unchanged
├── wallet.py               ← Unchanged
├── wallet_chia.py          ← Unchanged
├── wallet_sage.py          ← Unchanged
├── mock_wallet.py          ← Unchanged
├── coin_prep_worker.py     ← Unchanged
├── super_log.py            ← Unchanged
├── super_log_hooks.py      ← Unchanged
├── startup_test.py         ← Unchanged
├── chia_node.py            ← Unchanged
│
├── tests/                  ← Phase 4
│   └── (test files)
│
├── CLAUDE.md               ← This file
├── DESKTOP_MIGRATION_PLAN.md
├── DESIGN_SPEC.md
├── CODEBASE_AUDIT.md
├── CHIA_DEV_GUIDE.md
├── V2_PLAN.md
├── v1_retrospective.md
└── SAGE_WALLET_RESEARCH.md
```

## Chia-Specific Rules (Critical — same as V3)
1. **UTXO model:** Coins, not balances. Every offer locks a coin.
2. **Always use RPC**, never CLI parsing.
3. **Never trust offer status alone.** Cross-reference `valid_times.max_time`.
4. **Coin operations need confirmation loops.** Poll every 5s.
5. **Wallet operations must be serialised.** One split at a time.
6. **trade_id is the universal key.**
7. **Amounts:** XCH uses 1e12 mojos. CAT uses 10^decimals.
8. **Batch cancels must be sequential** with ~0.3s delays (was 0.5-1s in v1; tightened in v2 for cancel-storm responsiveness — see `wallet_sage.cancel_offers_batch`).
9. **Mass disappearance guard:** 3 confirmations before treating as fills.

## Code Conventions
- Python: snake_case, UPPER_CASE for constants
- Always use `Decimal` for financial amounts
- Always `log_event()` for important operations
- Catch specific exceptions, never bare `except:`
- All wallet RPC through wallet.py
- pip installs: `--break-system-packages`
- Verify syntax: `python -c "import ast; ast.parse(open('file.py').read())"`

## Dependencies
```
# Core (already installed from V3)
flask
requests
python-dotenv

# Desktop (NEW for V4)
pywebview          # Native desktop window
pystray            # System tray icon
plyer              # Native notifications
Pillow             # Required by pystray for icon generation

# Testing (Phase 4)
playwright         # GUI testing (dev only, not bundled)

# Packaging (Phase 5)
pyinstaller        # Build executables
```
