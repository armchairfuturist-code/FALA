# FALA — European Portuguese Tutor

A conversational European Portuguese tutor for English speakers. CLI-based, LLM-powered.

## Stack

- **Language**: Python 3.10+
- **Dependencies**: `openai` (LLM + TTS), `rich` (CLI), `openai-whisper` (optional, local STT)
- **Entrypoint**: `fala.py`
- **Package management**: `pip install -r requirements.txt` (in `.venv` — Arch Linux requires virtualenv)
- **Dev setup**: `source scripts/bootstrap.sh` or `pip install -r requirements-dev.txt`

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
export FALA_API_KEY=sk-...   # or OPENAI_API_KEY
.venv/bin/python fala.py
```

## Development setup

```bash
source scripts/bootstrap.sh    # creates .venv, installs all deps
.venv/bin/pip install -r requirements-dev.txt  # or add dev deps manually
```

Copy `.env.example` to `.env` and fill in your API key:

```bash
cp .env.example .env
# edit .env with your FALA_API_KEY
```

## Commands

| Command | Action |
|---------|--------|
| `python -m venv .venv` | Create virtualenv |
| `source scripts/bootstrap.sh` | Full dev setup (venv + deps) |
| `.venv/bin/pip install -r requirements.txt` | Install runtime deps |
| `.venv/bin/pip install -r requirements-dev.txt` | Install dev deps (pytest, ruff, mypy) |
| `cp .env.example .env` | Create env file |
| `.venv/bin/python fala.py` | Run the tutor |
| `scripts/lint.sh` | Run all linters |
| `.venv/bin/ruff check .` | Lint with ruff |
| `.venv/bin/ruff check --fix .` | Auto-fix lint issues |
| `.venv/bin/python -m pytest tests/ -v` | Run tests |

## Code layout

```
fala.py             # CLI entrypoint — main loop, voice toggle
config.py           # Env vars, paths, guardrails
conversation.py     # ConversationEngine — prompt building, LLM calls, turn management
audio.py            # STT (Whisper/local) + TTS (OpenAI) pipeline
progress.py         # Rolling summary, SM-2 SRS, vocabulary persistence
prompts/
  system.md         # Tutor personality, error correction rules
  warmup.md         # Warm-up phase prompt template
data/               # Auto-created: sessions/, records/, summary.md, vocabulary.md
```

## Testing

Tests live in `tests/`. Run with:

```bash
.venv/bin/python -m pytest tests/ -v
```

## Linting

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy .
# or all at once:
scripts/lint.sh
```

## Conventions

- No monorepo tooling — this is a standalone project
- Use `gh` CLI for GitHub operations
- Git identity: Alex Myers <alex@thearmchairfuturist.com>
- All agent infrastructure lives in `docs/agents/`
- Architecture decisions in `docs/adr/`
- This project uses the `setup-matt-pocock-skills` pattern: canonical issue labels, GitHub Issues as tracker, CONTEXT.md + ADRs for domain docs
- Use `.venv` for all Python environments (system Python is externally managed on Arch)
- Output style: see `~/.claude/CLAUDE.md` § Maximum Terseness — zero preamble, fragments over sentences. Both agents (MiMo Code, OMP) enforce identical rules.
