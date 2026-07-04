---
type: task
labels: [wayfinder:task, wayfinder:claimed]
blocked_by: [001-clone-and-verify]
---

## Question

What does the local development environment look like: virtualenv, dev extras, lint/format config, environment file, and tooling?

## Acceptance

1. Python virtualenv setup instructions in AGENTS.md or a `.venv` bootstrap script
2. `dev` extras in requirements or pyproject.toml: pytest, ruff, mypy (or pyright)
3. Ruff/pyright config in `pyproject.toml` or `ruff.toml`
4. `.env.example` with all config vars documented
5. `pre-commit` config or a simple lint script
6. All config works: `ruff check .` passes on current code with minimal (documented) exceptions

## Assets

- (linked when resolved)
