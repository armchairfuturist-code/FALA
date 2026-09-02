import html
import logging
import os
import re
import subprocess
import tempfile
import threading
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

logger = logging.getLogger(__name__)

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

_piper_voice = None  # cached PiperVoice (loaded once per process)
_piper_download_lock = threading.Lock()  # serializes the one-time download


def _ensure_piper_voice() -> bool:
    """Download the Piper tugão voice if not already present. Returns True if available.

    The download is guarded by a lock so two threads never race the fetch;
    the double-check inside the lock makes the common case lock-free.
    """
    if PIPER_MODEL_PATH.exists() and PIPER_CONFIG_PATH.exists():
        return True
    with _piper_download_lock:
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


def _get_piper_voice():
    """Load and cache the PiperVoice model at module level (reload is slow)."""
    global _piper_voice
    if _piper_voice is None:
        from piper import PiperVoice  # type: ignore[import-not-found]

        _piper_voice = PiperVoice.load(str(PIPER_MODEL_PATH), str(PIPER_CONFIG_PATH))
    return _piper_voice


def _piper_text_to_speech(text: str) -> Path | None:
    """Synthesize speech using Piper TTS with the pt-PT tugão voice."""
    if not _ensure_piper_voice():
        return None

    try:
        from piper.config import SynthesisConfig  # type: ignore[import-not-found]

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


def _gpt4o_text_to_speech(text: str) -> Path | None:
    """Synthesize speech using gpt-4o-mini-tts with pt-PT steering instructions."""
    client = _get_openai_client()
    try:
        resp = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=os.getenv("FALA_TTS_VOICE", "alloy"),
            input=text,
            instructions=(
                "Speak in European Portuguese (Portugal), slowly and clearly, "
                "standard Lisbon pronunciation."
            ),
            response_format="mp3",
        )
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(resp.content)
        tmp.close()
        return Path(tmp.name)
    except Exception as e:
        print(f"[gpt-4o-mini-tts error: {e}]")
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
        f'<voice name="{AZURE_TTS_VOICE}">'
        f'<prosody rate="-20%">{html.escape(text)}</prosody></voice></speak>'
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


# Speech channel contract: a tutor response may end with a "---SAY---" line;
# everything after it is the ONLY text to speak (pt-PT, no markdown).
_SAY_MARKER = "---SAY---"


def extract_speech_text(response: str) -> tuple[str, str | None]:
    """Split a tutor response into (display_text, speech_text|None).

    Returns speech_text=None when no ---SAY--- marker is present; the caller
    should then speak the display text (markdown-stripped) instead.
    """
    if _SAY_MARKER in response:
        display, _, speech = response.partition(_SAY_MARKER)
        return display.strip(), speech.strip()
    return response, None


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting that should never be read aloud."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [label](url) -> label
    text = text.replace("**", "").replace("__", "")  # bold
    text = text.replace("*", "").replace("`", "")  # italics / inline code
    text = re.sub(r"#{1,6}\s*", "", text)  # heading marks (anywhere)
    return text


def _use_gpt4o() -> bool:
    """True when the gpt-4o-mini-tts provider is selected."""
    return TTS_PROVIDER == "gpt4o" or os.getenv("FALA_TTS", "") == "gpt4o"


def text_to_speech(text: str) -> Path | None:
    """Synthesize speech using the configured TTS provider.

    Provider order: piper -> azure -> gpt4o (FALA_TTS=gpt4o) -> OpenAI tts-1.
    Markdown is stripped before synthesis in every provider.
    """
    text = _strip_markdown(text)
    if TTS_PROVIDER == "piper":
        return _piper_text_to_speech(text)
    if TTS_PROVIDER == "azure":
        return _azure_text_to_speech(text)
    # ponytail: FALA_TTS/FALA_TTS_VOICE are re-read from env here because
    # config.py is owned by another agent; move these into config.py as
    # gpt4o-specific constants once that merges.
    if _use_gpt4o():
        return _gpt4o_text_to_speech(text)
    return _openai_text_to_speech(text)


def play_audio(path: Path) -> bool:
    players = [
        ["mpv", "--no-video", "--really-quiet", str(path)],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
    ]
    # aplay only handles wav — feeding it mp3 fails (or emits raw noise).
    if path.suffix.lower() == ".wav":
        players.append(["aplay", str(path)])
    for cmd in players:
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return False


def speak(text: str) -> bool:
    """Speak a tutor response, honoring the ---SAY--- speech contract.

    When the response carries a ---SAY--- section, only that speech text is
    synthesized — never the marker or the English display text.
    """
    _display, speech = extract_speech_text(text)
    path = text_to_speech(speech if speech is not None else _display)
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
    if _use_gpt4o():
        return f"TTS: gpt-4o-mini-tts (cloud, voice: {os.getenv('FALA_TTS_VOICE', 'alloy')})"
    return f"TTS: OpenAI (cloud, voice: {TTS_VOICE})"


