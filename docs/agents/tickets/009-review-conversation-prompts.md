---
type: grilling
labels: [wayfinder:grilling]
blocked_by: []
assigned_to: ""
---

## Question

The conversation flow (warmup → free conversation → session end) works, but the quality depends entirely on the LLM prompts in `prompts/system.md` and `prompts/warmup.md`. What specific improvements should we make?

Current prompts have known rough edges:
- The system prompt tells the tutor to "use the learner's name occasionally" but no name is ever collected
- Pronunciation feedback instructions exist but the STT pipeline may not provide enough phonetic detail
- The warmup template is detailed but the LLM may skip steps under token pressure
- No prompt versioning — changing a prompt is a one-way door with no rollback

This ticket is a **grilling** session: review the prompts together, identify pain points, and decide what changes to make. The output is a concrete list of prompt edits or a decision to defer.

## Acceptance

1. Current prompts (`system.md`, `warmup.md`) reviewed and critiqued
2. Specific pain points identified (at least 3)
3. Concrete edits decided for each — either apply now or defer to a follow-up ticket
4. If edits are decided, they are applied in this session
