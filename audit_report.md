# Codebase Audit Report — 2026-04-08 (Merged)

> Merged from two parallel audit passes (Claude + Codex). Where the reports overlapped, the more specific finding was kept; contradictions are flagged inline. Each finding was re-verified before being included here. **Report only — no code edits made.**

---

## Part 1 — Deletable Code (the actionable list)

This is the focused "what can I delete" view. Each row is a single deletion decision. Read the **Decision** column to triage:

- **DELETE** = high confidence dead. Safe to remove with `git rm` / Edit. Verify the line is still there first.
- **DELETE-IF** = needs a 30-second sanity check before deleting (a specific reason is given).
- **KEEP** = looked dead at first glance but is actually wired up via dynamic dispatch / external API / etc.

### 1.1 Python — unreferenced functions and methods

| File:Line | Symbol | Decision | Reason |
|---|---|---|---|
| `api_server.py:971` | `AlertStore.get_all` (method) | **DELETE** | Verified — `alerts.get_all()` has zero call sites in `.py`, `bot_gui.html`, or `app_bridge.py`. The `AlertStore` class is used (`alerts = AlertStore()` at api_server.py:978), but this specific method is not. |
| `api_server.py:5841` | `_fetch_dexie_ticker_full(ticker_id)` | **DELETE** | Helper defined once, never called. Standalone fetch function with no consumers. |
| `api_server.py:6032` | `_fetch_tibet_pool_standalone(asset_id, decimals)` | **DELETE** | Same pattern — definition-only standalone fetcher. |
| `api_server.py:9563` | `_get_main_console_hwnd` / `_set_window_visible` / `_find_window_by_pid` | **DELETE** | Three Windows console-window helpers, all definition-only. Likely leftovers from a removed "show/hide console" feature. |
| `boost_manager.py:1075` | `BoostManager.mark_cascade_done` | **DELETE** | No callers anywhere. |
| `coin_manager.py:761` | `get_tier_coin_requirements(max_offers_per_side)` | **DELETE** | Definition-only helper. The CoinManager uses different functions for tier accounting. |
| `coinset_client.py:308` | `watch_coins` / `unwatch_coins` / `clear_watched_coins` / `get_watched_coin_count` | **DELETE-IF** | Public methods on a client object — no in-repo callers, but the coinset client is sometimes called externally for diagnostics. **Confirm you're not using these in a script outside the repo before deleting.** |
| `database.py:3531` | `cleanup_old_events(days=7)` | **DELETE-IF** | No callers. Looks like a cleanup utility that was supposed to be scheduled but never wired up. **If you ever planned to schedule database cleanup, you may want to wire this in instead of deleting.** |
| `database.py:3980` | `prune_market_analysis_cache()` | **DELETE-IF** | Same pattern — looks like a maintenance routine that nothing schedules. Same caveat as above. |
| `market_intel.py:583` | `prune_fingerprints()` | **DELETE** | Explicit comment: "Compatibility no-op after Offerpool removal". Empty stub. |
| `wallet_sage.py:207` | `class SageTransactionError(Exception)` | **DELETE** | Custom exception class is never raised, caught, or referenced anywhere. |
| `wallet_sage.py:262` | `reset_initialization_state()` | **DELETE-IF** | No in-repo callers. Looks like a debug helper for forcing re-init. **Keep if you ever call it manually from a Python REPL during dev.** |
| `wallet_sage.py:667` | `sage_logout()` | **DELETE-IF** | No in-repo callers. Same caveat — manual debug helper? |

### 1.2 Python — unread instance attributes

These are `self.foo = ...` assignments that nothing ever reads. Same precedent as the V3-era `self._known_ids` cleanup.

| File:Line | Attribute | Decision | Reason |
|---|---|---|---|
| `boost_manager.py:71` | `self._last_activate_time` | **DELETE** | Written on activation, never read. |
| `boost_manager.py:72` | `self._last_refresh_time` | **DELETE** | Written on refresh, never read. |
| `bot_loop.py:190` | `self._last_loop_time` | **DELETE** | Written every loop, never read for logic, status, or logging. |
| `bot_loop.py:287` | `self._coin_watcher_polls` / `self._coin_watcher_changes` | **DELETE** | Two counters incremented in the watcher; nothing reads them. (If you wanted these for runtime telemetry, that's a feature add — but right now they're write-only.) |
| `coin_prep_worker.py:289` | `self.xch_consolidate_threshold` / `self.cat_consolidate_threshold` | **DELETE** | Loaded from env in `__init__`, never used afterward. The consolidation logic uses different config keys. |
| `coinset_client.py:69` | `self._last_success_time` | **DELETE** | Updated on success, never consumed for backoff or telemetry. |
| `tray_manager.py:75` | `self.app_version` | **DELETE-IF** | Constructor stores it, no tray/menu/status path reads it. **Keep if you intend to put the version in the tray tooltip — that's a tiny feature add worth doing instead.** |

