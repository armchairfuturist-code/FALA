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
2. **Warm-up** — review trouble words, learn new vocabulary, introduce a grammar point
3. **Free conversation** — natural dialogue that weaves in what you've been taught
4. **Session end** — progress is compressed into a rolling summary that persists across sessions

The tutor uses spaced repetition behind the scenes. Words you struggle with come back more often; words you know well fade into the background. Every session builds on the last.

## Features

- **LLM-powered tutoring** — a single large model handles conversation, error correction, pronunciation feedback, and difficulty adjustment
- **European Portuguese only** — no Brazilian vocabulary or pronunciation compromises
- **Voice input/output** — the tutor always speaks (TTS in pt-PT voices); you can type or speak your responses
- **Priority-based error correction** — critical mistakes corrected immediately, minor ones noted at end of turn
- **Phase-dependent scaffolding** — heavy English support at A1, fading to mostly Portuguese by B1
- **Pronunciation feedback** — the tutor evaluates your speech and gives targeted feedback on sounds that are hard for English speakers (nasal vowels, lh, nh, open/closed vowels)
- **Persistent memory** — a rolling summary tracks your strengths, weaknesses, grammar progress, and vocabulary across unlimited sessions
- **Spaced repetition** — LLM-assessed confidence scores feed an SM-2-style scheduler

## Setup

```bash
cd fala
pip install -r requirements.txt
```

Set your API key:

```bash
export OPENAI_API_KEY=sk-...
```

Or use a different provider:

```bash
export FALA_BASE_URL=https://your-provider.com/v1
export FALA_API_KEY=your-key
export FALA_MODEL=your-model
```

For voice input, install Whisper locally:

```bash
pip install openai-whisper
```

## Usage

```bash
python3 fala.py
```

**Commands during a session:**
- `/voice` — toggle voice input mode
- `quit` / `exit` / `sair` — end the session

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `FALA_MODEL` | `gpt-4o` | LLM model to use |
| `FALA_BASE_URL` | `https://api.openai.com/v1` | LLM API base URL |
| `FALA_API_KEY` | `$OPENAI_API_KEY` | LLM API key |
| `FALA_TTS` | `openai` | TTS provider |
| `FALA_TTS_VOICE` | `alloy` | TTS voice |
| `FALA_STT_MODEL` | `base` | Whisper model size for STT |

## Project structure

```
fala/
├── fala.py              # CLI entrypoint
├── config.py            # Settings and paths
├── conversation.py      # Conversation engine (prompts, LLM calls, turn management)
├── audio.py             # STT (Whisper) + TTS (cloud) pipeline
├── progress.py          # Rolling summary, spaced repetition, vocabulary tracking
├── prompts/
│   ├── system.md        # Tutor personality and rules
│   └── warmup.md        # Warm-up phase template
└── data/                # Auto-created on first run
    ├── summary.md       # Rolling session summary
    ├── vocabulary.md    # Learned words with SRS metadata
    ├── sessions/        # Raw session logs
    └── records/         # Learning records
```

## Design decisions

Built from a deliberate set of choices:

- **CLI over web/mobile** — low friction, fast iteration, works in any terminal
- **Hybrid audio** — local Whisper for STT, cloud TTS for natural pt-PT voices (local EP voices are scarce)
- **File-based persistence** — human-readable markdown over databases; grep-friendly, version-controllable
- **LLM-assisted spaced repetition** — the model assesses confidence, a scheduler handles timing
- **Priority-based correction** — mirrors how a good human tutor works (fix meaning-breaking errors now, note small stuff later)

## License

MIT
