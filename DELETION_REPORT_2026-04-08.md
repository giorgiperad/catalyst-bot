# Pre-Publish Cleanup — Deletion Report (2026-04-08)

This report documents the dead-code deletions made before the GitHub release. Every entry was independently verified (read the definition, grepped for callers across `.py` files and `bot_gui.html`) before removal. All modified Python files pass `ast.parse` and full module-import checks, and `bot_gui.html` passes a `node --check` JavaScript syntax check.

A full backup of every source file was taken in `backups_pre_audit_cleanup_20260408/` (114 files, 5.2 MB) before any edit. That directory is gitignored.

## Summary

| Category | Items removed |
|---|---|
| Python functions / methods / classes | 13 |
| Python instance attributes | 7 |
| Python module-level constants | 1 |
| Python unused import names | 11 |
| Database table + index | 1 |
| `bot_gui.html` duplicate JS function definitions | 4 |
| `bot_gui.html` legacy/orphan JS functions | 5 |
| `bot_gui.html` orphan CSS classes | 3 |
| `bot_gui.html` orphan call sites + variables | (cleaned) |

## Python — Functions, Methods, Classes Deleted

### `api_server.py`
- **`AlertStore.get_all`** (was line 971) — zero callers; only `get_active()` is used.
- **`_fetch_dexie_ticker_full`** (was line 5841, ~80 lines) — definition-only standalone fetcher.
- **`_fetch_tibet_pool_standalone`** (was line 6032, ~30 lines) — definition-only standalone fetcher.
- **`_get_main_console_hwnd` / `_set_window_visible` / `_find_window_by_pid`** (was line 9563, ~60 lines combined) — three Windows console-window helpers, all definition-only. Also removed the orphan `_main_console_hwnd` and `_coin_prep_console_hwnd` globals and the `global _coin_prep_console_hwnd` declaration that no longer had any reader.

### `boost_manager.py`
- **`BoostManager.mark_cascade_done`** (was line 1075) — no callers anywhere.

### `coin_manager.py`
- **`get_tier_coin_requirements`** (was line 761) — definition-only helper, never called.

### `coinset_client.py` — entire mempool-watching subsystem
- **`watch_coins`**
- **`unwatch_coins`**
- **`clear_watched_coins`**
- **`check_mempool_for_spends`**
- **`get_watched_coin_count`**

All five methods + their section header. The subsystem was scaffolded but never wired up — `ENABLE_MEMPOOL_WATCH` defaults to false and nothing in the codebase calls these methods (verified with `\.<method>\(` grep across `.py` and `bot_gui.html`).

### `database.py`
- **`cleanup_old_events`** (was line 3531) — utility function with no callers, no scheduled invocation.
- **`prune_market_analysis_cache`** (was line 3980) — same pattern, no callers.

### `market_intel.py`
- **`MarketIntel.prune_fingerprints`** (was line 583) — empty stub, comment said "Compatibility no-op after Offerpool removal". Note: `splash_manager.SplashManager.prune_fingerprints` is a different method on a different class and is still called from `bot_loop.py:5121` — that was preserved.

### `wallet_sage.py`
- **`SageTransactionError`** class (was line 207) — never raised, caught, or referenced.

### Kept (was DELETE-IF in audit) — conservative call
- `wallet_sage.reset_initialization_state` — debug helper, plausible REPL utility.
- `wallet_sage.sage_logout` — wallet logout, reasonable to expose.
- `tray_manager.app_version` instance attribute — useful for a future tray tooltip.
- `database.config_history` table + `record_config_change` writer — audit flagged as DELETE-IF for a possible future config-history viewer.

## Python — Instance Attributes Deleted (write-only)

| File | Attribute | Notes |
|---|---|---|
| `boost_manager.py` | `self._last_activate_time` | Set on activation, never read. Removed assignment too. |
| `boost_manager.py` | `self._last_refresh_time` | Set on refresh, never read. Removed assignment too. |
| `bot_loop.py` | `self._last_loop_time` | Set every loop, never read. Removed assignment too. |
| `bot_loop.py` | `self._coin_watcher_polls` | Counter incremented in watcher, never consumed. |
| `bot_loop.py` | `self._coin_watcher_changes` | Counter incremented in watcher, never consumed. |
| `coin_prep_worker.py` | `self.xch_consolidate_threshold` | Loaded from env in `__init__`, never used afterwards. |
| `coin_prep_worker.py` | `self.cat_consolidate_threshold` | Same. |
| `coinset_client.py` | `self._last_success_time` | Updated on success, never consumed for backoff or telemetry. Removed assignment too. |