### 1.3 Python — unread module-level constants

| File:Line | Symbol | Decision | Reason |
|---|---|---|---|
| `spacescan.py:46` | `_FREE_MONTHLY_BUDGET` | **DELETE-IF** | Constant declared, never read. **Possibly intended for a future quota check — verify you're not relying on it appearing in code review.** |

### 1.4 Python — unused imports

These are imports at the top of a file that import a name nothing in the file references.

| File:Line | Import(s) | Decision | Reason |
|---|---|---|---|
| `api_server.py:67` | `get_tier_distribution`, `get_weighted_tier_prep_counts` from `coin_manager` | **DELETE** | Neither name is referenced in `api_server.py`. |
| `bot_loop.py:38` | `init_database` | **DELETE** | Not used in `bot_loop.py`. |
| `bot_loop.py:66` | `classify_offers_from_list`, `cancel_offer` | **DELETE** | Not used in `bot_loop.py`. |
| `coin_prep_worker.py:50` | `ThreadPoolExecutor`, `as_completed` | **DELETE** | Not used. |
| `coin_prep_worker.py:55` | `get_fee_coin_size_xch`, `get_fee_pool_count` | **DELETE** | Not used. |
| `offer_manager.py:23` | `update_offer_coin_id`, `update_offer_lifecycle_state` | **DELETE** | Not used in `offer_manager.py`. |
| `offer_manager.py:28` | `is_offer_time_expired`, `get_offer_expiry_info`, `WALLET_ID_XCH` | **DELETE** | Not used in `offer_manager.py`. |

### 1.5 Database — dead tables

| File:Line | Table | Decision | Reason |
|---|---|---|---|
| `database.py:240` | `diagnostic_snapshots` (full table + columns: `phantoms`, `orphans`, `status_mismatches`, `amount_mismatches`, `issue_summary`, `wallet_audit_ok`) + index at `database.py:260` | **DELETE** | Table is created and indexed but no code anywhere INSERTs, SELECTs, or UPDATEs it. Pure schema cruft. |
| `database.py:175` | `config_history` table | **DELETE-IF** | Written via `INSERT INTO config_history` at `database.py:3300`, but no reads. **If you ever want to ship a "config history viewer" in the GUI, you'll want to keep this. If you don't, the writes are a pointless write amplification.** |

### 1.6 Config keys — loaded but never read

| File:Line | Key | Decision | Reason |
|---|---|---|---|
| `config.py:168` | `SAGE_DATA_DIR` | **DELETE-IF** | In `config.py`, `.env`, and `.env.example`, but no runtime code reads it. **Sage's data directory is auto-detected; this was probably a manual override that's no longer wired in. Verify before removing from `.env.example`.** |
| `config.py:265` | `COIN_PREP_COOLDOWN_SECS` | **DELETE-IF** | Loaded into config, no consumers. **If you intended cooldown semantics for coin prep, this is a missing feature, not dead code.** |
| `config.py:307-309` | `ENABLE_MEMPOOL_WATCH`, `MEMPOOL_POLL_INTERVAL_SECS` | **DELETE** | Both loaded but neither consumed. Looks like an unfinished mempool-watcher feature. The `mempool_watcher.py` module exists but isn't wired to these config keys. |
| `config.py:375` | `BUY_INNER_TIER_SPARE_COUNT` | **DELETE** | Dead fallback — `INNER_TIER_SPARE_COUNT` is always evaluated first (config.py:382), so this branch never fires. |
| `config.py:455` | `BOOST_EXPIRY_SECS` | **DELETE-IF** | Exposed in config/example, but `boost_manager.py` never reads it. **Possibly the boost logic was rewired to use a different key — verify before deletion.** |
| `.env.example:93` | `MAX_MID_MOVE_BPS` | **DELETE** | Decision log says: "MAX_MID_MOVE_BPS was never consumed by trading code and was removed from config + GUI" (2026-04-08). The line in `.env.example` is the last orphan. |
| `.env.example:257-258` | `OFFERPOOL_ENABLED`, `OFFERPOOL_API_URL` | **DELETE** | Offerpool was removed (see `prune_fingerprints` comment in market_intel.py). Only referenced in `test_all_apis.py`, not core bot code. |

### 1.7 HTML / CSS / JS in `bot_gui.html`

#### 1.7.1 Duplicate JS function definitions — **DELETE EARLIER COPIES IMMEDIATELY**

These are the most dangerous finding in the whole audit. Verified by direct grep — three definitions of each, only the last runs at runtime, the earlier ones are silently dead:

| Line | Function | Decision | Reason |
|---|---|---|---|
| `bot_gui.html:12835` | `function lcApplySpread()` | **DELETE** | Shadowed by line 13056. Editing this copy has zero runtime effect — a real footgun. |
| `bot_gui.html:12903` | `function lcApplySpread()` | **DELETE** | Shadowed by line 13056. |
| `bot_gui.html:13056` | `function lcApplySpread()` | **KEEP** | This is the live one. |
| `bot_gui.html:12870` | `function lcApplySkew()` | **DELETE** | Shadowed by line 13140. |
| `bot_gui.html:13089` | `function lcApplySkew()` | **DELETE** | Shadowed by line 13140. |
| `bot_gui.html:13140` | `function lcApplySkew()` | **KEEP** | This is the live one. |

#### 1.7.2 Explicitly-named legacy functions

| Line | Function | Decision | Reason |
|---|---|---|---|
| `bot_gui.html:17164` | `legacy_updateCoinPrepPreview_unused` | **DELETE** | Suffix says it all. |
| `bot_gui.html:25383` | `legacy_checkIfCoinPrepNeeded_unused` | **DELETE** | Suffix says it all. |
| `bot_gui.html:25935` | `legacy_showCoinPrepConfirm_unused` | **DELETE** | Suffix says it all. |

#### 1.7.3 Removed-feature leftovers

| Line | Symbol | Decision | Reason |
|---|---|---|---|
| `bot_gui.html:14787` | `initSetupGuideBanner()` | **DELETE** | Comment at line 7685 says the `#setupGuideBanner` element was removed on 2026-04-06. This function and the two below it now no-op against a missing DOM node. |
| `bot_gui.html:14824` | `updateSetupGuideBannerSteps()` | **DELETE** | Same — orphan after banner removal. |
| `bot_gui.html:14912` | `dismissSetupGuideBanner()` | **DELETE** | Same — orphan after banner removal. |
| `bot_gui.html:3743` | `.fingerprint-box` CSS class | **DELETE** | Defined, not applied to any element. |
| `bot_gui.html:3756` | `.fingerprint-label` CSS class | **DELETE** | Defined, not applied to any element. |
| `bot_gui.html:3764` | `.fingerprint-value` CSS class | **DELETE** | Defined, not applied to any element. |

#### 1.7.4 Stale CSS classes (bulk)

A separate Claude pass flagged **~331 CSS class definitions in `bot_gui.html` that have zero usages**. The Codex pass independently confirmed `.fingerprint-*` (above). The full list is too long to enumerate, but it's a single bulk-cleanup task.

| Decision | Reason |
|---|---|
| **DELETE-IF** (bulk task — needs careful verification) | These accumulated across V2→V3→V4 visual rewrites. Before bulk-deleting, run a careful re-check for dynamic class application: `class="${cond ? 'foo' : 'bar'}"` patterns and `classList.add(varName)` patterns will not be caught by a static grep. Recommendation: tackle this in one focused session with a JS-aware tool (e.g. PurgeCSS) rather than ad-hoc deletion. |

#### 1.7.5 Orphan DOM IDs (~46)

Sample (the rest follow the same pattern):

| Line | ID | Decision | Reason |
|---|---|---|---|
| `bot_gui.html:6977` | `pairSwitchOverlay` | **DELETE-IF** | No JS reads it. **Verify the `<div>` with this id isn't a placeholder for a planned feature.** |
| `bot_gui.html:6981` | `pairSwitchTitle` | **DELETE-IF** | Same. |
| `bot_gui.html:6982` | `pairSwitchSubtitle` | **DELETE-IF** | Same. |
| `bot_gui.html:6983` | `pairSwitchPill` | **DELETE-IF** | Same. |
| `bot_gui.html:7682` | `dataFreshnessIndicator` | **DELETE-IF** | `display:none`, no JS shows it. |
| `bot_gui.html:7863` | `tokenSnapshotBar` | **DELETE-IF** | `display:none`, never referenced. |
| `bot_gui.html:7878` | `snapshotDescWrap` | **DELETE-IF** | `display:none`, never referenced. |
| `bot_gui.html:7883` | `snapshotWebsiteWrap` | **DELETE-IF** | `display:none`, never referenced. |
| `bot_gui.html:7947` | `consoleWarningBanner` | **DELETE-IF** | Defined, never referenced in JS. |
| `bot_gui.html:7966` | `alertBadge` | **DELETE-IF** | Defined, never referenced in JS. |

(...plus ~36 more — same bulk-cleanup approach as 1.7.4.)

### 1.8 Filesystem — backup / scratch directories (delete locally; verify gitignore)

| Path | Size | Decision | Reason |
|---|---|---|---|
| `backups_pre_fix_20260407/` | **45 MB** | **DELETE** (and add to `.gitignore`) | Contains: 5 source `.bak` files, your live `bot.db` (43 MB), and a `bot_superlog_20260407_174250.log`. **Currently NOT gitignored** — `git add -A` would commit the live database publicly. This is the #1 pre-publish blocker. |
| `_archive/` | 644 KB | **DELETE** | Already gitignored, but clutters the working tree. |
| `tmp_db_debug_ea6wvfjs/` | small | **DELETE** | SQLite scratch dir, gitignored, no longer needed. |
| `tmp_db_reconcile_7reuflpo/` | small | **DELETE** | Same. |
| `bot_data.db` (root) | 0 bytes | **DELETE** | Empty file, gitignored. |

