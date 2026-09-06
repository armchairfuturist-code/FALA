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
**Best hosted setup (web beta):** Groq (🧠 brain + STT, one key) + Azure (`FALA_TTS=azure`) = free tiers, dedicated pt-PT neural voice.

### Audio
- **TTS (tutor speaks)**: Piper (local, free) by default — `.env.example` sets `FALA_TTS=piper`. Just `pip install piper-tts`.
- **STT (you speak)**: optional. Install `pip install openai-whisper` then use `/voice` during a session
- **No audio at all?**: Type-only works — just ignore any audio errors

### First session
- The tutor uses a **comprehension-first** method: says a pt-PT sentence → you translate to English → it affirms and repeats
- A0 level = no grammar, no open-ended questions, just listening and understanding
- Sessions are saved automatically. Stop anytime with `quit` and pick up later

### Known limitations
- Piper (tugão) is the only free local pt-PT voice — quality is medium but serviceable; for the hosted web app use `FALA_TTS=azure` (dedicated pt-PT neural voices, free tier)
- Pronunciation feedback only works when you **speak** (voice input), not when you type
- Cloud Run filesystem is ephemeral — user data resets on redeploy unless you mount a persistent volume (see `docs/deploy.md`)
- Piper TTS needs system deps not in the Docker image (use `FALA_TTS=azure` or `openai` for hosted)
- No streaming/VAD yet — push-to-talk only (hands-free is a planned M2 improvement)

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
| **Kokoro** (natural local voice) | `pip install tts_eu_pt` + `FALA_TTS=kokoro` | High (eu-pt voice, 24 kHz) | Free | ✅ |
| **Azure** (best for hosted) | Set `FALA_TTS=azure` + `FALA_AZURE_KEY` | High (dedicated pt-PT neural voices: Fernanda/Raquel/Duarte) | Free tier ~0.5M chars/mo | ❌ |
| **OpenAI** (cloud) | Set `FALA_TTS=openai` in `.env` | Good (English-optimised) | Per-character | ❌ |
| **None** | Ignore audio errors | — | — | ✅ |

The Piper voice auto-downloads (~63 MB) on first use.

### STT (your voice input)
Optional. Install Whisper:
```bash
pip install openai-whisper
```
Then use `/voice` during a session to switch to voice input mode.

### Web app (with voice)

The web app wraps the CLI engine in a browser UI with push-to-talk voice:

```bash
python3 web.py
```
Open http://127.0.0.1:8080

**Features:**
- Push-to-talk voice input (browser `MediaRecorder` → Whisper STT)
- TTS playback of tutor responses (Piper or OpenAI)
- Text input fallback
- Multi-user support (cookie-keyed sessions, per-user data isolation)
- Invite-code auth (set `FALA_INVITE_CODES` env var) — gates every endpoint, including `/stt` and `/tts`
- Rate limiting on cost-bearing endpoints (`FALA_RATE_LIMIT_PER_MIN`, default 30/min)
- Refresh-safe: your conversation is checkpointed to disk after every turn, so a page refresh or server restart resumes where you left off (the transcript is re-rendered from `GET /history`)
- Mobile-friendly (works on phone browsers)

**Docker:**

```bash
docker build -t fala .
docker run -p 8080:8080 \
  -e FALA_API_KEY=gsk_... \
  -e FALA_BASE_URL=https://api.groq.com/openai/v1 \
  -e FALA_MODEL=llama-3.3-70b-versatile \
  -e FALA_INVITE_CODES=alex-beta-1,tester-2 \
  fala
```