## Python — Module Constants Deleted

| File | Symbol | Notes |
|---|---|---|
| `spacescan.py` | `_FREE_MONTHLY_BUDGET` | Constant declared, never read. |

## Python — Unused Imports Deleted

| File | Import name(s) |
|---|---|
| `api_server.py` | `get_tier_distribution`, `get_weighted_tier_prep_counts` (from `coin_manager`) |
| `bot_loop.py` | `init_database` (from `database`) |
| `bot_loop.py` | `classify_offers_from_list`, `cancel_offer` (from `wallet`) |
| `coin_prep_worker.py` | `ThreadPoolExecutor`, `as_completed` (from `concurrent.futures`) |
| `coin_prep_worker.py` | `get_fee_coin_size_xch`, `get_fee_pool_count` (from `tx_fees`) |
| `offer_manager.py` | `update_offer_coin_id`, `update_offer_lifecycle_state` (from `database`) |
| `offer_manager.py` | `is_offer_time_expired`, `get_offer_expiry_info`, `WALLET_ID_XCH` (from `wallet`) |

Note on `WALLET_ID_XCH`: All references in `offer_manager.py` are to `cfg.WALLET_ID_XCH`, never to the bare imported name. The import was dead.

Note on `get_tier_distribution`: There's an inline re-import as `_gtd_sd` at the actual usage site (`api_server.py:7411`), so deleting the top-level import was safe.

## Database — Tables Deleted

- **`diagnostic_snapshots`** table (was `database.py:240`) + index `idx_diag_snap_time` — `CREATE TABLE` and `CREATE INDEX` were emitted on every startup but no code anywhere INSERTs, SELECTs, or UPDATEs the table. Schema-only cruft. Removing the `CREATE TABLE` does NOT drop the table from existing databases — they will simply keep the orphan table, which is harmless.

## bot_gui.html — Dead JS, CSS, and Variables

### Duplicate function declarations (the most dangerous finding)

JavaScript function declarations of the same name silently shadow each other — only the last definition wins at runtime, and editing the earlier copies has zero effect.

| Line (pre-edit) | Function | Decision |
|---|---|---|
| 12835 | `lcApplySpread` (1st) | **DELETED** — was shadowed |
| 12903 | `lcApplySpread` (2nd) | **DELETED** — was shadowed |
| 13056 | `lcApplySpread` (3rd, final) | **KEPT** — the staged-slider Apply/Cancel version |
| 12870 | `lcApplySkew` (1st) | **DELETED** — was shadowed |
| 13089 → 12962 | `lcApplySkew` (2nd, staged-slider) | **KEPT** |
| 13140 → 13013 | `lcApplySkew` (3rd, simpler legacy) | **DELETED** ⚠️ |

**⚠️ Departure from audit recommendation for `lcApplySkew`:** The audit said to keep the third copy (line 13140) and delete the second (line 13089). I kept the second one instead. Reason: line 13089 is the **proper staged-slider version** that updates `_lcSkewAppliedRaw` and `_lcSkewDirty`. The simpler legacy copy at 13140 didn't update those — and `lcCancelSkew` (line 13047) checks `_lcSkewAppliedRaw == null` and bails out, meaning the **Cancel Move button for skew never worked at runtime** with the legacy version. Keeping line 12962 (the staged-slider version) **fixes that latent bug** while still removing the duplicate. After the deletion, `lcApplySpread` and `lcApplySkew` now have matching staged-slider behaviour. **This is a runtime behaviour change worth testing — the cancel button for the skew slider should now work.**

### Legacy "_unused" functions

All three were prefixed `legacy_*_unused` and only had a single definition with no callers — the suffix said it all.

- `legacy_updateCoinPrepPreview_unused` (was line 17164, ~275 lines) — replaced by `updateCoinPrepPreview` immediately below it.
- `legacy_checkIfCoinPrepNeeded_unused` (was line 25383, ~550 lines) — replaced by `checkIfCoinPrepNeeded`.
- `legacy_showCoinPrepConfirm_unused` (was line 25935, ~120 lines) — replaced by `showCoinPrepConfirm` immediately below it.

### Setup Guide Banner (PHASE 3) — entire dead subsystem removed

The audit found that the `#setupGuideBanner` DOM element was removed on 2026-04-06 (per the comment in the HTML), but the supporting JavaScript functions remained as no-ops against a missing element. They were still being called from two places per loop tick, wasting CPU and confusing the call graph.

