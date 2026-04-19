# Fixes — Slice 02-19

No production code fixes needed.

---

## Test corrections

- Attempted `patch("fill_classifier.cfg", ...)` for arb-hash and puzzle-hash tests.
  This fails because `cfg` is imported inside the function (`from config import cfg`)
  and does not exist at module level. Correct patch target is `config.cfg`.
  Fixed all 4 affected tests to use `patch("config.cfg", fake_cfg)`.
