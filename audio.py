import subprocess
import tempfile
from pathlib import Path
from openai import OpenAI
from config import LLM_API_KEY, LLM_BASE_URL, TTS_PROVIDER, TTS_VOICE, STT_MODEL


_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    return _client


def text_to_speech(text: str) -> Path | None:
    client = _get_client()
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
        print(f"[TTS error: {e}]")
        return None


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


def speech_to_text(audio_path: Path) -> str | None:
    try:
        import whisper
        model = whisper.load_model(STT_MODEL)
        result = model.transcribe(str(audio_path), language="pt")
        return result.get("text", "").strip()
    except ImportError:
        pass

    client = _get_client()
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
