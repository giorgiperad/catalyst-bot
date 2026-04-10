# Chia Market Maker V4 — Comprehensive Test Sheet

**Created:** 2026-04-05
**Purpose:** Master test reference for validating all frontend + backend functionality
**Budget:** Max 40 XCH across offers for live testing

---

## Test Categories

| # | Category | Tests | Status |
|---|----------|-------|--------|
| 1 | App Launch & Navigation | 8 | |
| 2 | API Health & Connectivity | 7 | |
| 3 | Wallet & CAT Management | 8 | |
| 4 | Dashboard View (Bot Stopped) | 12 | |
| 5 | Configuration & Settings | 14 | |
| 6 | Smart Defaults | 5 | |
| 7 | Coin Prep & Management | 6 | |
| 8 | Bot Lifecycle (Start/Stop) | 8 | |
| 9 | Dashboard View (Bot Running) | 14 | |
| 10 | Offers View & Management | 12 | |
| 11 | P&L & Inventory View | 8 | |
| 12 | Market Intelligence View | 7 | |
| 13 | Fills & Trade History | 7 | |
| 14 | Logs & Diagnostics | 6 | |
| 15 | Alerts & Notifications | 5 | |
| 16 | Session Management | 5 | |
| 17 | Splash Network | 5 | |
| 18 | SSE Real-Time Updates | 6 | |
| 19 | Security & Auth | 6 | |
| 20 | Visual & Modal Integrity | 8 | |
| **TOTAL** | | **151** | |

---

## 1. App Launch & Navigation

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 1.1 | GUI loads at localhost:5000 | Navigate to http://localhost:5000/ | HTML page renders, no blank screen | GET / returns 200 | |
| 1.2 | Sidebar visible with all nav items | Inspect sidebar | 8 nav icons: Dashboard, Offers, P&L, Intel, Settings, Logs, Help, About + Shutdown | — | |
| 1.3 | Dashboard is default view | Fresh page load | Dashboard view visible, others hidden | — | |
| 1.4 | Click Offers nav | Click offers icon in sidebar | v4View-offers visible, dashboard hidden | — | |
| 1.5 | Click P&L nav | Click P&L icon in sidebar | v4View-pnl visible | — | |
| 1.6 | Click Market Intel nav | Click intel icon in sidebar | v4View-intel visible | — | |
| 1.7 | Click Settings nav | Click settings icon | Settings view/modal opens | — | |
| 1.8 | Click Logs nav | Click logs icon | v4View-logs visible with log entries | — | |

---

## 2. API Health & Connectivity

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 2.1 | Health endpoint responds | GET /api/health | 200 with {healthy: true, wallet_ok: bool} | Direct API call | |
| 2.2 | Doctor preflight check | GET /api/doctor | Returns readiness report with checks array | Direct API call | |
| 2.3 | Wallet detection | GET /api/wallets/detect | Returns detected wallets (sage/chia) | Direct API call | |
| 2.4 | Sage RPC reachable | GET /api/wallet/sage-running | Returns {running: true/false} | Direct API call | |
| 2.5 | Config validate endpoint | GET /api/config/validate | Returns validation issues or empty | Direct API call | |
| 2.6 | Fingerprint endpoint | GET /api/fingerprint | Returns wallet fingerprint number | Direct API call | |
| 2.7 | SSE stream connects | GET /api/events | SSE connection established, receives heartbeats | EventSource in JS | |

---

## 3. Wallet & CAT Management

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 3.1 | CAT list loads | GET /api/cats | Returns array of discovered CATs | Direct API call | |
| 3.2 | CAT selector populated | Check catSelector dropdown | Shows available pairs | — | |
| 3.3 | Active CAT displayed | Check dashboard pair display | Shows Monkeyzoo Token (MZ_XCH) | Match /api/status | |
| 3.4 | XCH balance shown | Check dashboard balances | Shows spendable + total XCH | Match /api/status balances.xch | |
| 3.5 | CAT balance shown | Check dashboard balances | Shows spendable + total CAT | Match /api/status balances.cat | |
| 3.6 | Balance refresh works | POST /api/balances/refresh | Returns updated balances | Direct API call | |
| 3.7 | Wallet type badge | Check dashboard status area | Shows "Sage" badge | Match config WALLET_TYPE | |
| 3.8 | Fingerprint badge | Check dashboard status area | Shows fingerprint number | Match /api/fingerprint | |

