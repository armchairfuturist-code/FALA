---
type: task
labels: [wayfinder:task]
blocked_by: [007-research-tts-stt-ptpt]
assigned_to: closed
---

## Question

Add Piper TTS (tugão pt-PT voice) as a local/offline TTS option in `audio.py`, switchable via `FALA_TTS=piper`.

Research (ticket #007) identified Piper's `pt_PT-tugão-medium` as the best free, offline, CPU-runnable TTS with a dedicated European Portuguese voice.

## Resolution

Implemented in `audio.py`. Piper TTS engine uses `piper-tts` v1.4.2 (OHF-Voice/piper1-gpl) with the `pt_PT-tugão-medium` ONNX voice model.

**What was done:**
1. Added `_piper_text_to_speech()` — loads PiperVoice, synthesizes text to WAV via `synthesize_wav()`
2. Added `_ensure_piper_voice()` — auto-downloads tugão voice (~63 MB) from HuggingFace on first use
3. `text_to_speech()` dispatches to Piper or OpenAI based on `TTS_PROVIDER` (from `FALA_TTS` env var)
4. Added `get_tts_provider_info()` — returns human-readable string for the CLI banner
5. `fala.py` banner shows "TTS: Piper (local tugão pt-PT)" or "TTS: OpenAI (cloud, voice: alloy)"
6. Voice files stored in `data/piper-voices/` using ASCII-safe filenames

**Usage:** `FALA_TTS=piper python3 fala.py`
**Default:** `FALA_TTS=openai` (existing behavior)

| # | Acceptance | Status |
|---|-----------|--------|
| 1 | Piper engine alongside OpenAI | ✅ |
| 2 | FALA_TTS=piper / FALA_TTS=openai switching | ✅ |
| 3 | Voice auto-downloads on first use | ✅ |
| 4 | Existing tests pass (56/56) | ✅ |
| 5 | CLI banner shows TTS provider | ✅ |
