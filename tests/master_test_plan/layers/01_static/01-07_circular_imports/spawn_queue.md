# Spawn queue — Slice 01-07

---

## Queue

- [ ] **`database ↔ super_log` deferred cycle — consider decoupling** — The cycle
  is functional but means database.py and super_log.py each know about the other.
  A cleaner approach would be a `log_event` protocol/interface that both depend on
  instead of each other. Low priority since current approach works.
  - Discovered at: AST import graph
  - Severity: low (architectural smell, not a bug)
  - Suggested slice: future architecture refactor

---

## Dispatched

(none)