---

## 4. Dashboard View (Bot Stopped)

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 4.1 | Status shows IDLE | Check status indicator | Sidebar shows "IDLE", grey dot | /api/status running=false | |
| 4.2 | Start Bot button visible | Check dashboard controls | Green "Start Bot" button present | — | |
| 4.3 | Stop button disabled/hidden | Check dashboard controls | Stop button not active | — | |
| 4.4 | Session overview shown | Check if resumable session | Shows session restored banner or startup guide | /api/check-resume | |
| 4.5 | Startup checklist renders | Check startup guide panel | 5 steps: Wallet, Pair, Settings, Coin Prep, Start | — | |
| 4.6 | Wallet step green | Check wallet checklist step | Green dot, "Sage is connected" | /api/health | |
| 4.7 | Pair step green | Check pair checklist step | Green dot, pair name shown | — | |
| 4.8 | Market strip loads | Check market data strip | Best Bid, Best Ask, Volume, Liquidity populated | /api/market/summary | |
| 4.9 | AMM strip loads | Check LIVE AMM bar | Price, drift, reserves shown | /api/amm/price | |
| 4.10 | Price matches backend | Compare GUI mid price to API | Values match within rounding | /api/price | |
| 4.11 | Action Flow panel | Check action flow section | Shows "Nothing to do" or relevant actions | — | |
| 4.12 | Advisor panel | Check advisor section | Shows contextual advice based on state | — | |

---

## 5. Configuration & Settings

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 5.1 | Settings load from backend | Open settings view | All fields populated with current config | GET /api/config | |
| 5.2 | Spread BPS field | Check configBaseSpreadBps | Shows current spread value | Match cfg.BASE_SPREAD_BPS | |
| 5.3 | Max buy offers field | Check configMaxBuy | Shows current max buy count | Match cfg.MAX_ACTIVE_BUY | |
| 5.4 | Max sell offers field | Check configMaxSell | Shows current max sell count | Match cfg.MAX_ACTIVE_SELL | |
| 5.5 | Trade size field | Check configTradeXch | Shows current trade size | Match cfg.TRADE_SIZE_XCH | |
| 5.6 | Reserve sliders work | Move XCH reserve slider | Input updates, preview changes | — | |
| 5.7 | Risk profile radio | Check radio buttons | Current profile selected | — | |
| 5.8 | Save settings | Change a value, save | Config persisted, confirmed | POST /api/config returns success | |
| 5.9 | Settings locked when running | Start bot, open settings | "Settings locked" banner shown | — | |
| 5.10 | Tier config section | Check tier inputs | Inner/mid/outer sizes and counts shown | Match config values | |
| 5.11 | Sniper config section | Check sniper inputs | Enabled checkbox + size + prep count | Match config values | |
| 5.12 | Fee config section | Check fee inputs | Fee enabled, amount, coin size | Match config values | |
| 5.13 | Dynamic spread toggle | Check configDynamicSpreadEnabled | Matches backend setting | Match config | |
| 5.14 | Config export | GET /api/config/export-env | Returns valid .env file content | Direct API call | |

---

## 6. Smart Defaults

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 6.1 | Smart defaults endpoint | GET /api/smart-defaults | Returns computed defaults with quality score | Direct API call | |
| 6.2 | Quality badge renders | Run smart defaults in GUI | Quality badge (green/amber/red) appears | — | |
| 6.3 | Profile badge renders | Run smart defaults | Profile badge (Conservative/Balanced/Aggressive) | — | |
| 6.4 | Capital plan shown | Run smart defaults | Capital breakdown with fee/sniper/trading pools | — | |
| 6.5 | Values applied to form | Click apply | Settings fields update with computed values | Verify POST /api/config | |

---

