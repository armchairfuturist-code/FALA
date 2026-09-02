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

> **Set `--max-instances=1` until a shared store exists.** Session tokens,
> rate-limit windows, lockout counters, and live engines are all in-memory
> per container — multiple instances mean a request can land on a container
> that never saw the login, breaking auth and rate limiting.

## Persistent storage (important for real users)

Cloud Run's container filesystem is **ephemeral** — without a volume, every
deploy wipes user data (vocabulary, summaries, session checkpoints). Mount a
Cloud Storage bucket as a read-write volume:

```bash
# Create the bucket once
gcloud storage buckets create gs://fala-data --location=europe-west1

# Deploy with the volume mounted at /app/data
gcloud run deploy fala \
  --image gcr.io/PROJECT-ID/fala \
  --port 8080 \
  --add-volume name=data,type=cloud-storage,bucket=gs://fala-data \
  --add-volume-mount volume=data,mount-path=/app/data \
  --set-env-vars "FALA_API_KEY=gsk_...,FALA_BASE_URL=https://api.groq.com/openai/v1,FALA_MODEL=llama-3.3-70b-versatile,FALA_INVITE_CODES=alex-beta-1,tester-2,FALA_TTS=azure,FALA_AZURE_KEY=...,FALA_AZURE_REGION=westeurope"
```

Notes:
- `mount-path=/app/data` must match the app's `data/` dir (user data + Piper
  voices + session checkpoints all live there).
- Cloud Storage volumes are FUSE-backed: writes are eventually consistent
  (reads may lag writes by a few seconds). Fine for FALA's write pattern
  (vocabulary + one JSON checkpoint per turn).
- If your region doesn't support read-write GCS volumes yet, fall back to a
  Cloud Run execution-environment Gen2 instance with gcsfuse, or a small VM /
  managed Redis for session state.

## Environment variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `FALA_API_KEY` | yes | — | LLM provider API key (Groq or OpenAI) |
| `FALA_BASE_URL` | no | `https://api.openai.com/v1` | LLM API endpoint |
| `FALA_MODEL` | no | `gpt-4o` | LLM model name |
| `FALA_INVITE_CODES` | no | (empty = no auth) | Comma-separated invite codes; each is a user_id |
| `FALA_TTS` | no | `openai` | TTS provider: `openai`, `piper`, or `azure` |
| `FALA_TTS_VOICE` | no | `alloy` | OpenAI TTS voice |
| `FALA_AZURE_KEY` | no | — | Azure Speech key for `FALA_TTS=azure` (free tier ≈0.5M chars/mo) |
| `FALA_AZURE_REGION` | no | `westeurope` | Azure Speech region |
| `FALA_AZURE_VOICE` | no | `pt-PT-FernandaNeural` | Azure pt-PT voice |
| `FALA_STT_MODEL` | no | `base` | Whisper model size (local STT) |
| `FALA_STT_API_MODEL` | no | auto | Cloud STT model; auto-uses `whisper-large-v3-turbo` on Groq |
| `FALA_RATE_LIMIT_PER_MIN` | no | `30` | Web rate limit — requests/min per session/IP on `/message`, `/stt`, `/tts`, `/auth` |

## Notes

- **TTS in Docker**: Piper requires additional system deps (`espeak-ng`, `onnxruntime`).
  For hosted mode, `FALA_TTS=azure` is recommended (dedicated pt-PT neural voices,
  free tier). `FALA_TTS=openai` also works. Piper is best for local CLI use.
- **STT in hosted mode**: local Whisper needs significant CPU/RAM. The cloud
  fallback uses `FALA_STT_API_MODEL` — auto-set to Groq's `whisper-large-v3-turbo`
  when `FALA_BASE_URL` points at Groq, so the same key handles brain + STT.
- **Data persistence**: user data lives in `data/users/<invite-code>/`. In-progress
  conversations are checkpointed to disk after every turn, so a session survives a
  container restart (same volume). On Cloud Run the filesystem is ephemeral — for
  production, mount a persistent volume or add cloud storage (GCS, Firestore) — a
  future task.
- **Health check**: `GET /healthz` returns `{"status": "ok"}` for load-balancer /
  Cloud Run health probes.
