# test_all_apis.py — Comprehensive API Diagnostic Script

Complete diagnostic tool for testing all 7 external API services used by the Chia liquidity bot. Tests 27+ endpoints across wallet, exchange, pricing, and blockchain verification services.

## Quick Start

```bash
# Run the diagnostic
python test_all_apis.py

# Expected output: [OK], [XX], [!!], [--] status indicators
# Summary at end: PASS/FAIL/WARN/SKIP counts
```

## What It Tests

### 1. Sage Wallet RPC (localhost:9257) — Optional
Tests the Sage light wallet RPC interface (only if `WALLET_TYPE=sage` in config).

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/get_wallets` | POST | List wallets | SKIP if not running |
| `/get_coins` | POST | Get owned coins | SKIP if not running |
| `/get_offers` | POST | Get all offers | SKIP if not running |
| `/get_wallet_balance` | POST | Get balances | SKIP if not running |
| Connectivity | - | Basic connectivity | SKIP if not running |

**Required only if:** `WALLET_TYPE=sage` in `.env`
**Default:** Uses official Chia wallet (Sage is optional light wallet)

---

### 2. Dexie API (https://api.dexie.space) — Critical
Tests the Dexie DEX API used for posting offers and getting orderbook data.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/offers` | GET | Get all offers on Dexie |
| `/v1/offers?offered={CAT_ID}&requested=xch` | GET | Get filtered offers (CAT→XCH) |
| `/v1/trades` | GET | Get recent trade history |
| `/v1/tickers` | GET | Get ticker/price data |

**Status:** CRITICAL — bot cannot post offers without this
**Note:** Only GET endpoints tested (no actual posts to avoid pollution)

---

### 3. TibetSwap API (https://api.v2.tibetswap.io) — Critical
Tests the TibetSwap AMM API used for reference pricing.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/pair/{asset_id}` | GET | Get pair reserves and price |
| `/quote` | GET | Get swap quote (price impact) |

**Status:** CRITICAL — used for price reference
**Note:** Some tests skipped if `CAT_ASSET_ID` not configured

---

### 4. Spacescan API (https://api.spacescan.io) — Recommended
Tests Spacescan blockchain explorer API for fill verification and balance checks.

| Endpoint | Method | Purpose | Tier |
|----------|--------|---------|------|
| `/coin/info/{coin_id}` | GET | Check if coin spent | Pro/Free |
| `/address/xch-balance/{address}` | GET | Get XCH balance | Pro/Free |
| `/address/token-balance/{address}` | GET | Get CAT balances | Pro/Free |

**Status:** Recommended — used for fill detection
**Auto-detection:** Detects Pro (with API key) vs Free tier
**Config:** Set `SPACESCAN_API_KEY` for Pro tier

---

### 5. Offerpool (https://offerpool.io) — Optional
Tests cross-listing capability for wider offer visibility.

| Endpoint | Purpose |
|----------|---------|
| `/api/v1/offers` | Cross-post offers for visibility |

**Status:** Optional — only if `OFFERPOOL_ENABLED=true`
**Note:** Connectivity test only (no actual posts)

---

### 6. Splash P2P (localhost:4000) — Optional
Tests local P2P network submission (usually not running).

| Endpoint | Purpose |
|----------|---------|
| `/` | Submit offers to P2P network |

**Status:** Optional — skipped if not running
**Note:** Most users won't have this running

---

### 7. Coinset API (https://api.coinset.org) — Optional
Tests Coinset coin data service (future integration point).

| Endpoint | Purpose |
|----------|---------|
| `/` | Coinset coin queries |

**Status:** Optional — skipped if not available
**Note:** Not currently used by bot

---

## Configuration Checks

Script also validates bot configuration:
- Wallet type (chia vs sage)
- Dexie auto-post enabled?
- TibetSwap timeout adequate?
- Spacescan API key valid?
- Offerpool enabled?
- Market intelligence enabled?

## Output Format

### Status Icons

| Icon | Status | Meaning |
|------|--------|---------|
| `[OK]` | PASS | Working as expected |
| `[XX]` | FAIL | Critical failure — needs fixing |
| `[!!]` | WARN | Non-critical issue — monitor |
| `[--]` | SKIP | Not tested (e.g., optional service not running) |

### Example Output

```
================================================================================
  COMPREHENSIVE API DIAGNOSTIC
================================================================================

