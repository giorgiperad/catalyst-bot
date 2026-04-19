# Spawn queue — Slice 01-05

---

## Queue

- [ ] **~108 mypy annotation gaps in 6 core modules** — 65 `[assignment]` (None
  defaults for str params should be `Optional[str]`), 17 `[arg-type]`, 8 `[operator]`,
  8 `[index]`, etc. None are bugs; all are annotation style issues. Worth a dedicated
  pass to add `Optional[...]` annotations throughout, which would make mypy strict-mode
  viable.
  - Discovered at: mypy run across config.py, database.py, wallet.py, fill_tracker.py,
    risk_manager.py, price_engine.py
  - Why out-of-scope here: 108 annotation gaps; needs a full dedicated session
  - Severity: low (annotation quality, not correctness)
  - Suggested slice: add new slice 01-09 "Optional annotation sweep — database.py + core"

- [ ] **`price_engine._update_reference_price`: `self._reference_price` typed as
  `Optional[Decimal]` but multiplied without None check in the nudge path** — mypy
  flags `price_engine.py:857` as `Decimal * None`. At runtime this is safe because
  `get_dynamic_limits()` returns `(None, None)` when `_reference_price is None`, so the
  `if dyn_min is not None` guard prevents the multiply. But mypy can't prove this indirect
  relationship. Type narrowing comment or explicit guard would silence it cleanly.
  - Discovered at: `price_engine.py:857, 879`
  - Why out-of-scope here: no real runtime risk; requires careful type annotation
  - Severity: low
  - Suggested slice: 01-09

- [ ] **`database.py`: `cursor.lastrowid` used as `int` without None guard** —
  `cursor.lastrowid` is `int | None`. Multiple places call `int(cursor.lastrowid)` which
  raises `TypeError` if `None`. In practice an INSERT always sets lastrowid, but mypy
  is correct that it's theoretically possible.
  - Discovered at: `database.py:3090`
  - Why out-of-scope here: not a real runtime issue; needs annotation review
  - Severity: low
  - Suggested slice: 01-09

---

## Dispatched

(none)