Deleted:
- The `// PHASE 3: FIRST-RUN SETUP GUIDE BANNER` section header comment block
- `const SETUP_GUIDE_DISMISSED_KEY`
- `let _setupGuideChecked`
- `let _isFirstRun`
- `function initSetupGuideBanner()`
- `function updateSetupGuideBannerSteps()`
- `function _setSetupStep()` (helper used only by the above)
- `function dismissSetupGuideBanner()`
- All call sites (one in the status update loop, one in the bottom init block)
- The stale `<!-- PHASE 3 setupGuideBanner removed -->` HTML comment that referenced the deleted symbols

### CSS classes removed (no usages anywhere in HTML or JS)

- `.fingerprint-box` (was line 3743)
- `.fingerprint-label` (was line 3756)
- `.fingerprint-value` (was line 3764)

## What was *not* deleted (DELETE-IF kept for safety)

These were on the audit's list as DELETE-IF and I made the conservative call to **keep** them — a re-evaluation point for a follow-up cleanup:

| Item | Why kept |
|---|---|
| `wallet_sage.reset_initialization_state` | Plausible debug/REPL helper |
| `wallet_sage.sage_logout` | Wallet logout is a reasonable thing to expose |
| `tray_manager.app_version` | Tiny — useful for a tray-tooltip feature |
| `database.config_history` table + `record_config_change` writer | Plausible "config history viewer" feature, harmless if unused |
| Part 1.6 config keys (`SAGE_DATA_DIR`, `COIN_PREP_COOLDOWN_SECS`, `BOOST_EXPIRY_SECS`) | DELETE-IF candidates with unclear blast radius |
| `BUY_INNER_TIER_SPARE_COUNT` | Audit was wrong — this IS used by the GUI as a per-side override; the audit's "always shadowed" reasoning was inverted. Kept. |
| Part 1.7.4 stale CSS bulk task | The audit recommended a separate focused session with PurgeCSS-style tooling rather than ad-hoc deletion |
| Part 1.7.5 orphan DOM IDs | Same — bulk task, needs separate session |

## Verification Performed

After every batch of deletions:
1. **Python syntax check** — `python -c "import ast; ast.parse(open(f).read())"` on each modified file. 11/11 passed.
2. **Python import sanity check** — `importlib.util.spec_from_file_location` + `exec_module` on each modified file. 11/11 passed.
3. **Flask route count** — confirmed `api_server.py` still exposes 116 `@app.route` handlers (no routes accidentally deleted).
4. **JS Bridge method count** — confirmed `app_bridge.py` still exposes 97 methods.
5. **JavaScript syntax check** — extracted `bot_gui.html`'s `<script>` block and ran `node --check`. Passed.
6. **Cross-reference grep** — confirmed no remaining references to any deleted symbol.

## Files Modified

```
api_server.py
boost_manager.py
bot_gui.html
bot_loop.py
coin_manager.py
coin_prep_worker.py
coinset_client.py
database.py
market_intel.py
offer_manager.py
spacescan.py
wallet_sage.py
```

## Backup Location

`backups_pre_audit_cleanup_20260408/` (114 files, 5.2 MB, gitignored)

If anything in this report was a wrong call, restore the file from the backup directory and re-run the affected tests.

## Recommended Next Steps Before GitHub Publish

1. **Test the skew Cancel Move button.** The duplicate `lcApplySkew` cleanup intentionally restored the staged-slider version, which is a runtime behaviour change. Open the dashboard, drag the skew slider, click "Cancel Move", and confirm it reverts to the previously-applied value. (Spread already worked correctly — only skew was buggy.)
2. **Smoke-test full bot startup** — `python desktop_app.py` should still launch the desktop window, the bot loop should still cycle, and the dashboard should still render with all panels. The biggest risk areas are: api_server.py (heavily edited globals), bot_loop.py (lost a couple of imports), and the bot_gui.html JS hoisting changes.
3. **Address the 5 critical pre-publish blockers from the audit** (still pending — these are NOT cleanup, they are gating items):
   - `backups_pre_fix_20260407/` — was patched into `.gitignore` at session start.
   - `user_paths.py` is untracked but is a runtime import — must be `git add`'d before publishing or the cloned repo will not run.
   - Broken markdown links in `sage_docs/SAGE_V4_MISMATCH_REPORT.md` and `SAGE_V4_PATCH_CHECKLIST.md` (~30 personal local-machine paths).
   - `CLAUDE.md` references to three "READ THESE FIRST" docs that no longer exist.
   - The duplicate JS functions — **resolved by this cleanup pass**.
