# Findings — Slice 02-01

Unit test expansion for `bot_loop.py` — cycle orchestrator, gates, timer logic.

---

## Existing coverage (before this slice)

19 tests across 3 files:
- `test_bot_loop_sage_status_mapping.py` — `map_sage_terminal_offer_status()`
- `test_bot_loop_probe_anchor.py` — probe anchor timing/linger/maturation
- `test_bot_loop_recovery_mode.py` — recovery mode state machine

---

## Functions added coverage for

| Function | Category | Tests |
|----------|----------|-------|
| `_bps_to_pct` | Pure formatting | 6 |
| `BotLoop._get_live_offer_edges` | Static, offer edge extraction | 6 |
| `BotLoop._extract_open_offer_ids` | Offer classification | 6 |
| `BotLoop._probe_hold_seconds_remaining` | Timer math | 3 |
| `BotLoop._probe_has_matured` | Timer gate | 2 |
| `BotLoop._probe_cleanup_seconds_remaining` | Linger countdown | 4 |
| `BotLoop._confirmed_probe_slot_offsets` | Slot math | 4 |
| `BotLoop._apply_probe_retry_backoff` | Retry step logic | 5 |
| `BotLoop._get_sniper_launch_reason` | Rearm decision | 4 |
| `BotLoop._get_probe_price_boundary` | Guard calculation | 5 |

**45 new tests** in `tests/test_plan_02_01_bot_loop_unit.py`.

---

## Functions NOT covered (intentionally skipped)

High-I/O or threading methods that can't be unit-tested safely:
- `start()`, `stop()`, `_run_loop()`, `_run_one_cycle()` — live wallet/DB/threads
- All background thread workers — infinite loops + sleep
- `_watch_active_probe_window()` — internal polling loop
- `_startup_sync()` — wallet sync + DB reset

These are Layer 3 integration test territory.

---

## No bugs found — documentation slice only

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 0 | blocked |
