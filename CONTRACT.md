# CONTRACT — FALA voice web app (beta-ready)

**Goal**: FALA becomes a hosted-capable web app with a full voice conversation loop, ready to put in front of beta testers.

## Acceptance terms (checkable)

1. **Multi-user sessions** — concurrent users each get an isolated `ConversationEngine` keyed by session cookie; no global engine state; one user's data never leaks into another's prompts.
2. **Per-user persistence** — vocabulary/summary/sessions/records namespaced per user under `data/users/<id>/`; existing single-user `data/` migrates to a default user; server restart loses nothing on disk.
3. **Voice loop over HTTP** — browser push-to-talk → `POST /stt` → engine → `POST /tts` → audio playback; works on mobile Safari/Chrome (HTTPS or LAN).
4. **Text parity** — warmup, message, stats, quit all available in the web UI, matching CLI behavior.
5. **Auth-lite** — invite-code gate; no open signup; identity = stable per-user ID behind a cookie.
6. **Deployable** — `Dockerfile` builds and runs; config via env vars (API keys, TTS provider); documented Cloud Run deploy path.
7. **Latency feedback** — UI shows listening → thinking → speaking states; voice turn gives visible progress within 1s of mic release.
8. **Quality gates** — existing 77 tests stay green; new endpoints covered by TestClient tests; `scripts/lint.sh` (ruff + mypy) clean.

## Non-goals (this push)

- Streaming / VAD / interruptible speech (M2)
- Next.js frontend (only if UX polish demands it)
- Pronunciation scoring, CEFR dashboard UI (M3)
- Public launch, billing, accounts beyond invite codes

## Defaults adopted

- **Backend**: FastAPI + existing Python engine (no rewrite)
- **TTS**: Piper (local, pt-PT tugão) default; OpenAI TTS via env switch
- **STT**: Whisper API (or Groq) in hosted mode for latency; local Whisper optional
- **Deploy target**: Cloud Run (container)
- **Auth**: invite code + signed session cookie
