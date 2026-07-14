---
type: task
labels: [wayfinder:task]
blocked_by: []
assigned_to: closed
---

## Question

`progress.py::vocabulary_report()` ships to users (`/stats` mid-session + session-end report) but has **zero direct tests**. It loads `data/pt_50k.txt`, maps each vocab word to a CEFR band by frequency rank, and returns the report string. If the frequency file format drifts, the rank thresholds change, or an empty/word-not-in-list path breaks, no test catches it. Add real coverage.

## Acceptance

- [x] Test: empty vocabulary → report says 0 total_words, empty cefr, zero stats.
- [x] Test: words at each CEFR band boundary (rank <500 → A1, <2000 → A2, <5000 → B1, else B2+) assert the right band.
- [x] Test: a word not present in `pt_50k.txt` is handled (not crashed, not mislabeled).
- [x] Test: SRS stats portion (mature words avg confidence, due-for-review count) is exercised.
- [x] All new tests pass; `pytest tests/ -v` stays green; no ruff/mypy regressions.

## Resolution

4 tests added mocking `_load_frequency_words`: empty, CEFR boundary bands (A1/A2/B1/B2+), unknown-word B2+ fallback, and SRS maturity/stats. 65 tests green, ruff clean.
