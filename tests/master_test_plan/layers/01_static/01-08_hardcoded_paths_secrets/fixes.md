# Fixes — Slice 01-08

No fixes needed. No secrets or hardcoded paths found in version-controlled production files.

---

## Lessons / gotchas

- Dev utility scripts (`check_status.py`, `qdb*.py`, etc.) contain hardcoded tokens and
  user-specific paths, but all are gitignored — no production risk.
- `user_secrets.py` is a purpose-built secrets store that keeps API keys out of both the
  repo and the install directory entirely.
- TibetSwap URL inconsistency (6 direct hardcodes vs `cfg.TIBET_API_BASE`) is a
  configuration consistency issue, not a security issue.
