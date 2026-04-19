# Fixes — Slice 01-04

No code fixes needed. The single TODO in the codebase is a legitimate
architectural note (real future work, not stale). It was logged in
`docs/tech_debt.md` as TD-001 instead.

---

## Lessons / gotchas

- Build artefacts in `build/` contain `_distutils_hack` in HTML — exclude
  `build/` and `build2/` from future grep patterns alongside `dist/`.
- The `xxx` in `api_server.py:12672` is a literal JSON example value
  (`{"api_key": "xxx"}`), not a comment marker.
- One TODO in ~50 kloc is unusually clean. The codebase uses `# Fx` prefixed
  comments instead (e.g. `# F49 (2026-04-09):`) to reference work items.
