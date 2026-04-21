# Partial Offers (CHIP-0052) design docs

This folder bundles the design, reference, and planning material for the CHIP-0052 partial-offers integration. **Nothing here is live code.** The implementation has not yet landed. See `.claude/skills/catalyst-partial-offers/SKILL.md` for the full integration skill.

| File | Purpose |
|------|---------|
| `PARTIAL_OFFERS_PLAN.md` | Complete integration plan, phased build order |
| `CATalyst_Partial_Offers_Build_Prompts.docx` | Build-session prompts per phase |
| `Chia_Partial_Offers_Reference.docx` | CHIP-0052 reference material |
| `PHASE1_SESSION_PROMPT.md` | Phase-1 kickoff prompt (standalone session starter) |

When the implementation lands (`partial_offer_manager.py`, `partial_fill_tracker.py`, `partial_coin_monitor.py`, `OFFER_MODE` feature flag, DB schema), it goes in the project root. These docs stay here as the design record.
