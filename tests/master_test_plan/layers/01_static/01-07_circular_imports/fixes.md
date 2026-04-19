# Fixes — Slice 01-07

No fixes needed. No true module-level circular imports found.

---

## Lessons / gotchas

- The AST-based full import graph shows 241 "potential" cycles, but all are
  deferred (inside function bodies). These don't cause import errors.
- Filter to `tree.body` (top-level statements only) to get true circular import
  risk. Everything at function body level is safe.
- pydeps can generate import graphs visually but requires graphviz. The AST
  approach is sufficient for correctness checking.
