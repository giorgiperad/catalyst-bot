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
| 2026-04-01 | Probe-on-fill = positive signal, not failure | When a sniper probe fills immediately, treat it as price confirmation and build ladder at that level. Do not retry the probe — that wastes coins and time. |
| 2026-04-01 | Topup threshold = `MAX_BUY_OFFERS + MAX_SELL_OFFERS` spare coins | 30% of max offers is too low. Create-first requote requires enough spare coins to replace the whole side without falling back to cancel-first. |
| 2026-04-01 | Topup backoff = exponential starting at 5 min, max 60 min | 2-hour fixed backoff is too long. Ladder degrades during the wait. Exponential gives fast retry on transient failures. |
| 2026-04-01 | Circuit breaker must NOT halt the correcting side | If CB trips because position is over-long, sell offers must continue. Halting everything when you should be selling is wrong. |
| 2026-04-01 | Smart Settings must clear legacy MAX_MID/MIN_MID keys | Legacy fallback chain in config silently overrides HARD_MAX/HARD_MIN. Fragile. Smart Settings writes both new and legacy keys. |

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
8. **Batch cancels must be sequential** with 0.5-1s delays.
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
