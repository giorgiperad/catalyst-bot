# Fixes — Slice 01-06

No code fixes. Complexity is documented in docs/tech_debt.md (TD-005 – TD-009).
Refactoring these functions is out-of-scope for a static analysis slice — each
is a large orchestrator that would require its own dedicated slice with regression
test coverage as a prerequisite.

---

## Lessons / gotchas

- radon CC grades: A=1-5, B=6-10, C=11-15, D=16-25, E=26-50, F=51+
- `_calculate_smart_defaults` (CC=460) is a single massive function computing
  all Smart Settings output in one pass. It contains ~1500 lines of sequential
  data transformation. High CC but low branching risk — most paths are
  independent parallel computations.
- `BotLoop._run_one_cycle` (CC=321) is the main trading loop. It's intentionally
  flat (step-by-step) rather than decomposed — decomposing it would hide the
  overall flow. The high CC comes from many small guards and side-effect
  branches, not from deep nesting.
- Both of the above are known design decisions. Refactoring them is a major
  undertaking requiring extensive test coverage first.
