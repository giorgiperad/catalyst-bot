# CATalyst

Automated market maker for CAT tokens on the [Dexie](https://dexie.space) exchange, powered by [Sage wallet](https://sage.rigidnetwork.io). Maintains a tiered bid/ask ladder, auto-requotes on price moves, and handles coin management — all from a native desktop window.

**Status:** Beta — actively used in production. No warranty. Use at your own risk.

---

## Features

- **Tiered ladder** — inner/mid/outer/extreme offer sizing, configurable per side
- **Dynamic spreads** — adjusts based on volatility, inventory skew, and competitor depth
- **Smart Settings** — one-click capital planning from wallet balance and market data
- **Sniper probes** — detects arb gaps and probes new price edges
- **Mempool detection** — spots TibetSwap swaps before they confirm on chain
- **Multi-source fill verification** — Spacescan + Sage + Dexie fallback chain
- **Splash P2P** — broadcasts offers directly to other Splash nodes
- **Native desktop app** — system tray, notifications, runs in background
- **Coin prep** — automatic UTXO splitting and replenishment

---

## Requirements

- Windows 10 or 11 (64-bit)
- Python 3.10+
- [Sage wallet](https://sage.rigidnetwork.io) with RPC enabled
- XCH + the CAT token you want to trade

---

## Quick start

```bash
# Install dependencies
pip install flask requests python-dotenv pywebview pystray plyer Pillow --break-system-packages

# Copy config template
cp .env.example .env
# Edit .env with your Sage wallet paths

# Run
python desktop_app.py
```

Or download the Windows installer from [Releases](https://github.com/Lowestofttim/catalyst-bot/releases).

---

## Configuration

All settings live in `.env`. The key ones:

| Setting | What it does |
|---------|-------------|
| `SAGE_RPC_URL` | Sage wallet RPC endpoint (default `https://127.0.0.1:9257`) |
| `SAGE_CERT_PATH` / `SAGE_KEY_PATH` | Path to Sage mTLS client cert and key |
| `CAT_ASSET_ID` | The CAT you want to trade (64-char hex) |

Everything else (spread, offer count, tier sizes, reserves) is configured via **Smart Settings** in the GUI — no need to edit `.env` manually for trading parameters.

> **Security:** `.env` contains wallet cert paths. Never commit it. The `.gitignore` already excludes it.

---

## Architecture

```
desktop_app.py          Entry point — Flask + PyWebView + system tray
api_server.py           HTTP API + Server-Sent Events for the GUI
bot_loop.py             Main trading loop (price → requote → fills → repeat)
bot_gui.html            Dashboard UI (single-file HTML/CSS/JS)

offer_manager.py        Offer creation, cancellation, rolling wave requote
fill_tracker.py         Fill detection + multi-source verification
price_engine.py         Price oracle (TibetSwap + Dexie weighted average)
risk_manager.py         Circuit breakers, position limits, spread calculation
coin_manager.py         UTXO tracking, tier classification, topup worker

wallet_sage.py          Sage wallet RPC adapter
dexie_manager.py        Dexie API integration (posting, fingerprinting)
spacescan.py            On-chain verification via Spacescan API
sniper.py               Arb gap probing

config.py               Typed config loader from .env
database.py             SQLite state (offers, fills, events, coins)
```

---

## Running modes

| Mode | Command | Description |
|------|---------|-------------|
| Desktop (default) | `python desktop_app.py` | Native window + system tray |
| Browser | `python desktop_app.py --flask` | Opens in browser at localhost:5000 |
| Dev | `python desktop_app.py --dev` | Desktop window + browser access |

---

## Tests

```bash
pip install pytest --break-system-packages
cd tests && pytest
```

---

## Disclaimer

This is beta software that controls a live trading wallet. **There is no warranty.** You can lose funds if the bot misbehaves or if you misconfigure it. The authors accept no liability for financial losses.

---

## License

[MIT License](LICENSE) — Copyright (c) 2026