## 7. Coin Prep & Management

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 7.1 | Coin status endpoint | GET /api/coins | Returns coin inventory breakdown | Direct API call | |
| 7.2 | Coin prep verify | GET /api/coin-prep/verify | Returns readiness assessment | Direct API call | |
| 7.3 | Coin prep trigger | POST /api/coin-prep/trigger | Starts coin prep process | Direct API call | |
| 7.4 | Coin prep progress | GET /api/coin-prep/status | Returns phase, progress %, ETA | Direct API call | |
| 7.5 | Coin prep UI shows progress | Monitor logs view during prep | Progress bar updates, phase changes | — | |
| 7.6 | Coin prep completion | Wait for prep to finish | Status shows complete, coins ready | GET /api/coin-prep/status | |

---

## 8. Bot Lifecycle (Start/Stop)

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 8.1 | Pre-start validation | POST /api/bot/start | Returns pre-start check results | Direct API call | |
| 8.2 | Bot starts successfully | Click Start Bot | Status changes to RUNNING, green dot | /api/status running=true | |
| 8.3 | Loop count increments | Wait 30s, check loop count | Loop count > 0 and incrementing | /api/status stats.loop_count | |
| 8.4 | Uptime ticking | Check uptime display | Shows HH:MM:SS incrementing | /api/status stats.uptime_seconds | |
| 8.5 | Stop bot gracefully | Click Stop button | Status → Stopping → IDLE | /api/status running=false | |
| 8.6 | Offers survive stop | Check offers after stop | Offers still on-chain (not cancelled) | /api/offers count > 0 | |
| 8.7 | Resume after stop | Click Start Bot again | Bot resumes managing existing offers | /api/status running=true | |
| 8.8 | Stop Bot To Cancel | Click "Stop Bot To Cancel" | Bot stops AND cancels all offers | /api/offers count = 0 | |

---

## 9. Dashboard View (Bot Running)

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 9.1 | Hero strip visible | Check hero metrics | Mid Price, Active Offers, PnL, Position, Uptime all populated | — | |
| 9.2 | Mid price matches backend | Compare heroMidPrice to API | Values match | /api/status pricing.mid | |
| 9.3 | Active offers count | Compare heroOffers to API | Matches total buy + sell | /api/status offers | |
| 9.4 | Offers split shows buy/sell | Check heroOffersSplit | Shows "X buy / Y sell" breakdown | — | |
| 9.5 | PnL value displayed | Check heroPnl | Shows session PnL (0.0000 if no fills) | /api/pnl | |
| 9.6 | Position displayed | Check heroPosition + heroPositionSide | Shows CAT amount + side label | /api/inventory | |
| 9.7 | Market strip updates | Check market data | Best bid/ask populated from Dexie | /api/market/summary | |
| 9.8 | Activity feed populates | Check activity panel | Shows recent bot actions (postings, requotes) | — | |
| 9.9 | Live controls section | Check spread/skew sliders | Sliders present and functional | — | |
| 9.10 | Spread slider moves | Drag spread slider | Preview updates, value changes | — | |
| 9.11 | Data freshness indicator | Check freshness badge | Shows "Xs ago" or staleness warning | — | |
| 9.12 | Status dot colour | Check sidebar/titlebar dot | Green when running, grey when idle | — | |
| 9.13 | Running badge | Check status area | Shows "RUNNING" in green | — | |
| 9.14 | Ready badge | Check status area | Shows "Ready" badge green | — | |

---

## 10. Offers View & Management

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 10.1 | Offers view loads | Navigate to offers tab | Shows active offers panel | — | |
| 10.2 | Buy offers listed | Check buy offers section | Shows all buy offers with price, size, tier | /api/offers buy array | |
| 10.3 | Sell offers listed | Check sell offers section | Shows all sell offers with price, size, tier | /api/offers sell array | |
| 10.4 | Offer count badges | Check buyCount, sellCount | Match actual offer counts | — | |
| 10.5 | Orderbook chart renders | Check v4ObChart | Visual depth chart with buy/sell bars | — | |
| 10.6 | Offer prices match backend | Compare displayed prices to API | All prices match within formatting | /api/offers | |
| 10.7 | Cancel single offer | Click cancel on one offer | Offer removed, count decrements | /api/offers/cancel | |
| 10.8 | Cancel all offers | Click cancel all, confirm | All offers cancelled, empty state shown | /api/offers/cancel_all | |
| 10.9 | Offer sort toggle | Click sort button | Offers re-sort (price asc/desc) | — | |
| 10.10 | Offer filter (buy only) | Click "Buy" filter | Only buy offers shown | — | |
| 10.11 | History tab | Click "History" tab | Shows fill history | /api/fills | |
| 10.12 | Empty state display | Cancel all, check view | "No open offers" message shown | — | |

