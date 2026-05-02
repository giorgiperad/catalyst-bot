# CATalyst

## Quick Reference

```bash
# Run (dev)
python desktop_app.py          # Desktop window + system tray
python desktop_app.py --flask  # Browser-only at localhost:5000
python desktop_app.py --dev    # Desktop + browser simultaneously

# Tests
cd tests && pytest

# Build
python build.py                # PyInstaller → dist/Catalyst/
python build.py --no-clean     # Faster iterative build
```

## Git Workflow

- Default future changes to a feature branch plus pull request into `main`.
- Commit directly to `main` only when the user explicitly asks for it.
- Before opening or merging a PR, run the relevant tests/build as if checking out the repo fresh.

## Architecture

Pure Python desktop app. NOT Tauri/Rust despite the directory name.

- **Frontend:** Single-file vanilla HTML/CSS/JS (`bot_gui.html`)
- **Backend:** Flask HTTP + SSE (`api_server.py`), runs on `127.0.0.1:5000`
- **Desktop:** PyWebView wraps the Flask server in a native window
- **Bridge:** `app_bridge.py` exposes ~82 Python methods to JS via `window.pywebview.api.*`
- **Trading:** `bot_loop.py` runs the main trading cycle in a background thread
- **Database:** SQLite WAL mode via `database.py` — all DB access goes through this module
- **Config:** `.env` file loaded by `config.py` into singleton `cfg`. Use `cfg.SETTING_NAME`.
- **Wallet:** `wallet.py` adapts to Sage or Chia wallet based on `WALLET_TYPE` env var

## Code Conventions

- **Always use `Decimal`** for prices/amounts, never `float`. Coin amounts are mojos (integers).
- **Imports:** `from config import cfg` for settings, `from super_log import slog` for logging.
- **Logging:** `slog(category, message, data=None, level="info")` — never use `print()` or stdlib `logging`.
- **DB access:** Always through `database.py` functions — no raw SQL in other modules.
- **Wallet calls:** Always `from wallet import ...` — never import `wallet_sage` or `wallet_chia` directly.
- **Error returns:** AppBridge methods return `{"success": True/False, ...}` dicts. Never raise into JS.
- **HTML safety:** All server-sourced data rendered via `innerHTML` must go through `escapeHtml()`. Prefer `data-*` attributes + event delegation over inline `onclick` handlers; string-concat `onclick="fn('${userdata}')"` can't be made safe.
- **Dependencies:** canonical list in `requirements.txt` (runtime) and `requirements-dev.txt` (runtime + pytest/xdist/ruff/bandit/vulture/Playwright).
- **Versioning:** single source of truth in `_version.py`. Build-release CI overwrites it from the git tag.

## Testing

- Tests in `tests/`, named `test_<module>.py`
- `tests/conftest.py` isolates test data with `CMM_DATA_DIR` and fixes Windows capture encoding.
- Integration tests hitting live APIs are excluded in `conftest.py` `collect_ignore`
- Mock wallet available: `tests/mock_wallet.py`

## User Data Location

- Windows: `%APPDATA%\Catalyst\`
- macOS: `~/Library/Application Support/Catalyst/`
- Linux: `~/.local/share/Catalyst/`
- Override: `CMM_DATA_DIR` env var

## Key Module Map

| Module | Purpose | Lines |
|--------|---------|-------|
| `api_server.py` | Flask routes + SSE events | ~12k |
| `bot_loop.py` | Trading loop orchestrator | ~8k |
| `bot_gui.html` | Entire frontend UI | large |
| `coin_manager.py` | UTXO tracking + tier classification | ~5.7k |
| `coin_prep_worker.py` | Async coin splitting subprocess | ~5.7k |
| `offer_manager.py` | Offer lifecycle (create/track/requote/cancel) | ~3k |
| `wallet_sage.py` | Sage wallet RPC adapter | ~3.7k |
| `database.py` | SQLite state layer | ~4.3k |
| `fill_tracker.py` | Fill detection + verification | ~1.3k |
| `risk_manager.py` | Circuit breakers, dynamic spreads | ~1.2k |
| `price_engine.py` | TibetSwap + Dexie price oracle | ~940 |
| `config.py` | Typed .env config loader | ~1k |

## Threading Model

- Main thread: PyWebView window
- Thread 1: Flask server
- Thread 2: BotLoop trading cycle
- Subprocess: coin_prep_worker
- SQLite WAL mode enables safe concurrent reads. Module-level locks protect shared state.