--- DEXIE API (https://api.dexie.space) ---

  Base URL: https://api.dexie.space
  CAT Asset ID: 08beba...

  [OK] Dexie connectivity: PASS -- 245ms, HTTP 200
  [OK] Dexie /v1/offers: PASS -- 1847 offer(s) (234ms)
  [OK] Dexie /v1/offers (filtered): PASS -- 142 CAT/XCH offer(s) (189ms)
  [OK] Dexie /v1/trades: PASS -- 8934 trade(s) (267ms)
  [OK] Dexie /v1/tickers: PASS -- 126 ticker(s) (156ms)

================================================================================
  RESULTS: 23 passed, 1 failed, 3 warnings, 2 skipped / 29 total

  FAILURES (critical — bot may not work):
    XX Dexie /v1/offers: HTTP 503 (12045ms) -- service temporarily unavailable

  WARNINGS (non-critical — monitor):
    !! TibetSwap /quote: 8234ms -- slow response
    !! Spacescan API key: not configured (Free tier)
    !! Offerpool disabled: check if you want cross-posting

  Core APIs working. Check warnings above for optional services.
================================================================================
```

## Interpreting Results

### All Green (0 failures)
```
  All external APIs are working correctly. Bot should start normally.
```
Bot is ready to run.

### 1-2 Failures
```
  Some API endpoints have issues. Review failures above and take corrective action.
```
Check which endpoint failed and investigate connectivity/configuration.

### 3+ Failures
```
  Multiple API endpoints failing. Bot will not operate properly. Address failures above.
```
Bot will not work. Address all critical failures before starting.

## Common Failure Scenarios

### Sage Wallet Failures (SKIP)
**Expected** if using official Chia wallet (default).
- Set `WALLET_TYPE=sage` in `.env` if you want to use Sage light wallet
- Ensure Sage is running on port 9257

### Dexie Failures (FAIL)
**Critical** — bot cannot post offers.
- Check internet connection
- Verify `DEXIE_API_BASE` in config
- Check if Dexie.space is down (check https://dexie.space)

### TibetSwap Failures (FAIL)
**Critical** — price reference unavailable.
- Check internet connection
- Verify `TIBET_API_BASE` in config
- Check if TibetSwap API is down

### Spacescan Failures (WARN)
**Non-critical** — fills won't be verified.
- Check API key if using Pro tier
- Service may be temporarily down
- Free tier has lower rate limits

### Offerpool Failures (WARN)
**Non-critical** — offers won't be cross-listed.
- Optional service — not required
- Enable with `OFFERPOOL_ENABLED=true` if desired

### Splash P2P Failures (SKIP)
**Expected** — most users don't run P2P node.
- Only required if doing P2P submissions
- Usually skipped safely

## Performance Benchmarks

Script measures and reports response times:
- **Good:** <500ms per call
- **Acceptable:** <2000ms per call
- **Slow:** 2-5 seconds per call
- **Very Slow:** >5 seconds per call

Slow responses indicate:
- Network latency
- API service degradation
- Rate limiting (pause longer between calls)

## Rate Limiting

Script includes 2-second pauses between calls to avoid:
- API rate limiting
- Accidental DOS
- Overwhelming services

If you get rate limit errors:
- Increase sleep time in script (modify `time.sleep(2)`)
- Run at off-peak hours
- Consider caching results

## Configuration Used

Script reads from bot's config:
- `DEXIE_API_BASE` — Dexie URL (default: https://api.dexie.space)
- `TIBET_API_BASE` — TibetSwap URL (default: https://api.v2.tibetswap.io)
- `SAGE_RPC_URL` — Sage wallet URL (default: https://localhost:9257)
- `SPACESCAN_API_KEY` — API key (if configured, uses Pro tier)
- `WALLET_ADDRESS` — Optional, for balance checks
- `CAT_ASSET_ID` — Optional, for CAT-specific tests
- `WALLET_TYPE` — chia (default) or sage
- `OFFERPOOL_ENABLED` — Optional cross-listing

All values taken from `.env` file or defaults.

## Sensitive Data Handling

- API keys are **never printed in full**
- Shown as `***key_last_6_chars` only
- No credentials leaked to stdout
- Safe to run with logging enabled

## Running Without Config

If `config.py` cannot be loaded:
- Script falls back to environment variables
- Uses sensible defaults for URLs
- Tests proceed with reduced information
- No failures — just SKIP tests that need config

## Tips

### Test Before Bot Startup
Always run this before starting the bot to verify all APIs are working.

### Use for Debugging
If bot behaves strangely:
1. Run `test_all_apis.py`
2. Check for slow/failed endpoints
3. Investigate configuration
4. Re-run to confirm fix

### Monitor API Health
Run periodically (e.g., daily) to catch degradation early:
```bash
python test_all_apis.py >> api_health.log
# Check log for failures
```

### Check Specific Service
Comment out other test sections if you want to focus on one API.

## Requirements

- Python 3.6+
- `requests` library
- Internet connection (to test external APIs)
- Config file with API keys/settings (optional)

## Files

- `test_all_apis.py` — Main script
- `TEST_ALL_APIS_README.md` — This documentation
- `test_spacescan.py` — Spacescan-only diagnostic (legacy)

## Support

If tests fail:
1. Check internet connectivity
2. Verify URLs in `.env` are correct
3. Check API service status (visit URLs in browser)
4. Review API key validity
5. Check firewall/proxy settings
6. Run with verbose output (or add debug logging)

## Exit Code

Script always exits with `0` (success). Check the RESULTS line for actual status.

## See Also

- `CLAUDE.md` — Project overview and tech stack
- `CHIA_DEV_GUIDE.md` — Chia blockchain reference
- `V2_PLAN.md` — V2 architecture
