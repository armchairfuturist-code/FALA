# Conversation UX Research — Best Practices for LLM Language Tutoring

> Research for ticket #009 — reviewing and improving FALA's conversation prompts.

## Sources consulted

| Source | Key takeaway |
|--------|-------------|
| **Praktika AI** (multi-agent tutor, 30M+ users) | Gentle in-flow correction, adjustable tone, multi-agent architecture, 15min daily sessions |
| **Talkpal** (10M+ users, 130+ languages) | Mode-based structure (dialogue, roleplay, debate, call), real-time corrections, pronunciation assessment |
| **Maurya et al. (2025)** — 8-dimension pedagogical taxonomy | Do NOT reveal the answer; ensure actionability; maintain encouraging tone |
| **Beale (2025)** — Dialogic Pedagogy for LLMs | Socratic prompting, ZPD scaffolding, retrieval practice, structured + unstructured dialogue |
| **Liu et al. (2026)** — Teacher-Authored Prompts | "No direct answers" guardrails reduce answer-giving by 8.5pp; explicit finish lines improve outcomes |
| **Lin-Zucker et al. (2025)** — CEFR Level Targeting | Include level-appropriate vocabulary lists to constrain LLM output |
| **Zhang et al. (2024)** — RAISE model | Repetitiveness, Authenticity, Interactivity, Student-Centeredness, Enjoyment |

## Key findings applied to FALA

### 1. Error correction: gentle in-flow, never reveal the answer
Praktika's pattern: *"My dog likes to swim in the beach" → "I see your pet enjoys swimming in the sea."* — correction embedded naturally, not flagged as failure. Academic research confirms: "do NOT reveal the answer" is the single most important guardrail.

### 2. Session structure: warm-up → practice → free talk → wrap-up
Both Praktika and Talkpal use structured phases. FALA already has this shape but the LLM doesn't get a clear boundary signal between warmup and free conversation.

### 3. Pronunciation feedback conditional on voice input
The `[voice]` prefix is already passed to the LLM but the prompt doesn't tell it to use this flag to decide whether to give pronunciation feedback.

### 4. Name as a teaching moment, not a form field
Don't prompt for name upfront. Have the tutor ask "Como te chamas?" naturally in Portuguese as the first interaction.

### 5. Vocabulary level constraints
The LLM should be told which words are appropriate for the learner's current level (A1/A2/B1) and which have been learned.

## Changes applied

### prompts/system.md
- Replaced "use learner's name occasionally if known" → tutor asks name in Portuguese naturally
- Added **do NOT reveal the answer** guardrail
- Pronunciation feedback now conditional on `[voice]` prefix
- Added Praktika-style gentle in-flow correction examples
- Strengthened session phase boundaries
- Added level-appropriate vocabulary constraint

### prompts/warmup.md
- Made review count adaptive (3-5 → "a few")
- Added retrieval practice framing
- Added explicit transition signal to free conversation
