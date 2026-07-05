---
type: task
labels: [wayfinder:task, wayfinder:closed]
blocked_by: []
---

## Question

The SRS feedback loop is disconnected — `update_vocab_after_review()` and `save_learning_record()` are defined and tested in `progress.py` but never imported or called from `conversation.py`. Words are added at `confidence=0.3` and never graduate. The `conversation.py` module needs to:

1. Import and call `update_vocab_after_review()` after each user turn, feeding the LLM's assessment back into the SRS
2. Decide *when* and *how* to assess words
3. Import and call `save_learning_record()` at appropriate points (e.g. when a word reaches confidence >= 0.8)

## Resolution

**Approach:** Per-turn assessment. Modified `_extract_vocab_from_exchange()` to request a JSON object (`{"new_words": [...], "assessments": [...]}`) from the LLM instead of a plain array. Assessment entries feed `update_vocab_after_review()` per turn. At session end, `save_learning_record()` is called for any new words that reached confidence >= 0.8.

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Imports `update_vocab_after_review` and `save_learning_record` | ✅ |
| 2 | SRS feedback called per user turn | ✅ (via `_extract_vocab_from_exchange`) |
| 3 | Existing tests pass | ✅ (52 pass) |
| 4 | New integration tests | ✅ (4 new: assessment processing, wrong-answer reset, graduated records, no-graduation edge case) |

**Facts for future tickets:**
- Extraction prompt changed from returning `[...]` to `{"new_words": [...], "assessments": [...]}`
- `update_vocab_after_review()` mutates vocabulary entries in-place (confidence, ease, interval, last_reviewed, needs_review)
- `save_learning_record()` writes markdown files to `data/records/`
- 56 tests total now (52 original + 4 new)
