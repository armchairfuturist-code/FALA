# fala

A conversational European Portuguese tutor for English speakers. No gamification, no streaks, no cartoon owl — just you and a patient tutor having a conversation.

## What it is

`fala` is a CLI-based language learning tool that teaches European Portuguese (pt-PT) through natural conversation. It starts with simple phrases and progressively increases complexity as you improve. The tutor always speaks back to you — reinforcing listening skills alongside vocabulary and grammar.

**Target proficiency:** A1 → B1 (survive-in-Portugal level)

## Why conversation-first

The biggest component of learning a language is listening to conversations, not memorizing vocabulary lists. `fala` is built on this principle: you learn by talking and listening, with a tutor that adapts to your level in real time.

## How it works

Each session follows a structured flow:

1. **Status report** — see where you left off, what's due for review
2. **Warm-up** — review trouble words (retrieval practice), learn new vocabulary, introduce a grammar point
3. **Free conversation** — natural dialogue that weaves in what you've been taught. The learner steers.
4. **Session end** — progress is compressed into a rolling summary that persists across sessions

The tutor uses spaced repetition behind the scenes. Words you struggle with come back more often; words you know well fade into the background. Every session builds on the last.

## Features

- **LLM-powered tutoring** — a single large model handles conversation, error correction, pronunciation feedback, and difficulty adjustment
- **European Portuguese only** — no Brazilian vocabulary or pronunciation compromises
- **Voice input/output** — the tutor always speaks (Piper local TTS or OpenAI cloud TTS); you can type or speak your responses
- **Gentle in-flow error correction** — the tutor corrects by modelling the correct version naturally, not with red markers. Never reveals the answer directly — guides with hints instead.
- **Phase-dependent scaffolding** — heavy English support at A1, fading to mostly Portuguese by B1
- **Pronunciation feedback** — when speaking, the tutor evaluates your speech and gives targeted feedback on sounds hard for English speakers (nasal vowels, lh, nh, open/closed vowels)
- **Persistent memory** — a rolling summary tracks your strengths, weaknesses, grammar progress, and vocabulary across unlimited sessions
- **Spaced repetition** — LLM-assessed confidence scores feed an SM-2-style scheduler
- **CEFR vocabulary breakdown** — every word is mapped to a CEFR band (A1/A2/B1/B2+) via a frequency-ranked pt-PT word list. See your progress at any time with `/stats`.
- **SRS health report** — session end shows mature word count, average confidence, and CEFR distribution
- **56 automated tests** — unit tests for SRS logic, conversation engine, config, and CLI smoke tests

## Setup

### Prerequisites

- Python 3.10+
- A virtual environment (required on Arch Linux — system Python is externally managed)

```bash
cd fala
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### OpenAI (default TTS)

```bash
export OPENAI_API_KEY=sk-...
```

Or use a different provider:

```bash
export FALA_BASE_URL=https://your-provider.com/v1
export FALA_API_KEY=your-key
export FALA_MODEL=your-model
```

### Piper TTS (local, offline, free)

Piper provides a dedicated European Portuguese voice (`tugão`). The voice model auto-downloads (~63 MB) on first use.

```bash
pip install piper-tts
export FALA_TTS=piper
```

### Voice input

For speech-to-text, install Whisper locally:

```bash
pip install openai-whisper
```

## Usage

```bash
python3 fala.py
```

**Commands during a session:**
- `/voice` — toggle voice input mode
- `/stats` — show CEFR vocabulary breakdown and SRS health report
- `quit` / `exit` / `sair` — end the session

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `FALA_MODEL` | `gpt-4o` | LLM model to use |
| `FALA_BASE_URL` | `https://api.openai.com/v1` | LLM API base URL |
| `FALA_API_KEY` | `$OPENAI_API_KEY` | LLM API key |
| `FALA_TTS` | `openai` | TTS provider (`openai` or `piper`) |
| `FALA_TTS_VOICE` | `alloy` | TTS voice (OpenAI only) |
| `FALA_STT_MODEL` | `base` | Whisper model size for STT |

## Running tests

```bash
python -m pytest tests/ -v
```

## Project structure

```
fala/
├── fala.py              # CLI entrypoint
├── config.py            # Settings and paths
├── conversation.py      # Conversation engine (prompts, LLM calls, turn management, SRS feedback)
├── audio.py             # STT (Whisper) + TTS (Piper local / OpenAI cloud)
├── progress.py          # Rolling summary, spaced repetition (SM-2), vocabulary tracking
├── prompts/
│   ├── system.md        # Tutor personality, correction style, pronunciation rules
│   └── warmup.md        # Warm-up phase template with retrieval practice
├── tests/               # 56 tests (pytest)
│   ├── test_config.py
│   ├── test_conversation.py
│   ├── test_fala.py
│   └── test_progress.py
├── docs/
│   ├── agents/          # Agent infrastructure and wayfinding
│   ├── research/        # Research findings (TTS/STT, conversation UX, evaluation)
│   └── architecture.md  # Design decisions and module documentation
└── data/                # Auto-created on first run
    ├── summary.md       # Rolling session summary
    ├── vocabulary.md    # Learned words with SRS metadata
    ├── pt_50k.txt       # Frequency-ranked pt-PT word list (CEFR mapping)
    ├── sessions/        # Raw session logs
    ├── records/         # Learning records for graduated words
    └── piper-voices/    # Downloaded Piper voice models
```

## Design decisions

Built from a deliberate set of choices:

- **CLI over web/mobile** — low friction, fast iteration, works in any terminal
- **Hybrid audio** — local Whisper for STT; Piper (local) or OpenAI (cloud) for TTS
- **File-based persistence** — human-readable markdown over databases; grep-friendly, version-controllable
- **LLM-assisted spaced repetition** — the model assesses confidence per turn; SM-2 scheduler handles timing
- **Gentle in-flow correction** — the tutor models the correct version naturally, never reveals the answer directly (informed by research on Praktika, Talkpal, and academic sources)
- **Pronunciation feedback on voice only** — the tutor only gives pronunciation advice when you speak, not when you type
- **CEFR-graded vocabulary tracking** — every word gets a CEFR band based on a 50K-entry frequency list. `/stats` shows your vocabulary distribution and SRS health at a glance.
- **Natural name introduction** — the tutor asks "Como te chamas?" in Portuguese as the very first interaction, making it a teaching moment

## License

MIT