---

## 11. P&L & Inventory View

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 11.1 | P&L view loads | Navigate to P&L tab | Shows P&L and inventory data | — | |
| 11.2 | Session PnL shown | Check PnL display | Shows realised + unrealised PnL | /api/pnl | |
| 11.3 | Inventory position | Check inventory display | Shows XCH and CAT holdings | /api/inventory | |
| 11.4 | PnL chart renders | Check PnL chart area | Bar chart with green/red bars (if history exists) | — | |
| 11.5 | Round-trip stats | Check round-trip section | Avg round-trip time shown | /api/pnl round_trip data | |
| 11.6 | Fills per hour metric | Check fill rate | Shows fills/hour rate | /api/pnl | |
| 11.7 | Unmatched fills warning | If unmatched fills exist | Yellow panel shows count of unmatched | — | |
| 11.8 | Circuit breaker panel | If CB active | Red panel shows CB state | — | |

---

## 12. Market Intelligence View

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 12.1 | Intel view loads | Navigate to intel tab | Market data cards visible | — | |
| 12.2 | Competitor spread | Check intelCompSpread | Shows tightest competitor spread | /api/market/intel | |
| 12.3 | Best bid/ask | Check intelBestBid/Ask | Shows live best prices | /api/market/intel | |
| 12.4 | Thin side indicator | Check intelThinSide | Shows which side has less liquidity | — | |
| 12.5 | Orderbook data | GET /api/market/orderbook | Returns buy/sell levels | Direct API call | |
| 12.6 | Spacescan data | Check spacescan section | Holder count, activity, risk level | /api/market/intel | |
| 12.7 | Market summary | GET /api/market/summary | Returns dexie_price, tibet_price, volume, arb_gap | Direct API call | |

---

## 13. Fills & Trade History

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 13.1 | Fills endpoint | GET /api/fills | Returns fill array | Direct API call | |
| 13.2 | Classified fills | GET /api/fills/classified | Returns fills with classification | Direct API call | |
| 13.3 | Fill history in offers tab | Click History tab in offers view | Shows recent fills with side, price, time | — | |
| 13.4 | Fill export CSV | GET /api/fills/export | Returns valid CSV data | Direct API call | |
| 13.5 | Fill intel summary | GET /api/market/fill-intel | Returns fill classification breakdown | Direct API call | |
| 13.6 | PnL endpoint | GET /api/pnl | Returns realised/unrealised with breakdown | Direct API call | |
| 13.7 | Purge fills | POST /api/fills/purge | Clears fill history, resets position | Direct API call (use carefully) | |

---

## 14. Logs & Diagnostics

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 14.1 | Logs view loads | Navigate to logs tab | Shows log entries with timestamps | — | |
| 14.2 | Log entries populated | Check logsContainer | Recent log entries visible | /api/logs | |
| 14.3 | Clear logs | Click clear logs button | Log panel empties | POST /api/logs/clear | |
| 14.4 | Debug bundle download | Click download debug bundle | File downloads with events + state | GET /api/logs/download | |
| 14.5 | Runtime diagnostics | GET /api/diagnostics/runtime | Returns monitor snapshot | Direct API call | |
| 14.6 | Console toggle | POST /api/console/toggle | Console state changes | Direct API call | |

---

## 15. Alerts & Notifications

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 15.1 | Alerts endpoint | GET /api/alerts | Returns active alerts array | Direct API call | |
| 15.2 | Alerts panel renders | Check alertsPanel on dashboard | Shows active alerts with severity colour | — | |
| 15.3 | Dismiss alert | Click dismiss on an alert | Alert removed from panel | POST /api/alerts/dismiss | |
| 15.4 | Alert auto-clear on stop | Stop bot | Operational alerts cleared | GET /api/alerts after stop | |
| 15.5 | Advisor contextual | Check advisor panel | Shows relevant advice for current state | — | |

