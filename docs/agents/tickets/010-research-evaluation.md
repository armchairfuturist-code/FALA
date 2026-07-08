---
type: research
labels: [wayfinder:research]
blocked_by: []
assigned_to: closed
---

## Question

How can FALA objectively measure a learner's progress over time? Currently the only feedback is the LLM's subjective session summary.

Consider:
1. **Existing tools** — how do language learning apps (Praktika, Duolingo, LingQ, Anki) measure progress beyond "words learned"?
2. **CEFR alignment** — can we map vocabulary knowledge to CEFR levels? Are there standardised word lists for A1/A2/B1 pt-PT?
3. **Conversation-derived metrics** — what can we extract from transcript data? (e.g., words attempted vs. correct, sentence complexity growth, speech rate)
4. **Structured assessment** — should FALA include periodic mini-assessments (e.g., "test session" every 10 sessions)?

## Resolution

Research at `docs/research/evaluation.md`. Surveyed Duolingo (IRT/ML proficiency score), Anki (SM-2 interval growth), LingQ (Known Words count), and CEFR-graded vocab for pt-PT.

**Recommendation:** Add three lightweight indicators using existing data:
1. CEFR vocabulary breakdown via `pt_50k.txt` frequency list (heuristic bands)
2. SRS health report (retention rate, mature word count)
3. Weekly trend from session logs

**Graduated:** Follow-up ticket #011 to implement the CEFR vocabulary breakdown + session-end display.

| # | Acceptance | Status |
|---|-----------|--------|
| 1 | Survey of >=3 approaches | ✅ (Duolingo, Anki, LingQ, CEFR) |
| 2 | Feasibility assessment | ✅ |
| 3 | Recommendation | ✅ |
| 4 | Follow-up ticket scoped | ✅ (#011) |
