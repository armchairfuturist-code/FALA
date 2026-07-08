# fala

A conversational European Portuguese (pt-PT) tutor for English speakers. No gamification, no streaks, no cartoon owl — just you and a patient tutor having a conversation.

**Target proficiency:** A1 → B1 (survive-in-Portugal level)

---

## Quick Start (60 seconds)

```bash
# 1. Clone and enter
git clone https://github.com/armchairfuturist-code/FALA.git
cd FALA

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Get a free API key from Groq (https://console.groq.com/keys)
#    No credit card needed, instant signup, generous free tier.
export FALA_BASE_URL=https://api.groq.com/openai/v1
export FALA_API_KEY=gsk_your-key-here
export FALA_MODEL=llama-3.3-70b-versatile

# 5. Run
python3 fala.py
```

You'll see: the tutor greets you, introduces itself, and starts a warm-up. For your very first session, it will ask **"Como te chamas?"** in Portuguese — that's intentional, it's a teaching moment. Type your name in Portuguese and the conversation flows from there.

**Commands during a session:**
- `/voice` — toggle voice input mode (speak instead of type)
- `/stats` — show your vocabulary breakdown by CEFR level and SRS health
- `quit` / `exit` / `sair` — end the session

---

## What you need to know as a beta tester

### You need an API key — here's a free one

The app needs an LLM provider to run. The simplest free option is **Groq** — no credit card, instant signup, generous free tier, fully OpenAI-compatible.

```bash
# 1. Go to https://console.groq.com/keys
# 2. Sign up (free, no credit card)
# 3. Create an API key (gsk_...)
# 4. Set these:
export FALA_BASE_URL=https://api.groq.com/openai/v1
export FALA_API_KEY=gsk_your-key-here
export FALA_MODEL=llama-3.3-70b-versatile
```

**OpenAI** also works (free $5 credits on signup, requires credit card):
```bash
export OPENAI_API_KEY=sk-...
```

**Any OpenAI-compatible API** works — Groq, Together, Ollama (local), etc. Just set `FALA_BASE_URL`, `FALA_API_KEY`, and optionally `FALA_MODEL`.

### Audio
- **TTS (tutor speaks)**: enabled by default via OpenAI TTS (cloud). For offline/free TTS, install Piper (`pip install piper-tts` then `export FALA_TTS=piper`)
- **STT (you speak)**: optional. Install `pip install openai-whisper` then use `/voice` during a session
- **No audio at all?**: You can still type-only. The app works fine without audio — just ignore the TTS errors.

### First session
- The tutor is warm and patient. A1 means heavy English support; B1 means mostly Portuguese.
- Say anything — make mistakes. The tutor is designed to correct you gently, not to judge.
- Sessions are saved automatically. You can stop anytime with `quit` and pick up later.

### Known limitations
- The tutor's voice is OpenAI's TTS (English-optimised) by default. Piper (tugão) is free and local but quality is medium.
- Pronunciation feedback only works when you **speak** (voice input), not when you type.
- No multi-user support — this is a personal tool, single-user file-based.
- The web prototype (`python3 web.py`) is minimal — chat only, no voice.

---

## Setup (detailed)

### Prerequisites
- Python 3.10+
- A virtual environment (required on Arch Linux — system Python is externally managed)

