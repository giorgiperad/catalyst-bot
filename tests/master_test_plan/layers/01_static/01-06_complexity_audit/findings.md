# Findings — Slice 01-06

radon 6.0.1, `cc --min C --exclude tests,tools,backups,dist,build` on production code.

Totals: 4085 A | 715 B | 550 C | 162 D | 103 E | 129 F

Maintainability index C (lowest grade): api_server.py, bot_loop.py,
coin_manager.py, coin_prep_worker.py, database.py, fill_tracker.py

No actionable bugs found. All complexity is in well-understood, large
orchestrator functions. Logged in tech_debt.md as TD-005 through TD-009.

---

## Top 10 most complex functions (production code only)

| Rank | CC | Grade | File | Function |
|------|----|-------|------|----------|
| 1 | 460 | F | api_server.py:6937 | `_calculate_smart_defaults` |
| 2 | 321 | F | bot_loop.py:3544 | `BotLoop._run_one_cycle` |
| 3 | 211 | F | api_server.py:2109 | `api_status` |
| 4 | 182 | F | bot_loop.py:2682 | `BotLoop._startup_sync` |
| 5 | 146 | F | coin_prep_worker.py:4950 | `CoinPrepWorker.run_full_preparation` |
| 6 | 138 | F | offer_manager.py:1311 | `OfferManager.create_ladder` |
| 7 | 132 | F | coin_manager.py:5302 | `CoinManager._two_step_split` |
| 8 | 107 | F | coin_manager.py:3961 | `CoinManager._topup_worker` |
| 9 | 104 | F | bot_loop.py:6334 | `BotLoop._handle_housekeeping` |
| 10 | 90 | F | api_server.py:10141 | `api_settings_validate` |

---

## Closed findings tallied here

| Count | Status |
|-------|--------|
| 0 | open bugs |
| 0 | fixed |
| 10 | logged as tech debt (TD-005 – TD-009) |
| 0 | blocked |
