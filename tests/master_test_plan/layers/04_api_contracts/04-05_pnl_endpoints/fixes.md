# Fixes — Slice 04-05

No production bugs found. One test-side correction:

`test_lowercase_reset_not_accepted` was wrong: the handler calls `.strip().upper()` on the confirm value, making the check case-insensitive. Renamed to `test_confirm_case_insensitive` and updated assertion to 200.
