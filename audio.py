import subprocess
import tempfile
import urllib.request
from pathlib import Path

from openai import OpenAI

from config import DATA_DIR, LLM_API_KEY, LLM_BASE_URL, STT_MODEL, TTS_PROVIDER, TTS_VOICE

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


def _piper_text_to_speech(text: str) -> Path | None:
    """Synthesize speech using Piper TTS with the pt-PT tugão voice."""
    if not _ensure_piper_voice():
        return None

    try:
        from piper import PiperVoice
        from piper.config import SynthesisConfig

        voice = PiperVoice.load(str(PIPER_MODEL_PATH), str(PIPER_CONFIG_PATH))

        # Slower speech for beginners (length_scale 1.0 = normal, >1 = slower)
        syn_config = SynthesisConfig(length_scale=1.35)

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
# Public API
# ---------------------------------------------------------------------------


def text_to_speech(text: str) -> Path | None:
    """Synthesize speech using the configured TTS provider."""
    if TTS_PROVIDER == "piper":
        return _piper_text_to_speech(text)
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
    return f"TTS: OpenAI (cloud, voice: {TTS_VOICE})"


# ---------------------------------------------------------------------------
# STT (unchanged)
# ---------------------------------------------------------------------------


def speech_to_text(audio_path: Path) -> str | None:
    try:
        import whisper

        model = whisper.load_model(STT_MODEL)
        result = model.transcribe(str(audio_path), language="pt")
        return result.get("text", "").strip()
    except ImportError:
        pass

    client = _get_openai_client()
    try:
        with open(audio_path, "rb") as f:
            resp = client.audio.transcriptions.create(
                model="whisper-1",
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
