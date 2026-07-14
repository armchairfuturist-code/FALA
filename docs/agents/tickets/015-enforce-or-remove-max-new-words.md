---
type: grilling
labels: [wayfinder:grilling]
blocked_by: []
assigned_to: closed
---

## Question

`config.py` defines `max_new_words_per_session = 5` as a "guardrail" — but it is **referenced nowhere** in `conversation.py` or `progress.py`. The vocab-extraction prompt is told to cap at 5 words (a *prompt hint*), but nothing in code enforces it. If the LLM ignores the hint and returns 20 words, all 20 get added. Is `max_new_words_per_session` a guardrail (enforce it in code: truncate `new_words` to the cap before `add_vocabulary`) or a vestigial config value (remove it and rely on the prompt)? This is a decision — the answer shapes whether the cap is trustworthy or aspirational.

## Resolution

Grilling decision: **Enforce in code** — the user chose trust over dead-config cleanup. `conversation.py` now truncates `data.get("new_words", [])` to `GUARDRAILS["max_new_words_per_session"]` (5) before iterating. GuardRAILS widened in signature (mixed int/float) handled implicitly by the return type. Mypy 0 errors, 59 tests green, ruff clean.

## Acceptance

- [x] Decision recorded: enforce in code.
- [x] Code path: `_extract_vocab_from_exchange` in `conversation.py` — `new_words_raw = data.get("new_words", [])[:max_new]`.
- [x] Dead config removed: no — config stays as the single source of truth for the cap value.
- [x] Resolution comment on this ticket names the decision and its rationale (this section).