### 1.9 Documentation — files referenced but missing

This isn't strictly "code to delete" — it's text in `CLAUDE.md` to delete (or files to restore):

| File:Line | What | Decision | Reason |
|---|---|---|---|
| `CLAUDE.md:7-10` | "READ THESE FIRST" links to `DESKTOP_MIGRATION_PLAN.md`, `DESIGN_SPEC.md`, `CODEBASE_AUDIT.md` | **DELETE the references** (or restore the files) | All three files are missing from the repo. The instruction file's headline guidance is broken. |
| `CLAUDE.md:185` (file-tree section) | Lists `tests/`, `V2_PLAN.md`, `v1_retrospective.md`, `SAGE_WALLET_RESEARCH.md` | **DELETE the references** | None of these exist any longer. Tests live as `test_*.py` in the root, not in `tests/`. |
| `sage_docs/SAGE_V4_MISMATCH_REPORT.md` (~17 occurrences) | Broken markdown links: `[wallet_sage.py](. Monkeyzoo\chia_liquidity_bot_v2\v4\wallet_sage.py)` | **REWRITE the links** | Personal local-machine paths from when the doc was originally written. Either fix to relative repo paths or strip the link wrappers. |
| `sage_docs/SAGE_V4_PATCH_CHECKLIST.md` (~14 occurrences) | Same broken-link pattern | **REWRITE the links** | Same fix. |

---

## Part 2 — Full audit findings

### Summary

| | Findings |
|---|---|
| Pass A — Dead code (high confidence) | ~75 |
| Pass B — Pre-publish hygiene | ~20 |
| **Critical pre-publish blockers** | **5** |

**Critical pre-publish blockers (must fix before going public):**
1. `backups_pre_fix_20260407/` (45 MB) is **not gitignored**. Contains live `bot.db` and superlog.
2. `user_paths.py` is **untracked but is a runtime import** in `config.py:34`, `database.py:50`, `desktop_app.py:91`, `api_server.py:271`. Publishing the current tracked set would break the app on clone.
3. `sage_docs/SAGE_V4_MISMATCH_REPORT.md` and `SAGE_V4_PATCH_CHECKLIST.md` contain ~30 broken markdown links with personal local-machine paths (`. Monkeyzoo\chia_liquidity_bot_v2\v4\…`).
4. `CLAUDE.md` references three "READ THESE FIRST" docs that no longer exist (`DESKTOP_MIGRATION_PLAN.md`, `DESIGN_SPEC.md`, `CODEBASE_AUDIT.md`) plus three more in the file-tree section.
5. Six duplicate JS function definitions in `bot_gui.html` (3× `lcApplySpread`, 3× `lcApplySkew`) — not security-critical but a hidden footgun: editing the wrong copy has no effect.

### Pass A — Dead Code

#### A1 — Unreferenced functions / methods / classes

(See Part 1 §1.1 above. Verified: all listed functions appear only at their definition with no callers in `.py`, `bot_gui.html`, or `app_bridge.py`.)

#### A2 — Unread instance attributes

(See Part 1 §1.2 above.)

#### A3 — Unread module-level constants

(See Part 1 §1.3 above.)

#### A4 — Unused imports

(See Part 1 §1.4 above.)

#### A5 — Unreachable branches

**No findings.** No `if False:`, no `if 0:`, no code after unconditional `return`/`raise` in scoped production files.

#### A6 — Commented-out code blocks

**No findings.** The codebase has plenty of explanatory comments but no large blocks of commented-out Python.

#### A7 — Stale TODO / FIXME / XXX / HACK

| File:Line | Marker | Comment | Stale? |
|---|---|---|---|
| `api_server.py:1971` | TODO | "Move to /api/dashboard and cache; /api/status should be read-only." | **No** — still describes valid future work. |

Only one TODO marker found. None reference items from the CLAUDE.md decision log.

#### A8 — Database columns / tables with no live use

(See Part 1 §1.5 above.)

#### A9 — Database event types: emitted / consumed mismatches

These are concrete name mismatches between Python emitters and the GUI/SSE consumer. **All five are bugs** — events are being lost in transit because the names don't match.