```bash
cd FALA
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### LLM provider (required)

Pick one:

**Groq (free, no credit card, recommended for testing):**
```bash
export FALA_BASE_URL=https://api.groq.com/openai/v1
export FALA_API_KEY=gsk_your-key-here
export FALA_MODEL=llama-3.3-70b-versatile
```

**OpenAI (free $5 credits on signup, requires credit card):**
```bash
export OPENAI_API_KEY=sk-...
```

**Other provider (Together, Ollama locally, etc.):**
```bash
export FALA_BASE_URL=https://your-provider.com/v1
export FALA_API_KEY=your-key
export FALA_MODEL=your-model
```

### TTS (tutor voice)

| Option | How | Quality | Cost | Offline |
|--------|-----|---------|------|---------|
| **OpenAI** (default) | Nothing to install — uses `OPENAI_API_KEY` | Good, but English-optimised | Per-character billing | ❌ |
| **Piper** (local) | `pip install piper-tts` then `export FALA_TTS=piper` | Medium (dedicated pt-PT voice) | Free | ✅ |
| **None** | Ignore TTS errors — type-only works fine | — | — | ✅ |

The Piper voice model auto-downloads (~63 MB) on first use.

### STT (your voice input)
Optional. Install Whisper:
```bash
pip install openai-whisper
```
Then use `/voice` during a session to switch to voice input mode.

### Web prototype
A minimal web UI is available:
```bash
pip install fastapi uvicorn python-multipart
python3 web.py
```
Open http://127.0.0.1:8080 in your browser. Chat only, no voice in the web UI.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `FALA_API_KEY` | `$OPENAI_API_KEY` | LLM API key |
| `FALA_BASE_URL` | `https://api.openai.com/v1` | LLM API base URL |
| `FALA_MODEL` | `gpt-4o` | LLM model to use |
| `FALA_TTS` | `openai` | TTS provider (`openai` or `piper`) |
| `FALA_TTS_VOICE` | `alloy` | TTS voice name (OpenAI only) |
| `FALA_STT_MODEL` | `base` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large`) |

---

## Troubleshooting

| Problem | Likely fix |
|---------|-----------|
| `OpenAIError: Missing credentials` | Set `FALA_API_KEY` with a Groq key (free, see Quick Start) or `OPENAI_API_KEY` |
| `No module named pip` | Create a virtualenv: `python -m venv .venv` |
| `ModuleNotFoundError: No module named 'piper'` | `pip install piper-tts` (only needed for `FALA_TTS=piper`) |
| `[Piper voice download failed]` | Check your internet connection. Voice is ~63 MB from HuggingFace |
| No sound when tutor speaks | Check speakers, volume. Try `mpv`, `ffplay`, or `aplay` — one of these must be installed |
| `/voice` does nothing | Install Whisper: `pip install openai-whisper` |
| Tutor speaks too fast/slow | Not yet configurable — controlled by OpenAI TTS model |

---

## How it works

Each session follows a structured flow:

1. **Status report** — see your level, words due for review
2. **Warm-up** — retrieval practice on trouble words, new vocabulary, a grammar point
3. **Free conversation** — natural dialogue. You steer. The tutor weaves in what was taught.
4. **Session end** — progress compressed into a rolling summary. CEFR breakdown + SRS health shown.

The tutor uses spaced repetition (SM-2 scheduler) behind the scenes. Words you struggle with come back more often; words you know well fade. Every session builds on the last.

---

## Features

- **LLM-powered tutoring** — conversation, correction, pronunciation, difficulty — all handled by one model
- **European Portuguese only** — no BR vocabulary or pronunciation
- **Voice input/output** — Piper (local) or OpenAI (cloud) TTS; optional Whisper STT
- **Gentle in-flow correction** — the tutor models the correct version naturally, never reveals the answer directly (informed by Praktika, Talkpal, and academic research)
- **Phase-dependent scaffolding** — heavy English support at A1, mostly Portuguese by B1
- **Pronunciation feedback** — when speaking, the tutor evaluates and targets sounds hard for English speakers (nasal vowels, lh, nh, open/closed vowels)
- **Persistent memory** — rolling summary tracks strengths, weaknesses, grammar, and vocabulary across unlimited sessions
- **Spaced repetition** — LLM-assessed confidence → SM-2 scheduler
- **CEFR vocabulary breakdown** — each word mapped to A1/A2/B1/B2+ via a 50K-entry frequency list
- **SRS health report** — mature word count, average confidence, CEFR distribution shown at session end
- **Web prototype** — `python3 web.py` opens a chat UI in your browser
- **56 automated tests** — unit tests for SRS logic, conversation engine, config, and CLI

---

## Running tests

```bash
python -m pytest tests/ -v
```

---

## Project structure

```
fala/
├── fala.py              # CLI entrypoint
├── config.py            # Settings and paths
├── conversation.py      # Conversation engine — prompts, LLM calls, turn management, SRS feedback
├── audio.py             # STT (Whisper) + TTS (Piper local / OpenAI cloud)
├── progress.py          # Rolling summary, SM-2 spaced repetition, vocabulary tracking, CEFR stats
├── web.py               # Web prototype (FastAPI chat UI)
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

---

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

---

## Feedback / Issues

This is an early-stage project. Bugs, rough edges, and missing features are expected. If something broke or confused you, [open an issue](https://github.com/armchairfuturist-code/FALA/issues) — every report makes the tool better.

---

## License

MIT
