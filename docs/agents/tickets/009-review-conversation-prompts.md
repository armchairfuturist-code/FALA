---
type: grilling
labels: [wayfinder:grilling]
blocked_by: []
assigned_to: closed
---

## Question

What does the latest research and practice say about LLM-based conversational language tutoring? How should FALA's prompts be redesigned based on evidence?

The current prompts work but were written without the benefit of research into how apps like Praktika, LangMagic, and Talkpal structure their tutoring conversations.

This ticket has two phases:
1. **Research**: investigate best practices for LLM-based language tutoring — prompt structure, error correction timing, scaffolding, session flow
2. **Apply**: rewrite `system.md` and `warmup.md` based on findings

## Resolution

Research completed and prompts rewritten based on findings.

**Research sources consulted (5):**
- Praktika AI (multi-agent tutor, 30M+ users) — gentle in-flow correction, adjustable tone
- Talkpal (10M+ users) — mode-based structure, real-time corrections
- Maurya et al. (2025) — 8-dimension pedagogical taxonomy
- Beale (2025) — dialogic pedagogy, ZPD scaffolding for LLMs
- Liu et al. (2026) — "no direct answers" guardrails reduce answer-giving by 8.5pp

**Changes to `prompts/system.md`:**
- Added "never reveal the answer directly" guardrail (the #1 finding from research)
- Changed name from form field → natural first-conversation question ("Como te chamas?")
- Pronunciation feedback now conditional on `[voice]` prefix
- Added Praktika-style gentle in-flow correction example
- Added level-appropriate vocabulary constraint
- Strengthened session phase boundaries with explicit transition signal
- Added retrieval practice framing

**Changes to `prompts/warmup.md`:**
- First session now includes natural name introduction in Portuguese
- Retrieval practice framing (prompt in English, answer in Portuguese)
- Pronunciation feedback conditional on voice input
- Added explicit transition to free conversation ("OK, let's just talk...")

**Assets:**
- `docs/research/conversation-ux.md` — full research summary
- `prompts/system.md` — rewritten (4.3KB)
- `prompts/warmup.md` — rewritten (1.3KB)

| # | Acceptance | Status |
|---|-----------|--------|
| 1 | Research summary covering >=3 sources | ✅ (5 sources) |
| 2 | Concrete changes to system.md and warmup.md | ✅ |
| 3 | Changes applied, committed, all tests pass | ✅ (56/56) |
