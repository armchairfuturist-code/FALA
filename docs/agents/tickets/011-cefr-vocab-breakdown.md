---
type: task
labels: [wayfinder:task]
blocked_by: [010-research-evaluation]
assigned_to: ""
---

## Question

Implement the CEFR vocabulary breakdown and SRS health report recommended by ticket #010.

**Three outputs:**

1. **CEFR vocabulary breakdown** — download `pt_50k.txt` (frequency word list), map each known word to a CEFR band via heuristic thresholds (top 500 = A1, 500–2000 = A2, 2000–5000 = B1), display at session end
2. **SRS health report** — retention rate this session (correct / total reviews), mature word count (confidence ≥ 0.7), shown at session end
3. A `/stats` command to show the same info mid-session

## Acceptance

1. `pt_50k.txt` auto-downloads into `data/` on first use (or clear error if download fails)
2. `progress.py` has a `vocabulary_report(vocabulary)` function returning CEFR breakdown + SRS stats
3. `end_session()` output includes the report
4. A `/stats` command works mid-session
5. 56+ tests pass
