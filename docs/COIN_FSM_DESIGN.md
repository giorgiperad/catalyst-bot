# Coin Lifecycle Finite-State Machine — Design Doc

**Status:** design only (Phase 6 of the 2026-04-17 permanent refactor).
A minimal `validate_transition` helper is implemented in `coin_fsm.py` but
**is not yet hooked into any DB-write path** — it is callable by tests but
not wired into production code. Originally this doc claimed the helper was
hooked at `update_coin_status()` / `set_coin_designation()`; that was
aspirational. `update_coin_status` does not exist as a function (status is
updated inline at ~12 SQL sites in `database.py`), and `set_coin_designation`
performs a raw UPDATE with no FSM call. Wiring is tracked as a follow-up.
Full replacement of the current status+designation model is deferred until
after CHIP-0052 partial offers land, because partial offers change the coin
model substantially.

---

## Why formalise the state machine

The live bot has ~8 functions that read coin state and ~6 that write it. The transitions between states are implicit — any caller can set `status='locked'` without a rule saying "the coin must have been in `free` first." This has produced subtle bugs:

- **Zombie locks** — a `locked` coin whose `trade_id` no longer exists. Produced when a cancel race leaves the DB marking a coin locked but the offer has already been removed.
- **Phantom inventory** — coin appears in `_xch_inventory["inner"]` but its DB row says `status='spent'`. Happens when in-memory inventory isn't rebuilt after a spend.
- **Misfit drift** — coin designated `tier_spare/inner` by reconcile but classified as misfit by the absorber. (Fixed by the SSOT classifier in Phase 1.)

Making the FSM explicit means every transition must pass validation, and the set of allowed transitions is enforced at the DB-write boundary.

---

## States

The current codebase uses two orthogonal columns on the `coins` table:

- `status`: `free | locked | spent | gone`
- `designation`: `reserve | tier_spare | tier_active | dust | unknown | sniper | fees`

Rather than replacing these, the FSM is a **composite state** — the pair `(status, designation)` — with validation applied at the transition layer. The current rows don't change; only the set of allowed *transitions* is formalised.

The composite states we actually see (not every combination is legal):

| State | Meaning |
|---|---|
| `(free, unknown)` | Just-seen new coin, not yet classified |
| `(free, tier_spare)` | Free, sized for a tier, selectable for offers |
| `(free, reserve)` | Free, too big for any tier, used as topup fuel |
| `(free, dust)` | Free, too small for any tier, consolidation candidate |
| `(free, sniper)` | Free, sized for a sniper probe (distinct sizing) |
| `(free, fees)` | Free, sized for a fee coin |
| `(locked, tier_active)` | Locked, backing an active offer |
| `(locked, tier_spare)` | LEGACY — `tier_spare` should transition to `tier_active` on lock. Currently the bot sometimes leaves it as `tier_spare`. |
| `(spent, *)` | Coin was consumed on-chain (fill or consolidation). Designation preserved for history. |
| `(gone, *)` | Coin disappeared from wallet (external spend / prior-session carryover). |

Terminal states: `spent` and `gone`. Once a coin reaches either, its row should not be re-animated.

---

## Allowed transitions

```
                  ┌─────────────────────────────────────────────────┐
                  │                                                 │
  (new)           │                                                 │
    │             ▼                                                 │
    ├──────► (free, unknown)                                        │
    │             │                                                 │
    │             │  classify_coin() resolves designation           │
    │             ▼                                                 │
    ├──► (free, tier_spare) ──► (locked, tier_active) ──► (spent)  │
    │             │                        ▲                        │
    │             │    cancel              │                        │
    │             │◄───────────────────────┘                        │
    │             │                                                 │
    │             │    resize/reshape                               │
    │             ▼                                                 │
    ├──► (free, reserve) ──► (spent, reserve)  ── consolidate       │
    │             │                                                 │
    │    dust consolidation                                         │
    │             ▼                                                 │
    ├──► (free, dust)  ──► (spent, dust)  ── consolidate            │
    │                                                               │
    │    wallet snapshot                                            │
    └──────────────────────────────────────► (gone, *)              │
                                                                    │
         prep worker                                                │
         ────────────────► (free, sniper)   ── locked in probe      │
                                                                    │
         prep worker                                                │
         ────────────────► (free, fees)     ── reserved for fee     │
                                                                    │
    reanimation (wallet sees it again)                              │
    (gone, *) ────────────────────────────────► (free, prior desig) ┘
```

## Validation rules

1. `spent` and `gone` are terminal — no transition leaves them, EXCEPT `gone → free` when a coin reappears (rare, e.g. an uncommitted spend was reversed).
2. `locked` only transitions TO `free` (cancel / fill returned change) or `spent` (offer filled).
3. `tier_active` only appears with `locked` status.
4. `reserve` coins skip the `tier_spare` stage on split — a reserve coin is spent in a split TX, the outputs are new coins entering as `(free, unknown)`.
5. `unknown` is always a transient state — should resolve within one reconcile cycle.

---

## Why not do the full rewrite now

1. **CHIP-0052 (partial offers) arrives soon.** In the partial-offer model, a single on-chain coin can back *many* discrete offers simultaneously. The `locked ↔ free` binary breaks down. Forcing a clean FSM on top of the discrete-offer model and then throwing it away for the partial-offer model is wasted work.

2. **Current system works for the 99% case.** The bugs that the FSM would prevent (zombie locks, phantom inventory) already have detect-and-heal paths (`reconcile_with_wallet`, `orphan_cleanup`). They're imperfect but self-recovering.

3. **Risk of regression.** Moving the state machine to strict enforcement means every current code path that *does* an implicit transition becomes a failure. We'd spend days chasing false positives.

## What IS implemented

A lightweight validator — `coin_fsm.py::validate_transition(from_state, to_state)` — that returns True / False for whether a specific transition is currently allowed. The validator is **not yet wired into production code**. The intent is to hook it as a **non-blocking log-only check** at the coin-status and coin-designation write sites in `database.py`, logging disallowed transitions at WARN level while blocking nothing. Until that wiring lands, the module is exercised only by its unit tests (`tests/test_coin_fsm.py`) and gives no live-trading visibility.

Once the log shows clean behaviour for weeks, we can promote the validator from WARN-only to ERROR-blocking in a follow-up.

---

## Migration plan (future)

1. **Phase A (now):** Validator in place, WARN-only.
2. **Phase B (after 1 month of clean logs):** Promote validator to blocking. Any disallowed transition raises.
3. **Phase C (after CHIP-0052 ships):** Rewrite state model to reflect partial-offer semantics. Discrete-offer codepath retained behind `OFFER_MODE=standard` flag for backward compat.

---

**Last updated:** 2026-04-17
