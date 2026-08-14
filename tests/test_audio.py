"""Tests for audio.py — Azure TTS provider and Groq-aware STT model."""

import urllib.request
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


class _FakeResp:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture(autouse=True)
def _clean_audio_globals():
    """Restore any monkeypatched audio globals after each test."""
    yield


class TestAzureTTS:
    def test_azure_tts_success_returns_mp3(self, tmp_path, monkeypatch):
        import audio

        captured = {}

        def fake_urlopen(req, timeout=60):
            captured["url"] = req.full_url
            captured["body"] = req.data.decode("utf-8")
            captured["key"] = next(
                (v for k, v in req.header_items() if k.lower() == "ocp-apim-subscription-key"),
                None,
            )
            return _FakeResp(b"fake-mp3-bytes")

        monkeypatch.setattr(audio, "AZURE_SPEECH_KEY", "azure-key")
        monkeypatch.setattr(audio, "AZURE_SPEECH_REGION", "westeurope")
        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

        out = audio._azure_text_to_speech("Olá, como estás?")
        assert out is not None
        assert out.suffix == ".mp3"
        assert out.read_bytes() == b"fake-mp3-bytes"
        out.unlink(missing_ok=True)

        # Correct endpoint, auth header, and pt-PT voice in the SSML
        assert captured["url"].endswith("/cognitiveservices/v1")
        assert captured["key"] == "azure-key"
        assert "pt-PT-FernandaNeural" in captured["body"]
        assert 'xml:lang="pt-PT"' in captured["body"]

    def test_azure_tts_escapes_ssml(self, monkeypatch):
        import audio

        captured = {}

        def fake_urlopen(req, timeout=60):
            captured["body"] = req.data.decode("utf-8")
            return _FakeResp(b"x")

        monkeypatch.setattr(audio, "AZURE_SPEECH_KEY", "azure-key")
        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

        out = audio._azure_text_to_speech('A & B < C > D "quote"')
        assert out is not None
        out.unlink(missing_ok=True)
        assert "A &amp; B &lt; C &gt; D" in captured["body"]

    def test_azure_tts_no_key_returns_none(self, monkeypatch):
        import audio

        monkeypatch.setattr(audio, "AZURE_SPEECH_KEY", "")
        assert audio._azure_text_to_speech("olá") is None

    def test_azure_tts_network_error_returns_none(self, monkeypatch):
        import audio

        monkeypatch.setattr(audio, "AZURE_SPEECH_KEY", "azure-key")

        def boom(req, timeout=60):
            raise urllib.error.URLError("service down")

        monkeypatch.setattr(urllib.request, "urlopen", boom)
        assert audio._azure_text_to_speech("olá") is None

    def test_text_to_speech_dispatches_to_azure(self, monkeypatch):
        import audio

        monkeypatch.setattr(audio, "TTS_PROVIDER", "azure")
        monkeypatch.setattr(audio, "_azure_text_to_speech", lambda text: f"azure-called:{text}")
        assert audio.text_to_speech("olá") == "azure-called:olá"

    def test_tts_provider_info_azure(self, monkeypatch):
        import audio

        monkeypatch.setattr(audio, "TTS_PROVIDER", "azure")
        monkeypatch.setattr(audio, "AZURE_SPEECH_KEY", "azure-key")
        assert "Azure" in audio.get_tts_provider_info()
        assert "FernandaNeural" in audio.get_tts_provider_info()

        monkeypatch.setattr(audio, "AZURE_SPEECH_KEY", "")
        assert "no key" in audio.get_tts_provider_info()


class TestSTT:
    def test_speech_to_text_uses_configured_api_model(self, tmp_path, monkeypatch):
        """The cloud STT fallback must use STT_API_MODEL (Groq has no whisper-1)."""
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")

        fake_client = MagicMock()
        fake_client.audio.transcriptions.create.return_value = SimpleNamespace(text="olá tudo bem")
        monkeypatch.setattr(audio, "_get_openai_client", lambda: fake_client)
        monkeypatch.setattr(audio, "STT_API_MODEL", "whisper-large-v3-turbo")

        result = audio.speech_to_text(wav)
        assert result == "olá tudo bem"
        kwargs = fake_client.audio.transcriptions.create.call_args.kwargs
        assert kwargs["model"] == "whisper-large-v3-turbo"
        assert kwargs["language"] == "pt"

    def test_speech_to_text_default_model_is_whisper1(self, tmp_path, monkeypatch):
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")

        fake_client = MagicMock()
        fake_client.audio.transcriptions.create.return_value = SimpleNamespace(text="bom dia")
        monkeypatch.setattr(audio, "_get_openai_client", lambda: fake_client)
        monkeypatch.setattr(audio, "STT_API_MODEL", "whisper-1")

        audio.speech_to_text(wav)
        kwargs = fake_client.audio.transcriptions.create.call_args.kwargs
        assert kwargs["model"] == "whisper-1"
