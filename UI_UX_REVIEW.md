# UI/UX Review — Chia Market Maker V4

Reviewed: bot_gui.html (~24,500 lines), single-file HTML/CSS/JS app served by Flask.
Date: 2026-04-01

---

## What Works Well

**Design system coherence.** The `:root` token block (lines 20-88) is consistently applied across the file. Backgrounds, borders, text hierarchy, and status colours are largely uniform. The Inter + JetBrains Mono font pairing is well-chosen for a trading tool.

**Dashboard information density.** The hero strip (mid price, active offers, PnL, position, uptime) plus the market strip (bid/ask/volume/liquidity/arb gap) gives an experienced user everything they need at a glance. Each value has a tooltip (`cc-help`) — thorough.

**Startup flow.** The two-layer startup UI (first-run setup guide banner + per-session startup checklist) is well thought out. The checklist unlocks steps progressively. The "Session Restored" resume card (lines 7092-7125) is a strong UX touch for daily users.

**Smart Advisor panel.** Plain-language contextual advice with a clear separation from the to-do list is good. `panel-context-note` underneath each panel title explains scope well.

**Live Controls bar.** Toggle + slider in one panel is efficient. The "Applied ✓" feedback per toggle (e.g. `lcAppliedDynSpread`) reduces doubt about whether a change took effect.

**Action Flow / Activity split panel.** Separating "things you need to do" from "things the bot did" (lines 7222-7251) is correct. The `panel-context-note` copy is accurate and useful.

**SSE architecture.** Using Server-Sent Events as the primary update channel with a clean 5s reconnect loop (line 17264) is the right choice. The 30s polling fallback is a sensible safety net.

**Tooltip system.** `cc-help` tooltips on virtually every control removes the need for a separate help page. Consistent placement and styling.

**Coin prep modal.** A full-screen overlay modal with progress bar, per-side breakdown, and ETA is much better than inline progress. Keeps the main UI clean during a slow operation.

---

## Issues Found

### P1 — Blocking or Confusing

**P1-1. Settings footer overflows on small windows.**
The footer (line 8625) now has four flex children: unsaved badge, validation banner, Save button, Export button. On windows narrower than ~600px or when the badge text is long, these can overlap or the Save button can get pushed below the footer area. The footer uses `justify-content: center` with no `flex-wrap`. The Save button should never be the thing that wraps off-screen.
Lines: CSS `.v4-settings-footer` (1792-1803), HTML footer div (8625-8630).

**P1-2. `pollBotStatus` at line 22789 only updates `updateTibetSuggestion`.**
The function is named `pollBotStatus` and runs every 30 seconds, but actually only calls `updateTibetSuggestion`. All real state updates arrive via SSE. If SSE silently fails (no `onerror` fires, connection stalls), the dashboard can appear live while showing stale data indefinitely. There is no visible staleness indicator (e.g. "last updated Xs ago") on the hero strip or command centre.

**P1-3. Progress bar inside the Logs view is confusing placement.**
`#progressContainer` (lines 8645-8661) sits at the top of the Logs view (`v4View-logs`). When coin prep runs, users are expected to stay on the Logs view to watch progress. However coin prep is triggered from Settings, and the primary coin prep UI is the modal overlay. The duplicate bar in the Logs view is not clearly labelled as coin prep progress, and new users switching to Logs to read debug output will see "Preparing Trading Coins..." unexpectedly at the top before any logs.

**P1-4. Intel view header uses a legacy `card` component, not the V4 view-header pattern.**
The Intel view (line 7874) opens with `<div class="card">` containing `🧠 Market Intelligence` as its `card-title`, while every other view uses the standardised `v4-view-header` / `v4-view-kicker` / `v4-view-title` pattern. This means the Intel view has no subtitle explaining its purpose, and the heading hierarchy is inconsistent (plain `div.card-title` vs `h1.v4-view-title`).
Line: 7874-7876.

**P1-5. "Cancel All Offers" button is primary-red and unlabelled for its destructive scope.**
Line 7196: `<button class="btn btn-cancel btn-danger" id="cancelAllBtn"`. Its `title` attribute describes the action correctly, but the button label is just "Cancel All Offers" with no count indicator. When a user has 30 active offers across multiple tiers, there is no confirmation flow shown — the destructive scope is invisible. The button also shares visual weight with Stop.

**P1-6. Offers view has no view-header and no loading state.**
Lines 7651-7744: The Offers view (`v4View-offers`) jumps straight to `v4-orderbook` without a `v4-view-header`. When the view first loads with no offers, the visual orderbook is empty with no explanatory text, and the tab has no subtitle. Compare with PnL view which has a proper header.

---

### P2 — Notable Improvement

