# fala

A conversational European Portuguese (pt-PT) tutor for English speakers. No gamification, no streaks, no cartoon owl — just you and a patient tutor having a conversation.

**Target proficiency:** A0 → B1 (survive-in-Portugal level)

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
pip install piper-tts  # free pt-PT voice, no API key needed

# 4. Copy the example config and fill in a free Groq API key
cp .env.example .env
# Edit .env — replace gsk_your-key-here with your key from https://console.groq.com/keys
# Groq is free, no credit card needed, instant signup.
# The .env file is auto-loaded — no need to export manually.

# 5. Run
python3 fala.py
```

You'll see: the tutor greets you, introduces itself, and starts a warm-up. For your very first session, it will ask **"Como te chamas?"** in Portuguese — that's intentional, it's a teaching moment. Type your name in Portuguese and the conversation flows from there.

> **Two independent parts — both covered by Quick Start:**
> - **🧠 Tutor's brain** = LLM (required). Groq is free. You just paste the key.
> - **🗣️ Tutor's voice** = TTS (optional). Piper is free, `.env.example` already sets it up.
>
> Groq for brain + Piper for voice = $0, no credit card.

**Commands during a session:**
- `/voice` — toggle voice input mode (speak instead of type)
- `/stats` — show your vocabulary breakdown by CEFR level and SRS health
- `quit` / `exit` / `sair` — end the session

---

## What you need to know as a beta tester

### You need an API key for the brain — voice is optional

The app has **two independent parts**:

| Part | What | Required? | Free option |
|------|------|-----------|-------------|
| 🧠 **Brain** (LLM) | Generates conversation, corrections, feedback | ✅ Yes | Groq (free key, no credit card) |
| 🗣️ **Voice** (TTS) | Reads the tutor's responses aloud | ❌ No | Piper (free, local, no key needed) |

**For the brain (required):** Get a free Groq API key:
1. Go to https://console.groq.com/keys
2. Sign up (free, no credit card)
3. Create an API key (looks like `gsk_...`)
4. Edit your `.env` file — replace `gsk_your-key-here` with your key
The `.env` file is auto-loaded at startup — no `export` or `source` needed.

**OpenAI** also works (free $5 credits, requires credit card). Replace the `FALA_BASE_URL`, `FALA_API_KEY`, and `FALA_MODEL` lines in your `.env` file.

**For the voice (optional):** The `.env.example` already sets `FALA_TTS=piper` (free local voice). Just install it:

```bash
pip install piper-tts
```

**Best free setup:** Groq (🧠 brain) + Piper (🗣️ voice) = $0, no credit card.

### Audio
- **TTS (tutor speaks)**: Piper (local, free) by default — `.env.example` sets `FALA_TTS=piper`. Just `pip install piper-tts`.
- **STT (you speak)**: optional. Install `pip install openai-whisper` then use `/voice` during a session
- **No audio at all?**: Type-only works — just ignore any audio errors

### First session
- The tutor uses a **comprehension-first** method: says a pt-PT sentence → you translate to English → it affirms and repeats
- A0 level = no grammar, no open-ended questions, just listening and understanding
- Sessions are saved automatically. Stop anytime with `quit` and pick up later

### Known limitations
- Piper (tugão) is the only free local pt-PT voice — quality is medium but serviceable
- Pronunciation feedback only works when you **speak** (voice input), not when you type
- No multi-user support — this is a personal tool, single-user file-based
- The web prototype (`python3 web.py`) is minimal — chat only, no voice

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

Edit `.env` (copy from `.env.example` first):

| Provider | Cost | .env setup |
|----------|------|-----------|
| **Groq** (recommended) | Free, no credit card | Fill in `FALA_API_KEY` with a `gsk_...` key |
| **OpenAI** | $5 free credits, needs credit card | Fill in `OPENAI_API_KEY` with a `sk-...` key |
| **Other** (Together, Ollama, etc.) | Varies | Set `FALA_BASE_URL`, `FALA_API_KEY`, `FALA_MODEL` |

### TTS (tutor voice)

| Option | How | Quality | Cost | Offline |
|--------|-----|---------|------|---------|
| **Piper** (default in .env.example) | `pip install piper-tts` | Medium (dedicated pt-PT) | Free | ✅ |
| **OpenAI** (cloud) | Set `FALA_TTS=openai` in `.env` | Good (English-optimised) | Per-character | ❌ |
| **None** | Ignore audio errors | — | — | ✅ |

The Piper voice auto-downloads (~63 MB) on first use.

### STT (your voice input)
Optional. Install Whisper:
```bash
pip install openai-whisper
```
Then use `/voice` during a session to switch to voice input mode.

### Web prototype
```bash
pip install fastapi uvicorn python-multipart
python3 web.py
```
Open http://127.0.0.1:8080

---

## Environment variables

All set in `.env` (auto-loaded). Copy `.env.example` and edit:

```ini
FALA_BASE_URL=https://api.groq.com/openai/v1
FALA_API_KEY=gsk_your-key-here
FALA_MODEL=llama-3.3-70b-versatile
FALA_TTS=piper
```

| Variable | Default | Description |
|---|---|---|
| `FALA_API_KEY` | `$OPENAI_API_KEY` | LLM API key |
| `FALA_BASE_URL` | `https://api.openai.com/v1` | LLM API base URL |
| `FALA_MODEL` | `gpt-4o` | LLM model to use |
| `FALA_TTS` | `openai` | `openai` or `piper` |
| `FALA_TTS_VOICE` | `alloy` | Voice name (OpenAI only) |
| `FALA_STT_MODEL` | `base` | Whisper model size |

