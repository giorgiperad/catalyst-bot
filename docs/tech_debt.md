# Tech Debt Log

Items that are real future work but not urgent enough to fix immediately.
Seeded by audit slice 01-04 (2026-04-19). Add new items with file:line and
brief context so a future session can pick them up cold.

---

## TD-001: Move pricing logic out of `/api/status`

**File:** `api_server.py:2127`
**Discovered:** 2026-04-19, slice 01-04

`/api/status` is polled every 5 seconds by the GUI. When `bot` is None
(pre-start state), the endpoint runs live TibetSwap + Dexie price lookups
inline. This causes unnecessary wallet RPC contention on every poll and
makes the endpoint non-idempotent.

The comment at line 2127 correctly identifies the fix: move the pricing
fetch to `/api/dashboard` (called once on page load) and cache the result.
`/api/status` should only return lightweight read-only state.

**Impact:** low (only affects pre-bot startup display, not trading logic)
**Effort:** medium (need to add a cache layer and update frontend JS)

---

## TD-002: `reaction_strategy.CycleBudget` — defined but never instantiated

**File:** `reaction_strategy.py:45`
**Discovered:** 2026-04-19, slice 01-03 (spawn queue)

`CycleBudget` is a fully-implemented dataclass that caps per-cycle action
budgets (cancels, creates, requotes). It is never imported or used by any
caller. The `docs/CODEBASE_AUDIT_REPORT.md` lists it as a "key symbol",
suggesting it was intended for future use.

Decision needed: wire it into the requote/cancel flow, or delete it.

**Impact:** none (dead code)
**Effort:** small to delete; medium to wire in

---

## TD-003: `coin_manager._split_via_cli` — 100-line dead method

**File:** `coin_manager.py` (method `_split_via_cli`, ~line 2579)
**Discovered:** 2026-04-19, slice 01-03 (spawn queue)

`_two_step_split` inlined the CLI coin-split logic and stopped calling
`_split_via_cli`. The method has zero callers. A comment at ~line 5704
references it by name but does not call it.

**Impact:** none (dead code, ~100 lines of clutter)
**Effort:** small (remove method + check for any dynamic dispatch)

---

## TD-004: `coin_manager._diff_coin_snapshots` — dead in both files

**File:** `coin_manager.py:5865`, `coin_prep_worker.py:2273`
**Discovered:** 2026-04-19, slice 01-03 (spawn queue)

Identical method defined in both modules, never called in either. Was likely
used during early two-step-split development.

**Impact:** none (dead code)
**Effort:** trivial (delete both copies)
