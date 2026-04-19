# Spawn queue — Slice 01-06

---

## Queue

- [ ] **Refactor `_calculate_smart_defaults` (CC=460)** — single 1500-line function in
  api_server.py that computes all Smart Settings output. High CC from sequential parallel
  data transformations. Should be split into sub-functions by logical phase (spread calc,
  coin prep sizing, capital plan, etc.). Requires comprehensive test coverage first.
  - File: api_server.py:6937
  - Severity: low (works correctly; complexity is maintenance risk)
  - Prerequisite: Layer 2 unit tests for smart_defaults

- [ ] **Refactor `BotLoop._run_one_cycle` (CC=321)** — main trading loop step-by-step
  orchestrator. High CC from 20+ numbered steps each with error guards. Consider breaking
  into phase methods (_step_coincheck, _step_requote, etc.) while keeping the linear flow
  visible at the top level.
  - File: bot_loop.py:3544
  - Severity: low
  - Prerequisite: Layer 2/3 integration tests for the trading cycle

- [ ] **Refactor `CoinManager._two_step_split` (CC=132)** — coin splitting with multiple
  wallet-type branches (Sage RPC / Chia CLI), absorb-misfit logic, and failure fallbacks.
  A reasonable extraction target for the Sage / Chia dispatch.
  - File: coin_manager.py:5302
  - Severity: low

---

## Dispatched

(none)