---

## Troubleshooting

| Problem | Likely fix |
|---------|-----------|
| `OpenAIError: Missing credentials` | Edit `.env` — set `FALA_API_KEY` with a Groq key |
| `No module named pip` | Create a virtualenv: `python -m venv .venv` |
| `ModuleNotFoundError: No module named 'piper'` | `pip install piper-tts` |
| `[Piper voice download failed]` | Check internet. Voice is ~63 MB from HuggingFace |
| `The model 'tts-1' does not exist` | TTS trying to use Groq endpoint. Install Piper: `pip install piper-tts` |
| No sound when tutor speaks | Need `mpv`, `ffplay`, or `aplay` installed |
| `/voice` does nothing | Install Whisper: `pip install openai-whisper` |

---

## How it works

1. **Status report** — see your level, words due for review
2. **Warm-up** — scenario-based sentence practice (café, restaurant, directions...)
3. **Free conversation** — natural dialogue
4. **Session end** — CEFR vocabulary breakdown + SRS health shown

Spaced repetition (SM-2) runs behind the scenes.

---

## Features

- **LLM-powered tutoring** — conversation, correction, pronunciation — one model
- **European Portuguese only** — no BR vocabulary/pronunciation
- **Voice input/output** — Piper (local) or OpenAI (cloud) TTS; optional Whisper STT
- **Comprehension-first method** — hear → translate → repeat. Words always in context sentences
- **Gentle in-flow correction** — never reveals the answer directly (research-backed)
- **Persistent memory** — rolling summary across unlimited sessions
- **CEFR vocabulary breakdown** — A1/A2/B1/B2+ bands via frequency list
- **SRS health report** — stats at session end and via `/stats`
- **Web prototype** — `python3 web.py` at http://127.0.0.1:8080
- **56 automated tests** — pytest, CI via GitHub Actions

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
├── config.py            # Settings, .env auto-loading
├── conversation.py      # Conversation engine, prompts, SRS feedback
├── audio.py             # STT (Whisper) + TTS (Piper/OpenAI)
├── progress.py          # Rolling summary, SM-2 SRS, CEFR stats
├── web.py               # Web prototype (FastAPI)
├── prompts/
│   ├── system.md        # Tutor personality and pedagogical rules
│   └── warmup.md        # Warm-up template
├── tests/               # 56 tests (pytest)
├── docs/
│   ├── agents/          # Wayfinding and agent infrastructure
│   ├── research/        # TTS/STT, conversation UX, evaluation
│   └── architecture.md
└── data/                # Auto-created on first run
    ├── summary.md       # Rolling session summary
    ├── vocabulary.md    # Words with SRS metadata
    ├── pt_50k.txt       # Frequency-ranked pt-PT word list
    ├── sessions/        # Raw session logs
    ├── records/         # Graduated word records
    └── piper-voices/    # Downloaded Piper voice models
```

---

## Design decisions

- **CLI over web/mobile** — low friction, works in any terminal
- **Hybrid audio** — local Whisper for STT; Piper (local) or OpenAI (cloud) for TTS
- **File-based persistence** — human-readable markdown, grep-friendly
- **LLM-assisted spaced repetition** — model assesses confidence, SM-2 handles timing
- **Comprehension-first method** — words taught in real-life example sentences, no grammar lectures
- **Gentle in-flow correction** — research-backed (Praktika, Talkpal, academic sources)
- **Pronunciation feedback on voice only** — never on typed input
- **CEFR vocabulary tracking** — `/stats` shows distribution and SRS health

---

## Feedback / Issues

This is an early-stage project. Bugs, rough edges, and missing features are expected. [Open an issue](https://github.com/armchairfuturist-code/FALA/issues) — every report makes the tool better.

---

## License

MIT
