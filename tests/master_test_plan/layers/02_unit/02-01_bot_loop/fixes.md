# Fixes — Slice 02-01

No production code fixes needed. All tested functions behave correctly.

---

## Test correction

- `test_string_input` for `_bps_to_pct("100")` initially expected `"1.00%"` —
  corrected to `"1.0%"` (values ≥ 1 use one decimal place per the function's
  formatting branch).
