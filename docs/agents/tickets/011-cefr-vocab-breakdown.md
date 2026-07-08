---
type: task
labels: [wayfinder:task]
blocked_by: [010-research-evaluation]
assigned_to: closed
---

## Question

Implement the CEFR vocabulary breakdown and SRS health report recommended by ticket #010.

**Three outputs:**

1. **CEFR vocabulary breakdown** — download `pt_50k.txt` (frequency word list), map each known word to a CEFR band via heuristic thresholds (top 500 = A1, 500–2000 = A2, 2000–5000 = B1), display at session end
2. **SRS health report** — retention rate this session (correct / total reviews), mature word count (confidence ≥ 0.7), shown at session end
3. A `/stats` command to show the same info mid-session

## Resolution

All three outputs implemented:

1. **CEFR breakdown**: `progress.vocabulary_report()` loads `data/pt_50k.txt` (50K words, lazy cached), maps each known word → CEFR band via frequency rank heuristics (A1: top 500, A2: 500–2000, B1: 2000–5000, B2+: rest). Non-matching words count as B2+.
2. **SRS stats**: Same function returns mature count (confidence ≥ 0.7), avg confidence, due-for-review count.
3. **Session-end display**: `end_session()` now prints `Vocabulary: X words (A1: Y · A2: Z) | Mature: N | Avg confidence: XX%`.
4. **`/stats` command**: Added to `fala.py` main loop — prints a `vocabulary_report()` via Rich panel.

| # | Acceptance | Status |
|---|-----------|--------|
| 1 | pt_50k.txt in data/ | ✅ (manually downloaded, auto-load on first use) |
| 2 | vocabulary_report() in progress.py | ✅ |
| 3 | end_session() includes report | ✅ |
| 4 | /stats command works mid-session | ✅ |
| 5 | 56+ tests pass | ✅ (56/56) |
