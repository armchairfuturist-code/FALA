---
type: task
labels: [wayfinder:task]
blocked_by: []
assigned_to: closed
---

## Question

`mypy .` reports **13 errors, all in `progress.py`** — concentrated in `parse_vocabulary` and `update_vocab_after_review`. The pattern: vocab entries are typed as `dict[str, str]` but the code overwrites fields with `float` (ease), `int` (interval), `bool` (needs_review). The dict annotation says `str`, the values aren't. This is a real type-safety lie: a reader (or a future refactor) thinks `vocabulary[i]["ease"]` is a `str` when it's a `float`. Fix the typing so mypy passes — likely widening the entry dict to `dict[str, Any]` or `dict[str, str | float | int | bool]`, and checking whether the str-default-then-overwrite pattern in `parse_vocabulary` is masking a parse fragility (see map's "Not yet specified" on corruption recovery).

## Acceptance

- [ ] `mypy .` exits 0 (zero errors) on the whole project.
- [ ] `audio.py:161` whisper import error handled (add `# type: ignore[import-not-found]` or a stub, since whisper is optional).
- [ ] No runtime behavior change — pure typing fix. All 59 tests stay green.
- [ ] If `parse_vocabulary`'s overwrite pattern reveals actual parsing weakness (e.g. a malformed line silently typed wrong), note it in the resolution and feed it to the "Not yet specified" corruption-recovery fog.
- [x] `pytest tests/ -v` green; `ruff check .` green.

## Resolution

13 mypy errors resolved across 2 files:

- **`progress.py`**: Added `VocabEntry = dict[str, Any]` type alias, updated all 7 `list[dict]` signatures to `list[VocabEntry]`. Added `from __future__ import annotations` + `from typing import Any`. The `GUARDRAILS` inference bleed (`int|float` → `int|None`) fixed by wrapping assignment in `int(...)`.
- **`audio.py:161`**: Added `# type: ignore[import-not-found]` to the optional `import whisper`.

Mypy: 0 errors · Ruff: clean · Tests: 59/59 passing · No runtime changes.

**Parse fragility noted (feeds "Not yet specified" corruption-recovery fog):** `_parse_vocab_entry` does bare `float(parts[1])` / `int(parts[2])` with no try/except — a malformed `vocabulary.md` line throws `ValueError` with no recovery path. The typing fix masks this at the type level but the runtime fragility remains.