| Event Type | Emitter | Consumer (expects) | Severity |
|---|---|---|---|
| `pnl_matched` | `bot_loop.py:3314` (also in `event_taxonomy.py:146`) | `bot_gui.html:21400`, `21558` look for `pnl_match` (no `d`) | **Bug** — pnl-matched events never reach the GUI |
| `gap_closer_activated` | `boost_manager.py:188` | `bot_gui.html:21584` looks for `gap_closer_start` | **Bug** — gap-closer activations never reach the GUI |
| `offers_created` | (no Python emitter) | `bot_gui.html:21562` formats it | **Dead consumer** — formatter handles a string nothing emits |
| `sniper_fill` | (no Python emitter) | `bot_gui.html:21580` formats it | **Dead consumer** |
| `wallet_unhealthy` / `wallet_recovery` | (no Python emitter) | `bot_gui.html:21620` formats both | **Dead consumer** |

**On top of those specific cases**, an earlier pass also flagged:
- **~25 events listed in `event_taxonomy.py` that are never emitted anywhere** (`bot_health_topup_recovered`, `chia_recovered`, `config_validated`, `cycle_complete`, `fill_verified`, `known_ids_pruned`, `price_found`, `offer_cancelled`, `offer_created`, `reconcile_direct_link`, `recovery_mode_enter`, `recovery_mode_exit`, `requote_cancel_failed_stop`, `reservation_acquired`, `reservation_released`, `sage_change_address_set`, `sage_fill_backfill`, `spacescan_fill_confirmed`, plus ~7 more).
- **~178 event_type strings emitted by `log_event(...)` calls that are not in `event_taxonomy.py`** (sample: `amm_monitor_start`, `amm_buffer_guard`, `amm_drift_detected`, `cat_resolver_applied`, `api_error`, `batch_upsert_commit_failed`, `buy_offer_mojo_calc_failed`, etc.).

**Net finding:** `event_taxonomy.py` has drifted from being a contract to being aspirational documentation. Either enforce it (add a unit test that fails on mismatch) or rename it to make clear it's not authoritative.

#### A10 — HTML/CSS/JS dead weight in `bot_gui.html`

(See Part 1 §1.7 above.)

#### A11 — Duplicate / near-duplicate functions

In addition to the JS duplicates in §1.7.1 (which are critical), the audit also flagged three Python near-duplicates across the wallet adapters:

| File:Line | Symbol(s) | Confidence | Notes |
|---|---|---|---|
| `wallet_chia.py:1401` vs `wallet_sage.py:3852` | `prepare_coins_for_trading` | Low | Same name and same high-level multi-step prep workflow exist in both wallet adapters. These are intentional — one per backend. **KEEP** unless you decide to refactor wallet.py to mediate. |
| `wallet_chia.py:725` vs `wallet_sage.py:3948` | `prepare_coins_for_offers_v2` | Low | Same pattern. **KEEP**. |
| `wallet_chia.py:1292` vs `wallet_sage.py:2791` | `cancel_offers_batch` | Low | Same — duplicated across backends with diverging verification details. **KEEP**. |

#### A12 — Dead config keys

(See Part 1 §1.6 above.)

### Pass B — Pre-Publish Review

#### B13 — Secrets / credentials / personal data

| File:Line | What | Severity | Resolved? |
|---|---|---|---|
| `.env:13-14` | Working tree `.env` contains `C:\Users\t_you\…` Sage cert paths | **LOW** (was flagged HIGH by Codex) | **Resolved** — `.env` is gitignored (verified `git check-ignore -v .env` → matches `.gitignore:7`). It will not ship via git. ⚠️ But: if you ever publish via tarball/zip rather than git push, this leaks. |
| `.env:28` | Live `CAT_ASSET_ID` in working tree `.env` | **LOW** | Same — gitignored. |
| `bot.db` (root) | Live SQLite database with fills, offers, events | **LOW** (was flagged Critical by Codex) | **Resolved** — gitignored via `*.db` rule. But: same tarball-vs-git caveat, **and** `bot.db` is also sitting inside `backups_pre_fix_20260407/` which is **NOT gitignored** (see B14). That second copy is the real risk. |
| `sage_docs/SAGE_V4_MISMATCH_REPORT.md` | ~17 broken links with personal `. Monkeyzoo\…\v4\…` paths | **HIGH** | **Not resolved.** These files ARE tracked by git. |
| `sage_docs/SAGE_V4_PATCH_CHECKLIST.md` | ~14 broken links with personal `. Monkeyzoo\…\v4\…` paths | **HIGH** | **Not resolved.** Same. |
| `CLAUDE.md:23` | `"If Tim's stated goal conflicts…"` — first-name leak in instruction file | **LOW** | Cosmetic. |
| `api_server.py:6881` | `# Tim's mental model:` comment | **LOW** | Cosmetic. |
| `git log --diff-filter=A` history scan | No `.env` / `.key` / `.pem` / `wallet*.json` ever committed in history | **None** | ✓ Clean history. |
| `xch1...` address scan | Only the well-known null address `xch1qqqqqqqq...s0wd5zg` and test placeholders found in tracked source | **None** | ✓ No real wallet addresses leaked. |
| Fingerprint scan | Only `1234567890`-style placeholders in mocks, tests, and docs | **None** | ✓ No real fingerprints leaked. |