See [`docs/deploy.md`](docs/deploy.md) for Cloud Run deployment.

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
| `FALA_TTS` | `openai` | `openai`, `piper`, or `azure` |
| `FALA_TTS_VOICE` | `alloy` | Voice name (OpenAI only) |
| `FALA_AZURE_KEY` | (empty) | Azure Speech key (for `FALA_TTS=azure`); also reads `AZURE_SPEECH_KEY` |
| `FALA_AZURE_REGION` | `westeurope` | Azure Speech region (e.g. `northeurope`) |
| `FALA_AZURE_VOICE` | `pt-PT-FernandaNeural` | Azure pt-PT voice (Fernanda/Raquel/Duarte) |
| `FALA_STT_MODEL` | `base` | Whisper model size (local STT) |
| `FALA_STT_API_MODEL` | auto | Cloud STT model; auto-uses Groq's `whisper-large-v3-turbo` when `FALA_BASE_URL` is Groq |
| `FALA_INVITE_CODES` | (empty = no auth) | Comma-separated invite codes for web app auth |
| `FALA_RATE_LIMIT_PER_MIN` | `30` | Web rate limit — requests/min per session/IP on `/message`, `/stt`, `/tts`, `/auth` |

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
- **Web app with voice** — `python3 web.py`, push-to-talk, multi-user, Docker-ready
- **103 automated tests** — pytest, CI via GitHub Actions

---

## v0.2 — Daily-Driver Trust Pass (July 2026)

This release closes the gap between "demo works" and "I'd trust it with 200 hours of vocabulary." **Zero new features** — every change is a fix, a guardrail, or a test.

| Area | Before | After |
|------|--------|-------|
| **Tests** | 59 | **77** (+18) |
| **Type safety** (mypy) | 13 errors | **0 errors** |
| **Lint** (ruff) | 1 error | **clean** |
| **`vocabulary_report`** | 0 tests | **4 tests** (empty, CEFR bands, unknown word, SRS stats) |
| **`web.py` coverage** | 0 tests | **12 tests** (all 5 endpoints + regression guards for B5/B9) |
| **`max_new_words_per_session`** | defined, never enforced | **enforced in code** (LLM output truncated to cap) |
| **`start_warmup` idempotency** | no guard — double-call corrupts context | **early-return on second call** |
| **Record numbering** | `len+1` reuses on delete | **`max+1`** no collision |
| **Session filename collision** | seconds-resolution (B11 claimed minutes) | **accepted as-is** — negligible edge for personal CLI |

**No behavior changes** except the guardrail enforcement — everything else is test coverage, type hints, or cosmetic numbering.


---

## v0.3 — Voice Web App (July 2026)

Turns FALA from a CLI-only tool into a deployable web app with voice conversation, ready for beta testers.

| Area | Before | After |
|------|--------|-------|
| **Web app** | Minimal text-only prototype (single global session) | Full app: voice, multi-user, auth, Docker-ready |
| **Voice over HTTP** | CLI-only (`arecord`/`mpv` subprocess) | `/stt` + `/tts` endpoints, browser `MediaRecorder`, push-to-talk |
| **Multi-user** | Single global engine | Cookie-keyed sessions, per-user data isolation (`data/users/<id>/`) |
| **Auth** | None | Invite-code gate (`FALA_INVITE_CODES` env var) |
| **Deployment** | Run locally only | Dockerfile + Cloud Run deploy guide |
| **Tests** | 77 | **103** (+26: multi-user isolation, voice endpoints, auth) |

**3 commits:** multi-user foundation → voice loop → auth + Docker.

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
├── web.py               # Web app — FastAPI, voice, multi-user, auth
├── prompts/
│   ├── system.md        # Tutor personality and pedagogical rules
│   └── warmup.md        # Warm-up template
├── tests/               # 103 tests — pytest, CI via GitHub Actions
├── Dockerfile # Container image for Cloud Run / Docker
├── docs/
│   ├── agents/          # Wayfinding and agent infrastructure
│   ├── research/        # TTS/STT, conversation UX, evaluation
│   ├── deploy.md        # Docker + Cloud Run deployment guide
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

- **CLI and web** — CLI for personal use, web app for beta testers with voice + multi-user
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