**P2-1. The `settingsUnsavedBadge` and `settingsValidationBanner` use `display:none` on a flex container.**
Both new footer elements use `display:none` as initial state (lines 8626-8627), but are shown with `style.display = 'flex'`. This is correct. However the `.v4-settings-footer` is itself `display: flex` and the two badge elements use `display:none` / `display:flex` toggling. When only one badge is visible, the footer layout can shift the Save button horizontally. Consider adding `min-width: 0` or `flex-shrink: 1` on the badge elements so the Save button stays pinned right.

**P2-2. Tooltip on the fingerprint display (line 7212) is text only — no instruction.**
`title="Click to change wallet"` is the only affordance for the wallet picker. The element looks like a read-only badge. A cursor:pointer style and/or a small edit pencil icon would make it clearer this is interactive.

**P2-3. The "Close the Gap" button label and placement are unclear to new users.**
Line 7631: The button is styled with amber/green gradient and labelled "Close the Gap". The surrounding `lc-manual-sub` text explains its purpose in abstract terms. There is no status display showing the current gap size before you decide to press it. The `lc-manual-status` text below says "Manual strategy is off." — which reads like a disabled state, not an availability indicator.

**P2-4. PnL chart (line 7785) has a fixed height of 120px with no empty-state illustration.**
When there are no fills, the chart area shows a centred text span at a width:100% within a flex container. The text is correct but the tall blank area between two content sections draws attention to absent data rather than providing context.

**P2-5. Intel view sections use inline `background: rgba(30,30,60,0.5)` rather than design tokens.**
Spacescan, Orderbook Depth, TibetSwap, DBX Rewards, and Splash sections all use hardcoded `rgba(30,30,60,0.5)` backgrounds (lines 7904, 7928, 7954, 7972, 7988). This is slightly lighter than `--bg-surface` and will not automatically adapt if the design tokens are ever changed. These should use `var(--bg-surface)`.

**P2-6. Splash P2P section is very long with no collapse control.**
Lines 7987-8050: The Splash section is the longest subsection in the Intel view. It contains two separate grids (broadcast stats + incoming listener) and a toggle button. Unlike the Live Controls bar, there is no collapse button. The incoming listener toggle button (`splashListenToggle`) also looks like a primary action but sits inside a diagnostic panel — its visual weight suggests it does more than it does.

**P2-7. The coin prep breakdown inside Settings is hard to read at small sizes.**
`#coinPrepPreview` (line 8381) inside the Order Book section renders a multi-column grid showing XCH coins, sizes, and totals. The column labels ("Coins", "Size", "Total") are in very small text (0.75em and 0.85em inside an already compact section). These labels can be completely illegible on non-retina Windows displays.

**P2-8. "Debug Bundle" button (line 8668) is labelled only with a name, not what it produces.**
New users will not know what a "debug bundle" contains. A short tooltip or subtitle ("Downloads superlog + snapshots for troubleshooting") would reduce support friction.

**P2-9. `heroUptime` font-size differs from other hero values.**
Line 7154: `style="font-size: var(--text-xl);"` is applied inline to the uptime hero value. The other four hero values use the default `v4-hero-value` size. The uptime time string (e.g. `123:45:67`) is wider than the other values and the smaller override was presumably needed to fit it, but this means it looks visually subordinate compared to the other hero cards.

**P2-10. Wallet type badge (line 7208) shows "Sage" in green even when the bot is stopped.**
The badge is styled as a success-green permanent indicator. After a wallet disconnect or during the `Checking...` sync state, the badge continues showing "Sage" with green background, which is misleading. The wallet type label should follow the same colour logic as the `syncIndicator`.

---

### P3 — Polish

**P3-1. `v4-toolbar` Cancel All Offers button uses a `title` attribute for its description.**
Line 7196: Important safety information (what exactly gets cancelled) is only accessible via native browser tooltip, which requires hovering and has no styling. This should be a `cc-help` tooltip to match the rest of the UI.

**P3-2. The first-run "Setup Guide" banner (line 6987) and the "startup guide" (line 7026) overlap visually when both are visible.**
Both render at the top of the dashboard. The setup guide is for first-time users (blank `CAT_ASSET_ID`), the startup guide is the per-session checklist. They can both be visible simultaneously, creating a dense stack of instructional content before any trading controls.

**P3-3. `consoleWarningBanner` (line 7217) is never hidden in desktop mode.**
The banner warns about a console window, which is only relevant in Flask-only or dev mode. In `desktop-mode` (PyWebView), the console window warning is irrelevant but there is no CSS rule hiding `#consoleWarningBanner` when `body.desktop-mode` is applied.

**P3-4. `heroStrip` (line 7131) and `marketStrip` (line 7160) are always rendered, even pre-bot-start.**
Both strips show `—` dashes in all value slots until the bot starts and data arrives. There is no skeleton loading state — the dashes sit next to permanent labels without any visual indication they are waiting for data rather than just empty. Compare against the command centre panels which use `style="opacity: 0.3;"` to visually signal pending state.