#### B14 — `.gitignore` completeness

| Gap | Severity | Notes |
|---|---|---|
| `backups_pre_fix_*/` not covered | **CRITICAL** | `.gitignore:64` has `_backups/` (with leading underscore). The actual directory is `backups_pre_fix_20260407/`. 45 MB of source backups + your live `bot.db` + a superlog are currently untracked but **commit-able**. **Add `backups_pre_fix_*/`.** |
| No generic `*.bak` rule | HIGH | If the `backups_pre_fix_*/` rule is added, this is moot — but defense in depth is cheap. |
| `venv/` and `.venv/` not covered | Medium | If a contributor creates a venv, it'll be untracked-but-committable. |
| `.vscode/` (whole dir) not covered | Medium | Only `.vscode/settings.json` is gitignored at line 78. Workspace-specific files would still ship. |
| `super_log_*.txt` not covered | Low | `.gitignore:34` has `bot_superlog_*.log` but not `super_log_*.txt` if such a variant ever shows up. |

#### B15 — README presence and accuracy

| Issue | Line | Severity |
|---|---|---|
| Placeholder URL: `git clone https://github.com/your-username/chia-market-maker.git` | `README.md:36` | LOW |

Otherwise the README is accurate, has install + run instructions, and includes an appropriate "no warranty" disclaimer. ✓

#### B16 — License file

| Issue | Severity |
|---|---|
| `LICENSE` is MIT (good). Copyright holder is `Tim` (first name only). | LOW (cosmetic, but a public repo with `Copyright (c) 2026 Tim` looks unfinished. Replace with full legal name or "MonkeyZoo".) |

#### B17 — Documentation drift

