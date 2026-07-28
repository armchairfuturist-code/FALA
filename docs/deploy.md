# FALA — Deployment Guide

## Local development

```bash
.venv/bin/python web.py  # serves on http://127.0.0.1:8080
```

No auth — anyone on localhost can use it.

## Docker (local)

```bash
docker build -t fala .
docker run -p 8080:8080 \
  -e FALA_API_KEY=gsk_... \
  -e FALA_BASE_URL=https://api.groq.com/openai/v1 \
  -e FALA_MODEL=llama-3.3-70b-versatile \
  -e FALA_INVITE_CODES=alex-beta-1,tester-2 \
  fala
```

Open `http://localhost:8080` — you'll see the invite-code page.

## Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT-ID/fala

# Deploy
gcloud run deploy fala \
  --image gcr.io/PROJECT-ID/fala \
  --port 8080 \
  --set-env-vars "FALA_API_KEY=gsk_...,FALA_BASE_URL=https://api.groq.com/openai/v1,FALA_MODEL=llama-3.3-70b-versatile,FALA_INVITE_CODES=alex-beta-1,tester-2" \
  --allow-unauthenticated
```

> `--allow-unauthenticated` lets Cloud Run's HTTPS proxy reach the app.
> Auth is handled by FALA's invite-code gate, not Cloud IAM.

## Environment variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `FALA_API_KEY` | yes | — | LLM provider API key (Groq or OpenAI) |
| `FALA_BASE_URL` | no | `https://api.openai.com/v1` | LLM API endpoint |
| `FALA_MODEL` | no | `gpt-4o` | LLM model name |
| `FALA_INVITE_CODES` | no | (empty = no auth) | Comma-separated invite codes; each is a user_id |
| `FALA_TTS` | no | `openai` | TTS provider: `openai` or `piper` |
| `FALA_TTS_VOICE` | no | `alloy` | OpenAI TTS voice |
| `FALA_STT_MODEL` | no | `base` | Whisper model size (local STT) |

## Notes

- **Piper TTS in Docker**: requires additional system deps (`espeak-ng`, `onnxruntime`).
  For hosted mode, `FALA_TTS=openai` is recommended. Piper is best for local CLI use.
- **STT in hosted mode**: local Whisper needs significant CPU/RAM. For Cloud Run,
  consider using the OpenAI Whisper API (automatic fallback if `openai-whisper`
  is not installed).
- **Data persistence**: user data lives in `data/users/<invite-code>/`. In Cloud Run,
  the container filesystem is ephemeral. For production, mount a persistent volume
  or add cloud storage (GCS, Firestore) — a future task.
