---
type: task
labels: [wayfinder:task, wayfinder:claimed]
blocked_by: [002-bootstrap-agent-infrastructure, 003-setup-development-environment, 004-architecture-documentation]
---

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

## Assets

- `.github/workflows/ci.yml`
- `tests/` directory
