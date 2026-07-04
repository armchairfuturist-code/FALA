---
type: task
labels: [wayfinder:task, wayfinder:claimed, wayfinder:closed]
blocked_by: [002-bootstrap-agent-infrastructure, 003-setup-development-environment, 004-architecture-documentation]

---

## Resolution

**Status**: ✅ All criteria met

1. ✅ `tests/` with `conftest.py` and 52 tests:
   - `test_progress.py`: 20 tests — add_vocabulary, update_vocab_after_review, get_review_words, vocab persistence round-trip, summary load/save, get_vocab_for_prompt
   - `test_config.py`: 13 tests — env var defaults, overrides, precedence, paths, guardrails
   - `test_conversation.py`: 15 tests — level parsing, status reports, prompt building, warmup, user_message, _extract_vocab_from_exchange (mocked), end_session
   - `test_fala.py`: 3 tests — CLI banner, quit exits, /voice toggle
2. ✅ pytest config in `pyproject.toml` (testpaths, python_files)
3. ✅ `.github/workflows/ci.yml` — `pytest` + `ruff check` on push/PR to main
4. ✅ All 52 tests pass; `ruff check .` clean; `ruff format --check .` clean
5. ⚠️ CI badge — requires GitHub repo setup (not applicable until first push)

**Bonus:** Fixed a bug in `load_vocabulary()` where the first vocab entry's `- word:` prefix was doubled during parsing. Also added `data/` to `.gitignore` to prevent runtime data from being tracked.

**Commit**: `bed1ac6` on `chore/bootstrap`

## Assets

- `.github/workflows/ci.yml`
- `tests/conftest.py`
- `tests/test_config.py`
- `tests/test_conversation.py`
- `tests/test_fala.py`
- `tests/test_progress.py`

## Question

How do we add automated testing and continuous integration so the project is safe to develop on?

## Acceptance

1. `tests/` directory with `conftest.py` and at least:
   - Unit tests for `progress.py` (SRS logic, vocab add/update/review, summary load/save)
   - Unit tests for `config.py` (env var overrides, path defaults)
   - Unit tests for `conversation.py` (prompt building, vocabulary extraction)
   - Smoke test for `fala.py` entrypoint (CLI banner, quit)
2. `pyproject.toml` or `pytest.ini` with pytest config
3. GitHub Actions workflow `.github/workflows/ci.yml` running `pytest` + `ruff check`
4. Tests pass on current code
5. CI badge in README (if applicable)
