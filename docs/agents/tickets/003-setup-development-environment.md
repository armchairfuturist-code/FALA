---
type: task
labels: [wayfinder:task]
blocked_by: [001-clone-and-verify]
assigned_to: closed

---

## Resolution

**Status**: ✅ All criteria met

1. ✅ `scripts/bootstrap.sh` — creates `.venv`, installs runtime + dev deps; updated AGENTS.md with instructions
2. ✅ `requirements-dev.txt` with pytest, ruff, mypy; `pyproject.toml` with `[project.optional-dependencies] dev`
3. ✅ Ruff config in `pyproject.toml` (`[tool.ruff]`): py310 target, 100-char line length, E/F/I/W selects
4. ✅ `.env.example` with all FALA_* and OPENAI_* vars documented
5. ✅ `scripts/lint.sh` — runs ruff check, ruff format --check, mypy — all non-blocking
6. ✅ `ruff check .` passes clean; `ruff format --check .` passes clean; mypy: 12 pre-existing type issues in progress.py (dict mixing) — documented

**Known exceptions** (documented in AGENTS.md):
- mypy: 12 type errors from loosely-typed dict in `progress.py` — pre-existing, not introduced here

**Files created/modified:**
- `pyproject.toml`, `requirements-dev.txt`, `.env.example`
- `scripts/bootstrap.sh`, `scripts/lint.sh`
- `AGENTS.md` (updated with dev setup)
- `audio.py`, `conversation.py`, `fala.py`, `progress.py` (format + import fixes)

**Commit**: `c3cda46` on `chore/bootstrap`

## Assets

- `pyproject.toml`
- `requirements-dev.txt`
- `.env.example`
- `scripts/bootstrap.sh`
- `scripts/lint.sh`

## Question

What does the local development environment look like: virtualenv, dev extras, lint/format config, environment file, and tooling?

## Acceptance

1. Python virtualenv setup instructions in AGENTS.md or a `.venv` bootstrap script
2. `dev` extras in requirements or pyproject.toml: pytest, ruff, mypy (or pyright)
3. Ruff/pyright config in `pyproject.toml` or `ruff.toml`
4. `.env.example` with all config vars documented
5. `pre-commit` config or a simple lint script
6. All config works: `ruff check .` passes on current code with minimal (documented) exceptions
