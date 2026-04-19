# Findings — Slice 01-08

Regex grep audit: hardcoded IPs, ports, OS paths, API keys, tokens, passwords.

Result: **0 security issues.** No secrets in version-controlled files.

---

## What was checked

| Category | Result |
|----------|--------|
| API keys / tokens hardcoded in production `.py` | None found |
| Passwords in source | None found |
| OS-specific hardcoded paths (`C:\Users\...`, `/home/...`) | Only in gitignored dev scripts |
| Hardcoded external URLs bypassing config | 6 in api_server.py (see below) |
| Wallet RPC defaults | All env-var-overridable via config.py |
| Flask port hardcoded | Duplicate in `__main__` block (cosmetic) |

---

## Local API token pattern (clean)

`api_server.py:208` generates `BOT_LOCAL_WRITE_TOKEN` via `secrets.token_urlsafe(32)` at
runtime. Dev scripts like `check_status.py` hardcode a captured token value, but all such
scripts are gitignored. The token is also local-only (bound to 127.0.0.1), so exposure is
minimal even if it were committed.

## Spacescan API key (clean)

`user_secrets.py` stores keys in the OS user directory (`%APPDATA%\ChiaMarketMaker\` on
Windows), never in the repo or `.env`. `apply_to_config(cfg)` injects them at runtime.
`set_secret("SPACESCAN_API_KEY", key)` is the write path. Well-designed.

## Minor inconsistencies (non-blocking)

### TibetSwap URL bypasses cfg.TIBET_API_BASE (6 locations)

`config.py:397` defines:
```python
self.TIBET_API_BASE = _safe_url("TIBET_API_BASE", "https://api.v2.tibetswap.io")
```

`price_engine.py` correctly uses `cfg.TIBET_API_BASE`. But 6 places in `api_server.py`
hardcode the URL directly:

| Line | Context |
|------|---------|
| 2139 | inline Tibet price fetch in `/api/status` price fallback |
| 2442 | second Tibet price fallback path |
| 6236 | `/api/debug/coinprep` debug endpoint |
| 6432 | `/api/debug/pricing` test 3 |
| 6471 | `/api/debug/tibet-test` |
| 6661 | standalone price-lookup helper |

All use the same default URL so behaviour is identical. Only relevant if a user sets
`TIBET_API_BASE` to a non-default value (e.g., testnet) — these paths would silently ignore
it. → spawn queue

### Flask port 5000 duplicated in api_server `__main__`

`desktop_app.py:103` defines `FLASK_PORT = 5000` and uses it throughout.
`api_server.py:12787+12868` hardcode `5000` separately in the `if __name__ == "__main__":`
block. These are consistent but independent. → spawn queue

---

## Closed findings tallied here

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 0 | blocked |