# ---------------------------------------------------------------------------
# STT — local faster-whisper (primary), openai-whisper (fallback), cloud (last)
# See docs/research/stt-2026.md for the rationale.
# ---------------------------------------------------------------------------

# Silence / hallucination guards (research: docs/research/stt-2026.md §4).
# Drop a segment as non-speech when no_speech_prob exceeds the max, or when
# avg_logprob falls below the floor (very negative = low confidence).
_NO_SPEECH_PROB_MAX = 0.6
_AVG_LOGPROB_FLOOR = -1.0

_fw_model = None  # cached faster-whisper model (loaded once per process)
_ow_model = None  # cached openai-whisper model (loaded once per process)


class _NoLocalSTT(Exception):
    """No local STT backend is importable — fall through to the cloud API."""


def _map_stt_model(name: str) -> str:
    """Map FALA_STT_MODEL values to faster-whisper model sizes.

    'turbo' is an alias for large-v3-turbo. Empty falls back to 'small'
    (best pt accuracy/latency trade-off on CPU per the research doc).
    Unknown names pass through — faster-whisper accepts any size or HF id.
    """
    name = (name or "").strip().lower()
    if not name:
        return "small"
    if name == "turbo":
        return "large-v3-turbo"
    return name


def _get_fw_model():
    """Load and cache the faster-whisper model at module level."""
    global _fw_model
    if _fw_model is None:
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]

        # ponytail: CPU int8 fixed — detecting CUDA via ctranslate2 and picking
        # device="cuda"/float16 is the upgrade path if latency ever matters.
        _fw_model = WhisperModel(_map_stt_model(STT_MODEL), device="cpu", compute_type="int8")
    return _fw_model


def _fw_transcribe(audio_path: Path) -> str | None:
    """Transcribe with faster-whisper. Returns None for likely silence/hallucination.

    faster-whisper splits an utterance into segments at pauses (an A0 learner
    thinking mid-sentence is enough). Concatenate ALL segments that pass the
    silence/hallucination thresholds, in order — keeping only the single
    best-scoring segment silently truncated multi-part utterances.
    """
    model = _get_fw_model()
    segments, _info = model.transcribe(
        str(audio_path), language="pt", condition_on_previous_text=False
    )
    kept: list[str] = []
    saw_segment = False
    for seg in segments:
        saw_segment = True
        # Likely silence or hallucination — drop the segment, not the utterance.
        if seg.no_speech_prob > _NO_SPEECH_PROB_MAX or seg.avg_logprob < _AVG_LOGPROB_FLOOR:
            continue
        kept.append(seg.text.strip())
    if not saw_segment:
        return ""
    if not kept:
        return None
    return " ".join(t for t in kept if t).strip()


def _ow_transcribe(audio_path: Path) -> str | None:
    """Fallback: transcribe with openai-whisper (model cached at module level)."""
    global _ow_model
    import whisper  # type: ignore[import-not-found]

    if _ow_model is None:
        _ow_model = whisper.load_model(STT_MODEL)
    result = _ow_model.transcribe(str(audio_path), language="pt")
    return result.get("text", "").strip()


def _local_speech_to_text(audio_path: Path) -> str | None:
    """Try local backends in order. Raises _NoLocalSTT if none is usable.

    ImportError means the backend is not installed — skip it silently. Any
    other backend failure (corrupt file, decode error, model fault) is logged
    and the next backend tried; a hallucination-threshold miss returns None
    from the backend as a normal value and does NOT trigger the cloud call.
    """
    for backend in (_fw_transcribe, _ow_transcribe):
        try:
            return backend(audio_path)
        except ImportError:
            continue
        except Exception:
            logger.warning("Local STT backend %s failed", backend.__name__, exc_info=True)
            continue
    raise _NoLocalSTT


def speech_to_text(audio_path: Path) -> str | None:
    try:
        return _local_speech_to_text(audio_path)
    except _NoLocalSTT:
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


def record_audio(duration: int = 30) -> Path | None:
    """Record from the mic. Prefers record-until-silence (sox), else fixed duration.

    ponytail: a sound-device silence-detection loop was rejected as overkill —
    sox's `silence` effect does it in one command: start on sound above 1%,
    stop after 2s of near-silence, capped at `duration` via trim. If sox is
    absent, arecord records the full duration with no early stop; upgrade path
    is a Python sounddevice callback loop.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    path = Path(tmp.name)
    # ponytail: if both recorders fail the temp file is never unlinked —
    # harmless on a reboot-cleared tmpfs; upgrade path is try/finally unlink.
    commands = [
        # sox: keep audio above 1%, stop after 2.0s below 2%, max `duration` s.
        [
            "rec",
            "-q",
            str(path),
            "trim",
            "0",
            str(duration),
            "silence",
            "1",
            "0.1",
            "1%",
            "1",
            "2.0",
            "2%",
        ],
        ["arecord", "-d", str(duration), "-f", "cd", "-q", str(path)],
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