| Issue | File | Severity |
|---|---|---|
| Three "READ THESE FIRST" docs missing: `DESKTOP_MIGRATION_PLAN.md`, `DESIGN_SPEC.md`, `CODEBASE_AUDIT.md` | `CLAUDE.md:7-10` | **HIGH** |
| File-tree section lists `tests/` (doesn't exist — tests live as `test_*.py` in root), `V2_PLAN.md`, `v1_retrospective.md`, `SAGE_WALLET_RESEARCH.md` (all missing) | `CLAUDE.md:185+` | **HIGH** |
| Personal local-machine paths in sage_docs (already listed under B13) | sage_docs/ | HIGH |

#### B18 — Backup files / scratch directories / untracked core files

| Path | Severity | Action |
|---|---|---|
| `backups_pre_fix_20260407/` (45 MB, contains live `bot.db`) | **CRITICAL** | Gitignore + delete locally |
| `backups_pre_fix_20260407/api_server.py.bak` (and 4 sibling .bak files) | **HIGH** | Same |
| `tmp_db_debug_ea6wvfjs/`, `tmp_db_reconcile_7reuflpo/` | Medium | Already gitignored, delete locally |
| `_archive/` (644 KB) | Medium | Already gitignored, delete locally |
| `user_paths.py` is **untracked but a runtime import** in `config.py:34`, `database.py:50`, `desktop_app.py:91`, `api_server.py:271` | **CRITICAL** | **Must `git add user_paths.py` before publish or the cloned repo will fail to import.** |
| `installer.iss` is untracked | Medium | Verify intent — if you ship the installer, this should be committed. |
| `splash.html` is untracked | Low | Verify intent before committing. |
| `PRE_RELEASE_CHECKLIST.md`, `TEST_SHEET.md` are untracked | Low | Both look intentional, ready to commit. |

#### B19 — Stray `print()` statements in production paths

Verified counts (I re-grepped):

| File | print() count | Severity |
|---|---|---|
| `wallet_sage.py` | **140** | Medium |
| `api_server.py` | **122** | Medium |
| `bot_loop.py` | **55** | Medium |
| `desktop_app.py` | **46** | Medium |

**Caveat:** Many of these are in CLI entry points (`desktop_app.py`, `doctor.py`-style helpers) and startup paths where `print()` is the only available channel before logging is initialized. But the wallet_sage and api_server counts include error paths that should be going through `log_event()`. Specific examples worth fixing first:

- `wallet_sage.py:652` — fingerprint mismatch error (silent print, not in event log)
- `wallet_sage.py:678` — logout error
- `wallet_sage.py:2275-2289` — cancel_offer HTTP errors (404 / 500 / 202 paths)
- `api_server.py:835` — `[STARTUP] CAT metadata resolve failed` (error path masquerading as startup info)

#### B20 — Bare excepts and silent error swallows

**Distinction:** The CLAUDE.md style guide forbids bare `except:`. There are **zero true bare excepts** in the codebase. ✓

But the **silent-swallow pattern** `except Exception: pass` is rampant. Verified counts:

| File | `except Exception: pass` count | Severity |
|---|---|---|
| `api_server.py` | **128** | High |
| `database.py` | **65** | High |
| `bot_loop.py` | **37** | High |
| `wallet_sage.py` | **22** | High |
| `desktop_app.py` | ~21 | High |
| `sage_node.py` | ~20 | High |

These are technically not bare excepts (they catch a specific class), but the `: pass` makes them functionally equivalent: errors disappear silently. For trading-engine code that risks masking config bugs and data-corruption errors. **This is the largest hardening opportunity in the project.**

#### B21 — Hardcoded magic numbers in trading logic

Combined from both passes (sample, not exhaustive):

| File:Line | Number | Likely config name | Severity |
|---|---|---|---|
| `risk_manager.py:244` | 1.5 | `MIN_SPREAD_MULTIPLE_OF_EDGE` | Medium |
| `risk_manager.py:335` | 0.8, 0.5 | `VOL_SCALE_FLOOR`, `VOL_SCALE_OFFSET` | Medium |
| `risk_manager.py:421-426` | 0.05/0.20/0.30/1.20 | `POSITION_IMPACT_THRESHOLDS` (4-band ladder) | Medium |
| `risk_manager.py:432` | 2.0 | `MAX_VOL_MULTIPLIER` | Medium |
| `risk_manager.py:644` | 1.5 | `HARD_POSITION_LIMIT_SCALE` | Medium |
| `risk_manager.py:899, 903` | 0.9 | `SOFT_POSITION_WARN_PCT` | Medium |
| `risk_manager.py:1046` | 0.05 | `POOL_DEPTH_THRESHOLD_BPS` | Medium |
| `fill_tracker.py:84` | 8 | `_spacescan_per_cycle_cap` | Medium |
| `fill_tracker.py:100` | 5 events/hour | silent-loss alert policy | Medium |
| `fill_tracker.py:108` | 600s | silent-loss alert cooldown | Medium |
| `fill_tracker.py:306` | 600 | `GUARD_TIMEOUT_SECS` | Medium |
| `coin_manager.py:73` | 600/300/3600 | top-up/backoff timing constants | Medium |
| `offer_manager.py:2202` | 25, 5.0 | `BATCH_SIZE`, `BASE_BATCH_DELAY` | Medium |
| `boost_manager.py:655` | 60 | hardcoded offset to `GAP_CLOSE_STEP_COOLDOWN` | Medium |

#### B22 — Inconsistent error handling

Largely overlaps with B20 (silent swallows). Specific spot-checks worth fixing:

| File:Line | Pattern |
|---|---|
| `coin_manager.py:867-868` | `except Exception: sniper_size = Decimal("0")` — silent default with no logging |
| `coin_manager.py:1504-1505` | Logs warning on reserve-creation failure but returns `None` silently |
| `offer_manager.py:487-488` | `except Exception: return 1` — silently defaults to serial mode |
| `offer_manager.py:491-492` | `except Exception: configured = 5` — silently defaults to 5 |

#### B23 — Side-effect-only imports

**No findings.** The known side-effect imports (`super_log_hooks`) have explanatory comments.

#### B24 — File and function size outliers

**Files over 3000 lines:**

| File | Lines |
|---|---|
| `api_server.py` | **10,696** |
| `bot_loop.py` | **6,529** |
| `coin_prep_worker.py` | **5,450** |
| `coin_manager.py` | **4,979** |
| `wallet_sage.py` | **4,066** |
| `database.py` | **4,020** |

**Functions over 200 lines (top 10):**

| File:Line | Function | Lines |
|---|---|---|
| `api_server.py:6085` | `_calculate_smart_defaults` | **1,662** |
| `bot_loop.py:2809` | `_run_one_cycle` | **1,632** |
| `coin_prep_worker.py:2112` | `create_and_split_tier_pools_sage` | **1,379** |
| `bot_loop.py` | `_retire_probe_offers` | ~1,007 |
| `bot_loop.py:1988` | `_startup_sync` | **816** |
| `api_server.py:1953` | `api_status` | **812** |
| `bot_loop.py` | `_fire_probe` | ~711 |
| `api_server.py` | `_solve_base` | ~645 |
| `coin_prep_worker.py` | `run_full_preparation` | ~614 |
| `wallet_sage.py` | `cancel_offers_batch` | ~528 |

These are flagged for human review only. Any function ≥1000 lines is essentially a god-function and is hard to test in isolation.

#### B25 — Test coverage gaps for critical paths

| Module (lines) | Test file(s) | Status |
|---|---|---|
| `price_engine.py` (922) | **NONE** | **CRITICAL** — zero dedicated tests. Indirect references in `test_amm_monitor.py` and others, but no direct coverage of oracle aggregation, weighted average, safety guards, dynamic limits, volatility window. This is the price oracle every order is sized off. |
| `risk_manager.py` (1,079) | `test_risk_manager_snapshot.py` (32 lines) | **CRITICAL** — 1 test only. Missing: position-limit checks, circuit-breaker logic, `should_enable_side`, rail-breach handling, all spread-adjustment paths. |
| `fill_tracker.py` (1,441) | `test_fill_tracker_verification.py` (189 lines) | Limited — ~13% test ratio. The new `silent_loss_rate_exceeded` alert path and the `fills.trade_id` UNIQUE-index race-recovery branch are not visibly tested. |
| `coin_manager.py` (4,979) | 4 files (~497 lines) | ~10%. Tests cover topup and snapshots; the 493-line `_two_step_split` and 449-line `_amount_matches_target` are not visibly tested. |
| `offer_manager.py` (2,782) | `test_offer_manager_coin_ids.py` (873 lines) | ~31% — best of the critical modules. Missing: requote-side logic, batch-cancellation edge cases. |
| `wallet_sage.py` (4,066) | 5 files (~428 lines) | ~11%. The 528-line `cancel_offers_batch` has only ~65 lines of test coverage. Wallet-sync failure recovery untested. |
| `bot_loop.py` (6,529) | 3 files (~1,042 lines) | ~16%. The 1,632-line `_run_one_cycle` is only tested in probe/recovery modes. Side enable/disable interactions under errors are not visibly tested. |

**Worst gap:** `price_engine.py` has zero direct tests.

---

## Recommendations

### Pre-publish blockers (must fix before going public): **5**

1. **Add `backups_pre_fix_*/` to `.gitignore`** and verify with `git status` that the directory is gone from "untracked files". (45 MB of backups + your live `bot.db` are at risk of being committed.)
2. **`git add user_paths.py`** — it's a runtime import in 4 modules but currently untracked. The cloned repo would fail to import without it.
3. **Fix the broken markdown links in `sage_docs/SAGE_V4_MISMATCH_REPORT.md` and `sage_docs/SAGE_V4_PATCH_CHECKLIST.md`** — ~30 occurrences of personal `. Monkeyzoo\chia_liquidity_bot_v2\v4\…` paths.
4. **Update `CLAUDE.md`** — either restore the missing "READ THESE FIRST" docs (`DESKTOP_MIGRATION_PLAN.md`, `DESIGN_SPEC.md`, `CODEBASE_AUDIT.md`) or remove the references. Same for the file-tree section listing `V2_PLAN.md`, `v1_retrospective.md`, `SAGE_WALLET_RESEARCH.md`.
5. **Delete the 4 shadowed JS function definitions in `bot_gui.html`** (12835, 12903, 12870, 13089). Only the last copy of each runs, but the earlier copies are silent footguns when someone tries to edit them.

### Strongly recommended before publish: **4**

6. Fix the 5 event-name mismatches in §A9 (`pnl_matched` vs `pnl_match`, `gap_closer_activated` vs `gap_closer_start`, `offers_created`/`sniper_fill`/`wallet_unhealthy`/`wallet_recovery` are dead consumers). These are real bugs — events are being lost.
7. Replace the worst `print()` calls in `wallet_sage.py:652-2289` with `log_event()`. These are error paths bypassing the SQLite event log.
8. Replace `Tim` in `LICENSE` with a full legal/entity name.
9. Replace the `your-username` placeholder in `README.md:36`.

### Cleanup wins (high-confidence, safe to delete after a quick verification): **~30**

(All listed in Part 1 above with `DELETE` decisions. The biggest single win is removing the ~20 unused functions/methods/attributes in §1.1 and §1.2 — they total a few hundred lines of code that no path can reach.)

### Worth a closer look (low confidence — needs judgment): **~12**

10. The ~331 unused CSS classes and ~46 orphan DOM IDs in `bot_gui.html` — bulk cleanup, but needs a proper check for dynamic class application.
11. `event_taxonomy.py` is significantly out of sync (~25 dead entries, ~178 emitted-but-not-listed events). Pick a direction: enforce as a contract, or rename to make clear it's documentation.
12. **Six files over 3000 lines** — the worst is `api_server.py` at 10,696 lines. The 1,662-line `_calculate_smart_defaults` and 1,632-line `_run_one_cycle` functions need to be broken up to be testable.
13. **`price_engine.py` has zero tests.** Most critical untested module in the project — every order is sized off this. (Not blocking publish; blocking confidence.)
14. **`risk_manager.py` has one 32-line test.** Circuit-breaker logic is essentially untested.
15. **The silent-swallow pattern** `except Exception: pass` is rampant (~290+ instances across the top files). Not a publish blocker, but the largest hardening opportunity.
16. **17 hardcoded magic numbers in `risk_manager.py`** — circuit-breaker thresholds that should be tunable.
17. The **9 silent error fallbacks** in `coin_manager.py`, `offer_manager.py`, `wallet_sage.py` (specific lines in §B22) — they mask config bugs.
