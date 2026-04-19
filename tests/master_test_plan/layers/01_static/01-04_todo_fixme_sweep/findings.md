# Findings — Slice 01-04

Baseline: 1 real TODO comment across all *.py + *.html source (excluding build/dist).
No FIXME, XXX, or HACK comments. 0 stale comments; 0 current bugs.

---

## Finding F1: single TODO — pricing logic in /api/status (real future work)

**Check:** 2.2 · **Severity:** low · **Status:** logged in tech_debt.md

`api_server.py:2127` — comment asks to move TibetSwap + Dexie price fetches
from `/api/status` (polled every 5 s) to `/api/dashboard` (page-load only).
Not a bug; existing behaviour works. Logged as TD-001 in `docs/tech_debt.md`.

No code change needed this slice. Comment is a legitimate architectural note
(kept in place).

---

## Closed findings tallied here

| Count | Status |
|-------|--------|
| 0 | open |
| 0 | fixed |
| 1 | logged as tech debt (TD-001) |
| 0 | blocked |
