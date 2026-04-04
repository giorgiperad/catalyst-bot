# Chia Market Maker

An automated market maker for Chia blockchain CAT tokens on the [Dexie](https://dexie.space) exchange. The bot maintains a symmetric bid/ask ladder, profits from the spread, and uses TibetSwap v2 pricing as the primary oracle.

**Status:** Beta — actively used in production. No warranty. Use at your own risk.

---

## Features

- Symmetric market-making on Dexie with configurable spread (basis points)
- Tiered order sizing (inner/mid/outer/extreme tiers)
- Dynamic spread adjustment based on volatility and inventory skew
- Sniper mode for closing arbitrage gaps
- Native desktop application (PyWebView + system tray) or browser-based Flask mode
- Supports Sage light wallet (recommended) or official Chia wallet
- Coin preparation and health management
- Splash P2P offer broadcasting
- Spacescan on-chain verification
- Full audit log to SQLite

---

## Requirements

- Python 3.10 or newer
- [Sage wallet](https://github.com/rigidnetwork/sage) (recommended) or Chia wallet with full node
- A funded wallet with XCH and the CAT you want to market-make

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/chia-market-maker.git
cd chia-market-maker

# Install core dependencies
pip install flask requests python-dotenv --break-system-packages

# Install desktop dependencies (optional — required for desktop mode)
pip install pywebview pystray plyer Pillow --break-system-packages

# Copy the config template and fill in your values
cp .env.example .env
```

---

## Configuration

All settings live in `.env`. Copy `.env.example` to `.env` and configure:

| Key | Description |
|-----|-------------|
| `WALLET_TYPE` | `sage` (recommended) or `chia` |
| `SAGE_CERT_PATH` / `SAGE_KEY_PATH` | Path to your Sage mTLS client cert/key |
| `CAT_ASSET_ID` | The CAT token you want to trade |
| `SPREAD_BPS` | Bid/ask spread in basis points (e.g. `800` = 8%) |
| `MAX_ACTIVE_BUY` / `MAX_ACTIVE_SELL` | Max simultaneous offers per side |
| `DEFAULT_TRADE_XCH` | XCH size per offer |

See `.env.example` for the full list with comments.

> **Security note:** Keep your `.env` file private. It contains wallet certificate paths. Never commit it to git.

---

## Running

### Desktop mode (recommended)

Opens a native desktop window with system tray icon:

```bash
python desktop_app.py
```

### Browser mode (fallback / headless servers)

Opens the GUI in your browser at `http://localhost:5000/`:

```bash
python desktop_app.py --flask
```

### Dev mode (desktop window + browser access)

```bash
python desktop_app.py --dev
```

---

## Architecture

```
desktop_app.py          Main entry point — starts Flask, creates PyWebView window, manages tray
api_server.py           Flask HTTP API + Server-Sent Events for the GUI
bot_loop.py             Main trading loop orchestrator
bot_gui.html            Single-file dashboard UI (HTML/CSS/JS)
config.py               Typed configuration loader from .env
database.py             SQLite state store (offers, fills, events)
offer_manager.py        Offer creation, cancellation, lifecycle
fill_tracker.py         Fill detection and verification
price_engine.py         Price oracle (Dexie + TibetSwap weighted average)
risk_manager.py         Circuit breakers, position limits
coin_manager.py         UTXO management and coin preparation
sniper.py               Arbitrage gap-closing offers
wallet_sage.py          Sage wallet RPC adapter
wallet_chia.py          Chia wallet RPC adapter
```

---

## Tests

```bash
pip install pytest --break-system-packages
pytest
```

---

## Disclaimer

This is beta software. It controls a live trading wallet and submits real blockchain transactions. **There is no warranty.** You can lose funds if the bot misbehaves or if you misconfigure it. Always test with `DRY_RUN=true` first. The authors accept no liability for financial losses.

---

## License

[MIT License](LICENSE) — Copyright (c) 2026 Tim