---

## 16. Session Management

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 16.1 | Check resume endpoint | GET /api/check-resume | Returns resumable session info | Direct API call | |
| 16.2 | Resume session UI | After stop, check dashboard | Shows "Session Restored" banner with stats | — | |
| 16.3 | Fresh start | POST /api/session/fresh-start | Clears session, shows startup guide | Direct API call | |
| 16.4 | Fresh start UI | After fresh start | Startup guide/checklist shown, no resume banner | — | |
| 16.5 | Resume chosen | POST /api/session/resume-chosen | Restores previous session | Direct API call | |

---

## 17. Splash Network

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 17.1 | Splash setup check | GET /api/splash/setup/check | Returns whether binary is installed | Direct API call | |
| 17.2 | Splash stats | GET /api/splash/stats | Returns post count, queue size | Direct API call | |
| 17.3 | Splash node status | GET /api/splash/node | Returns running/stopped state | Direct API call | |
| 17.4 | Splash receive state | GET /api/splash/receive | Returns inbound listening state | Direct API call | |
| 17.5 | Splash incoming list | GET /api/splash/incoming/list | Returns recent inbound offers | Direct API call | |

---

## 18. SSE Real-Time Updates

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 18.1 | SSE connects | Check EventSource state | Connected to /api/events | — | |
| 18.2 | Heartbeat received | Monitor SSE stream | Heartbeat events every ~15s | — | |
| 18.3 | Dashboard update event | Start bot, check SSE | dashboard_update events with offers/balances | — | |
| 18.4 | Price update event | While bot running | price_update events with mid/bid/ask | — | |
| 18.5 | Staleness detection | Disconnect SSE, wait 60s | Data freshness warning appears | — | |
| 18.6 | Auto-reconnect | Kill SSE, check recovery | SSE reconnects within 15s | — | |

---

## 19. Security & Auth

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 19.1 | Write endpoints require token | POST /api/bot/start without token | Returns 401 unauthorized | Direct API call | |
| 19.2 | Read endpoints open | GET /api/status without token | Returns 200 OK | Direct API call | |
| 19.3 | Token header accepted | POST with X-Bot-Local-Token | Returns success | Direct API call | |
| 19.4 | Invalid token rejected | POST with wrong token | Returns 401 | Direct API call | |
| 19.5 | Loopback IP check | Request from 127.0.0.1 | Allowed (loopback) | — | |
| 19.6 | escapeHtml on dynamic content | Inspect rendered HTML | No unescaped dynamic values in innerHTML | DOM inspection | |

---

## 20. Visual & Modal Integrity

| ID | Test | Steps | Expected | BE Check | Result |
|----|------|-------|----------|----------|--------|
| 20.1 | Help modal opens | Click help icon in sidebar | Help modal visible with tabbed content | — | |
| 20.2 | About modal opens | Click about icon in sidebar | About modal with version info | — | |
| 20.3 | Shutdown modal opens | Click shutdown icon | Shutdown confirmation dialog | — | |
| 20.4 | Cancel confirm modal | Click cancel all on offers | Confirmation dialog with count | — | |
| 20.5 | No console errors | Check browser console | No JS errors or uncaught exceptions | — | |
| 20.6 | Responsive layout | Resize window | Layout adapts, no overflow/clipping | — | |
| 20.7 | Colour-coded status | Check various states | Green=running, grey=idle, red=error | — | |
| 20.8 | Design tokens applied | Inspect CSS variables | --bg-app, --accent-primary etc. in use | DOM inspection | |

---

## Execution Log

| Date | Tester | Tests Run | Passed | Failed | Blocked | Notes |
|------|--------|-----------|--------|--------|---------|-------|
| 2026-04-05 | Claude | — | — | — | — | Initial execution |

---

## Failure Register

| Test ID | Description | Actual Result | Severity | Fix Status |
|---------|-------------|---------------|----------|------------|
| — | — | — | — | — |

