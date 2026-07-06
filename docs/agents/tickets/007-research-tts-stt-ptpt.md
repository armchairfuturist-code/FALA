---
type: research
labels: [wayfinder:research]
blocked_by: []
assigned_to: closed
---

## Question

What are the best Text-to-Speech (TTS) and Speech-to-Text (STT) options for European Portuguese (pt-PT) in the context of a CLI language tutor?

Current setup uses OpenAI TTS (English-optimised voices) and local Whisper for STT. Need to understand:

1. Does OpenAI TTS have true pt-PT voices, or are the current ones repurposed English voices?
2. What ElevenLabs pt-PT voices exist, and how natural do they sound?
3. What local TTS models support pt-PT (Coqui TTS, Piper, etc.)?
4. Is current STT (Whisper) adequate for pt-PT, or are there better alternatives?
5. What's the latency/cost trade-off for each option?

## Resolution

Research complete. Document at `docs/research/tts-stt-ptpt.md` covers 6 TTS options and 7 STT options for pt-PT.

**Key findings:**
- OpenAI TTS has **no true pt-PT voices** — all 13 are English-optimised multilingual profiles
- **ElevenLabs** supports pt via multilingual models; Voice Design can generate pt-PT voices
- **Piper TTS (tugão)** is the best local neural TTS — dedicated pt-PT medium voice, ~63 MB, runs on CPU
- **Google STT** has explicit `pt-PT` locale (best accuracy) vs Whisper's generic Portuguese (leans pt-BR)

**Recommendation:** Keep current setup as default, add Piper TTS as local/offline option, add Google STT as opt-in for accuracy.

**Graduated:** A follow-up ticket (#008) to implement Piper TTS support in `audio.py`.

## Acceptance

1. ✅ Summary of at least 3 TTS options evaluated — 6 covered (OpenAI, ElevenLabs, Piper, Coqui, eSpeak, MBROLA)
2. ✅ STT assessment — Whisper, Google STT, Azure, AWS, Meta MMS, faster-whisper, whisper.cpp
3. ✅ Recommendation with impact — multi-tier quality progression from fallback to best cloud
4. ✅ Stays within destination scope — CLI tutor, personal use

## Assets

- `docs/research/tts-stt-ptpt.md`