**P3-5. Section comment style is inconsistent between views.**
Settings uses `<!-- ══ SECTION: ... ══ -->` comments. Dashboard uses `<!-- ===== ... ===== -->`. The Intel view uses no section markers at all. This is a developer experience issue, not a user one, but it makes the HTML harder to navigate.

**P3-6. Some `oninput` / `onchange` handlers are on the element in HTML and some are added via `addEventListener` in JS.**
Settings fields added in Part A use `addEventListener` in `attachUnsavedListeners()`. Existing fields use inline `oninput=` attributes. These coexist without conflict but create two different patterns for the same type of event handling.

**P3-7. The Offers view visual orderbook uses left-aligned numbers without monospace font.**
`v4UpdateOrderbook` builds the order book depth display. Price values are rendered in the standard UI font, not `var(--font-mono)`. For numeric data that aligns on decimal points, this can cause ragged alignment at different price magnitudes.

**P3-8. The market strip "Arb Gap" sub-label (line 7186) always says "Dexie vs Tibet".**
Once a gap value is populated, showing "Dexie vs Tibet" as sub-label is redundant — the context is already set by the card title. The sub-label could show the absolute price gap or a short interpretation (e.g. "Within sniper threshold") to add informational value.

**P3-9. "Reset Position" button (line 7817) in the PnL view has no confirmation.**
Resetting position history is irreversible in the current session. The button has a `title` describing the action but no confirmation dialog. This is inconsistent with "Cancel All Offers" which already has a styled confirm flow.

**P3-10. The dashboard Activity feed link "View full logs →" (line 7245) uses `onclick="v4SwitchView('logs'); return false;"` on an `<a href="#">`.**
Using `href="#"` causes the page to scroll to the top before `return false` cancels it, producing a visible scroll jank on longer dashboards. Using `href="javascript:void(0)"` or a `<button>` element styled as a link would avoid the jump.

---

## Recommendations Summary

| Priority | ID | Recommendation |
|---|---|---|
| P1 | P1-1 | Add `flex-wrap: wrap` and `justify-content: flex-end` to `.v4-settings-footer`; ensure Save button is last child so it wraps last |
| P1 | P1-2 | Add a "last updated" timestamp to the hero strip; make it amber after 60s without an SSE event |
| P1 | P1-3 | Move or clearly label the progress bar in the Logs view, or hide it unless coin prep is actively running |
| P1 | P1-4 | Replace the Intel view `card` wrapper with the standard `v4-view-header` pattern |
| P1 | P1-5 | Add a live count to the "Cancel All Offers" label (e.g. "Cancel All (12)") and show a styled confirm dialog before executing |
| P1 | P1-6 | Add a `v4-view-header` to the Offers view; show an empty-state message with instruction when no offers exist |
| P2 | P2-1 | Add `flex-shrink: 1; min-width: 0; overflow: hidden` to the badge elements in the settings footer |
| P2 | P2-2 | Add `cursor: pointer` CSS and a `cc-help` tooltip to the fingerprint display to signal interactivity |
| P2 | P2-3 | Show the current arb gap value in the Close the Gap section before the button |
| P2 | P2-4 | Add a styled empty state to the PnL chart area (e.g. "No fills yet this session") |
| P2 | P2-5 | Replace hardcoded `rgba(30,30,60,0.5)` in Intel sections with `var(--bg-surface)` |
| P2 | P2-6 | Add a collapse control to the Splash P2P section |
| P2 | P2-7 | Increase label font size in the coin prep breakdown preview to minimum 0.82em |
| P2 | P2-8 | Add a `cc-help` tooltip to the Debug Bundle button |
| P2 | P2-9 | Remove the inline `font-size` override on `heroUptime` or apply it to all hero values consistently |
| P2 | P2-10 | Tie wallet type badge colour to connection state, not a static green |
| P3 | P3-1 | Replace `title` on Cancel All with a `cc-help` tooltip |
| P3 | P3-2 | Add CSS to hide first-run banner when startup guide is also visible, or merge them |
| P3 | P3-3 | Add `.desktop-mode #consoleWarningBanner { display: none; }` |
| P3 | P3-4 | Use `opacity: 0.35` on hero/market strip dashes pre-start to signal "awaiting data" |
| P3 | P3-5 | Dev-quality issue only; no user action needed |
| P3 | P3-6 | Dev-quality issue only; no user action needed |
| P3 | P3-7 | Apply `font-family: var(--font-mono)` to order book price values |
| P3 | P3-8 | Use the arb gap sub-label to show a contextual interpretation once data loads |
| P3 | P3-9 | Add a styled confirm dialog before resetting position |
| P3 | P3-10 | Replace `href="#"` with `href="javascript:void(0)"` or a `<button>` on the "View full logs" link |
