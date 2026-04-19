# Spawn queue — Slice 01-08

---

## Queue

- [ ] **Use `cfg.TIBET_API_BASE` in 6 hardcoded `api_server.py` locations** — Lines 2139,
  2442, 6236, 6432, 6471, 6661 all call `https://api.v2.tibetswap.io/pairs` directly instead
  of `f"{cfg.TIBET_API_BASE}/pairs"`. Behaviour is identical at the default URL, but a user
  running against a testnet or alternative endpoint would be silently ignored on these paths.
  - Severity: low (config consistency)
  - Prerequisite: none

- [ ] **Centralise Flask port in `api_server.py` `__main__`** — Lines 12787 and 12868 duplicate
  the `5000` constant. Consider importing `FLASK_PORT` from `desktop_app` or defining the
  constant in a shared location.
  - Severity: cosmetic
  - Note: these are `__main__` run paths only (standalone mode); low priority.

---

## Dispatched

(none)
