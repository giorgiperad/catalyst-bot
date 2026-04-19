# Spawn queue — Slice 01-03

Out-of-scope issues found during this slice.

---

## Queue

- [ ] **`coin_manager._split_via_cli` — zero callers, ~100-line dead method**
  - A full Sage-RPC / Chia-CLI coin-split implementation at `coin_manager.py:2579`.
    `_two_step_split` inlined the CLI parts and stopped calling this method. A comment
    at line 5704 references it by name but does not call it.
  - Discovered at: `coin_manager.py:2579` (vulture 60%, confirmed by grep)
  - Why out-of-scope here: large method removal — needs its own careful read + tests
  - Severity: low (dead code, no behaviour impact)
  - Suggested slice: add new slice 01-09 "coin_manager dead method removal"

- [ ] **`coin_manager._diff_coin_snapshots` — zero callers**
  - Defined in both `coin_manager.py:5865` and `coin_prep_worker.py:2273`. Neither copy
    is called anywhere in the codebase (confirmed by grep excluding `def` lines).
  - Discovered at: `coin_manager.py:5865`, `coin_prep_worker.py:2273`
  - Why out-of-scope here: duplicate-copy pattern — need to check git history for intent
  - Severity: low
  - Suggested slice: 01-09 (dead method removal)

- [ ] **`reaction_strategy.CycleBudget` — defined but never imported**
  - A full dataclass at `reaction_strategy.py:45` that tracks per-cycle action budgets.
    Only `RequoteSeverity` and helper functions are imported by callers. `CycleBudget`
    is documented in the module docstring and `docs/CODEBASE_AUDIT_REPORT.md` as a
    "key symbol" but is never instantiated.
  - Discovered at: `reaction_strategy.py:45`
  - Why out-of-scope here: potentially intended future feature; docs reference it
  - Severity: low
  - Suggested slice: 01-09 or a future "feature gap audit" slice

- [ ] **B007: 28 loop variables not used in loop body** — carried forward from 01-01
    spawn queue. Review intent (intentional iteration vs forgotten variable).
  - Discovered at: ruff B007, 28 occurrences
  - Suggested slice: 01-05 or dedicated style-cleanup slice

- [ ] **E712: 3 comparison-to-True/False** — carried forward from 01-01 spawn queue.
  - Discovered at: `api_server.py`, `bot_loop.py`
  - Suggested slice: 01-05 (type annotation audit)

---

## Dispatched

- ~~**F841: 18 non-auto-fixable unused local variables**~~ → fixed in this slice (01-03).
