import html
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from openai import OpenAI

from config import (
    AZURE_SPEECH_KEY,
    AZURE_SPEECH_REGION,
    AZURE_TTS_VOICE,
    DATA_DIR,
    LLM_API_KEY,
    LLM_BASE_URL,
    STT_API_MODEL,
    STT_MODEL,
    TTS_PROVIDER,
    TTS_VOICE,
)

# ---------------------------------------------------------------------------
# Piper voice paths
# ---------------------------------------------------------------------------
PIPER_VOICES_DIR = DATA_DIR / "piper-voices"
PIPER_VOICE_NAME = "pt_PT-tugao-medium"  # ascii-safe local filename (original: tugão)
PIPER_MODEL_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
    "pt/pt_PT/tug%C3%A3o/medium/pt_PT-tug%C3%A3o-medium.onnx"
)
PIPER_CONFIG_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
    "pt/pt_PT/tug%C3%A3o/medium/pt_PT-tug%C3%A3o-medium.onnx.json"
)

PIPER_MODEL_PATH = PIPER_VOICES_DIR / "pt_PT-tugao-medium.onnx"
PIPER_CONFIG_PATH = PIPER_VOICES_DIR / "pt_PT-tugao-medium.onnx.json"


def _ensure_piper_voice() -> bool:
    """Download the Piper tugão voice if not already present. Returns True if available."""
    if PIPER_MODEL_PATH.exists() and PIPER_CONFIG_PATH.exists():
        return True

    PIPER_VOICES_DIR.mkdir(parents=True, exist_ok=True)

    try:
        print(f"[Downloading Piper voice: {PIPER_VOICE_NAME}...]")
        urllib.request.urlretrieve(PIPER_MODEL_URL, PIPER_MODEL_PATH)
        urllib.request.urlretrieve(PIPER_CONFIG_URL, PIPER_CONFIG_PATH)
        print("[Piper voice downloaded.]")
        return True
    except Exception as e:
        print(f"[Piper voice download failed: {e}]")
        return False


_piper_voice = None


def _get_piper_voice():
    """Load the Piper voice once and cache it (loading is slow, ~1-2s)."""
    global _piper_voice
    if _piper_voice is None:
        from piper import PiperVoice

        _piper_voice = PiperVoice.load(str(PIPER_MODEL_PATH), str(PIPER_CONFIG_PATH))
    return _piper_voice


def _piper_text_to_speech(text: str) -> Path | None:
    """Synthesize speech using Piper TTS with the pt-PT tugão voice."""
    if not _ensure_piper_voice():
        return None

    try:
        from piper.config import SynthesisConfig

        voice = _get_piper_voice()

        # Slower speech for beginners (length_scale 1.0 = normal, >1 = slower)
        syn_config = SynthesisConfig(length_scale=1.5)

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()

        import wave

        with wave.open(str(tmp_path), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file, syn_config=syn_config)

        return tmp_path

    except Exception as e:
        print(f"[Piper TTS error: {e}]")
        return None


# ---------------------------------------------------------------------------
# OpenAI client (lazy)
# ---------------------------------------------------------------------------

_client = None


def _get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    return _client


def _openai_text_to_speech(text: str) -> Path | None:
    """Synthesize speech using OpenAI TTS."""
    client = _get_openai_client()
    try:
        resp = client.audio.speech.create(
            model="tts-1",
            voice=TTS_VOICE,
            input=text,
            response_format="mp3",
        )
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(resp.content)
        tmp.close()
        return Path(tmp.name)
    except Exception as e:
        print(f"[OpenAI TTS error: {e}]")
        return None


# ---------------------------------------------------------------------------
# Azure Speech TTS (dedicated pt-PT neural voices)
# ---------------------------------------------------------------------------

_AZURE_TTS_URL = "https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
_AZURE_OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"


def _azure_text_to_speech(text: str) -> Path | None:
    """Synthesize speech using Azure Speech's pt-PT neural voices.

    Uses the REST API (no SDK dependency). Requires FALA_AZURE_KEY and
    FALA_AZURE_REGION (default: westeurope).
    """
    if not AZURE_SPEECH_KEY:
        print("[Azure TTS error: FALA_AZURE_KEY not set]")
        return None

    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="pt-PT">'
        f'<voice name="{AZURE_TTS_VOICE}">{html.escape(text)}</voice></speak>'
    )
    url = _AZURE_TTS_URL.format(region=AZURE_SPEECH_REGION)
    req = urllib.request.Request(
        url,
        data=ssml.encode("utf-8"),
        method="POST",
        headers={
            "Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": _AZURE_OUTPUT_FORMAT,
            "User-Agent": "FALA",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:
        print(f"[Azure TTS error: {e}]")
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.write(data)
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def text_to_speech(text: str) -> Path | None:
    """Synthesize speech using the configured TTS provider."""
    if TTS_PROVIDER == "piper":
        return _piper_text_to_speech(text)
    if TTS_PROVIDER == "azure":
        return _azure_text_to_speech(text)
    return _openai_text_to_speech(text)


def play_audio(path: Path) -> bool:
    players = [
        ["mpv", "--no-video", "--really-quiet", str(path)],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
        ["aplay", str(path)],
    ]
    for cmd in players:
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return False


def speak(text: str) -> bool:
    path = text_to_speech(text)
    if path:
        ok = play_audio(path)
        path.unlink(missing_ok=True)
        return ok
    return False


def get_tts_provider_info() -> str:
    """Return a human-readable string describing the active TTS provider."""
    if TTS_PROVIDER == "piper":
        if PIPER_MODEL_PATH.exists():
            return "TTS: Piper (local tugão pt-PT)"
        return "TTS: Piper (not downloaded)"
    if TTS_PROVIDER == "azure":
        if AZURE_SPEECH_KEY:
            return f"TTS: Azure (pt-PT neural, voice: {AZURE_TTS_VOICE})"
        return "TTS: Azure (no key set — set FALA_AZURE_KEY)"
    return f"TTS: OpenAI (cloud, voice: {TTS_VOICE})"


# ---------------------------------------------------------------------------
# STT (unchanged)
# ---------------------------------------------------------------------------


def speech_to_text(audio_path: Path) -> str | None:
    try:
        import whisper  # type: ignore[import-not-found]

        model = whisper.load_model(STT_MODEL)
        result = model.transcribe(str(audio_path), language="pt")
        return result.get("text", "").strip()
    except ImportError:
        pass

    client = _get_openai_client()
    try:
        with open(audio_path, "rb") as f:
            resp = client.audio.transcriptions.create(
                model=STT_API_MODEL,
                file=f,
                language="pt",
            )
        return resp.text.strip()
    except Exception as e:
        print(f"[STT error: {e}]")
        return None


def record_audio(duration: int = 10) -> Path | None:
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    path = Path(tmp.name)

    commands = [
        ["arecord", "-d", str(duration), "-f", "cd", "-q", str(path)],
        ["rec", "-q", str(path), "trim", "0", str(duration)],
    ]
    for cmd in commands:
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=duration + 5)
            return path
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return None


def listen() -> str | None:
    path = record_audio()
    if path:
        text = speech_to_text(path)
        path.unlink(missing_ok=True)
        return text
    return None
