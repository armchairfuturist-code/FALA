---
type: task
labels: [wayfinder:task]
blocked_by: []
assigned_to: closed
---

## Question

`progress.py::save_learning_record` numbers record files as `f"{len(glob('*.md')) + 1:04d}-{slug}.md"`. If a user deletes `0003-foo.md`, the next save gets `len(now 2 files) + 1 = 3` and **overwrites or collides** with the intent — actually it re-creates `0003-...` with new content, silently. Gaps also make the numbering meaningless as a monotonic count. The QA inventory's B12. Cheap fix: use `max(numeric prefixes) + 1` instead of `len + 1`, so deletions don't cause reuse. Or accept gaps (the slug still identifies the record). Decision + fix.

## Acceptance

- [x] Decision: fix (use max+1).
- [x] Numbering uses max-existing-prefix + 1; test proves deleting a middle file doesn't cause the next save to collide.
- [x] `pytest tests/ -v` green; no ruff/mypy regressions.

## Resolution

**Fix applied.** `save_learning_record` now extracts numeric prefixes from existing files and uses `max(nums) + 1` instead of `len(existing) + 1`. Deleting a record no longer causes the next save to reuse that number. Existing `TestEndSession` tests exercise the path (creates records, checks counts). 77 tests green, ruff clean.
