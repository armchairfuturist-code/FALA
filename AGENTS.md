# FALA — European Portuguese Tutor

A conversational European Portuguese tutor for English speakers. CLI-based, LLM-powered.

## Stack

- **Language**: Python 3.10+
- **Dependencies**: `openai` (LLM + TTS), `rich` (CLI), `openai-whisper` (optional, local STT)
- **Entrypoint**: `fala.py`
- **Package management**: `pip install -r requirements.txt` (in `.venv` — Arch Linux requires virtualenv)

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
export FALA_API_KEY=sk-...   # or OPENAI_API_KEY
.venv/bin/python fala.py
```

## Commands

| Command | Action |
|---------|--------|
| `python -m venv .venv` | Create virtualenv |
| `.venv/bin/pip install -r requirements.txt` | Install deps |
| `.venv/bin/python fala.py` | Run the tutor |
| `FALA_API_KEY=... .venv/bin/python fala.py` | Run with key |
| `FALA_MODEL=gpt-4o-mini` | Override LLM model |
| `FALA_TTS_VOICE=onyx` | Override TTS voice |

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
# or
.venv/bin/python -m ruff check .
```

## Conventions

- No monorepo tooling — this is a standalone project
- Use `gh` CLI for GitHub operations
- Git identity: Alex Myers <alex@thearmchairfuturist.com>
- All agent infrastructure lives in `docs/agents/`
- Architecture decisions in `docs/adr/`
- This project uses the `setup-matt-pocock-skills` pattern: canonical issue labels, GitHub Issues as tracker, CONTEXT.md + ADRs for domain docs
