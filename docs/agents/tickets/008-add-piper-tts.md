---
type: task
labels: [wayfinder:task]
blocked_by: [007-research-tts-stt-ptpt]
assigned_to: alex
---

## Question

Add Piper TTS (tugão pt-PT voice) as a local/offline TTS option in `audio.py`, switchable via `FALA_TTS=piper`.

Research (ticket #007) identified Piper's `pt_PT-tugão-medium` as the best free, offline, CPU-runnable TTS with a dedicated European Portuguese voice.

## Acceptance

1. Piper TTS engine implemented in `audio.py` as a new provider alongside OpenAI
2. `FALA_TTS=piper` env var switches to Piper; `FALA_TTS=openai` (default) keeps current behaviour
3. Piper voice download/auto-install on first use (or clear error message telling user to install)
4. Existing tests pass; new tests for Piper path
5. `fala.py` CLI banner shows available TTS providers (e.g. "TTS: Piper (local)" vs "TTS: OpenAI (cloud)")
