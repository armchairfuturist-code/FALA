# FALA — Project Context

**What**: A conversational European Portuguese (pt-PT) tutor for English speakers, running in the terminal. No gamification, no streaks — just a patient LLM-powered tutor having natural conversations.

**Why**: The biggest component of learning a language is listening to conversations, not memorising vocabulary lists. FALA is built on conversation-first learning with a tutor that adapts to your level in real time.

**Target**: A1 → B1 (survive-in-Portugal level).

**How**: Each session follows: status report → warm-up (review + new vocab + grammar point) → free conversation → end (summary + spaced repetition update).

## Key design decisions

- **CLI over web/mobile** — low friction, fast iteration, works in any terminal
- **Hybrid audio** — local Whisper for STT, cloud TTS for natural pt-PT voices
- **File-based persistence** — human-readable markdown, grep-friendly, version-controllable
- **LLM-assisted spaced repetition** — the model assesses confidence, an SM-2-style scheduler handles timing
- **Priority-based error correction** — fix meaning-breaking errors immediately, note minor ones at end of turn
- **European Portuguese only** — no Brazilian vocabulary or pronunciation compromises

## Architecture overview

```
fala.py ──► conversation.py ──► (OpenAI LLM)
                    │
                    ├──► progress.py ──► data/summary.md, data/vocabulary.md
                    │
                    └──► audio.py ──► STT (Whisper/local → cloud), TTS (OpenAI)
```

The `ConversationEngine` manages the LLM conversation, prompt templates, and session lifecycle. `progress.py` handles the SM-2 spaced repetition scheduler and markdown persistence. `audio.py` chains through available STT/TTS backends with fallbacks.

## Current state

- Repo cloned to `~/Projects/FALA`
- Dependencies install in `.venv` (required on Arch Linux)
- CLI verified to start and show the banner (real API key needed for LLM calls)
- Agent infrastructure being bootstrapped
