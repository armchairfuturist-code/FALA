FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: OpenAI TTS (cloud). For local Piper TTS, set FALA_TTS=piper
# and download the voice model (see docs/research/tts-stt-ptpt.md).
# Piper requires additional system deps — not included in this image.

EXPOSE 8080

CMD ["uvicorn", "web:app", "--host", "0.0.0.0", "--port", "8080"]
