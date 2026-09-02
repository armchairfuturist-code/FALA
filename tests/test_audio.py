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


class _FakeSegment:
    def __init__(self, text="olá tudo bem", no_speech_prob=0.01, avg_logprob=-0.3):
        self.text = text
        self.no_speech_prob = no_speech_prob
        self.avg_logprob = avg_logprob


@pytest.fixture
def fake_fw(monkeypatch):
    """Install a fake faster_whisper module and reset audio's model caches.

    Returns the FakeWhisperModel class: set .segments to control the fake
    transcription output; .calls records transcribe() invocations;
    .instances counts constructions (for the caching test).
    """
    import sys
    import types

    import audio

    class FakeWhisperModel:
        segments = [_FakeSegment()]
        instances = 0
        calls = []

        def __init__(self, name, device=None, compute_type=None):
            self.name = name
            self.device = device
            self.compute_type = compute_type
            type(self).instances += 1

        def transcribe(self, path, **kwargs):
            type(self).calls.append((path, kwargs))
            return iter(list(self.segments)), SimpleNamespace(language="pt")

    fake_mod = types.ModuleType("faster_whisper")
    fake_mod.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_mod)
    monkeypatch.setattr(audio, "_fw_model", None)
    monkeypatch.setattr(audio, "_ow_model", None)
    FakeWhisperModel.instances = 0
    FakeWhisperModel.calls = []
    return FakeWhisperModel


@pytest.fixture
def no_local_stt(monkeypatch):
    """Force both local STT backends to appear unavailable (ImportError)."""
    import audio

    def _no_local(path):
        raise ImportError("forced unavailable in test")

    monkeypatch.setattr(audio, "_fw_transcribe", _no_local)
    monkeypatch.setattr(audio, "_ow_transcribe", _no_local)


class TestMapSTTModel:
    def test_turbo_alias(self):
        import audio

        assert audio._map_stt_model("turbo") == "large-v3-turbo"

    def test_empty_defaults_to_small(self):
        import audio

        assert audio._map_stt_model("") == "small"

    def test_known_sizes_pass_through(self):
        import audio

        assert audio._map_stt_model("small") == "small"
        assert audio._map_stt_model("base") == "base"
        assert audio._map_stt_model("large-v3-turbo") == "large-v3-turbo"

    def test_case_and_whitespace_normalized(self):
        import audio

        assert audio._map_stt_model("  TURBO ") == "large-v3-turbo"


class TestLocalSTT:
    def test_transcribes_with_pt_and_no_conditioning(self, tmp_path, fake_fw, monkeypatch):
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")
        monkeypatch.setattr(audio, "STT_MODEL", "small")

        result = audio.speech_to_text(wav)
        assert result == "olá tudo bem"
        assert audio._fw_model.name == "small"
        assert audio._fw_model.compute_type == "int8"
        assert fake_fw.instances == 1
        path, kwargs = fake_fw.calls[0]
        assert path == str(wav)
        assert kwargs["language"] == "pt"
        assert kwargs["condition_on_previous_text"] is False

    def test_silence_returns_none_not_text(self, tmp_path, fake_fw):
        """no_speech_prob above threshold means silence — must not return text."""
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")
        fake_fw.segments = [_FakeSegment(text="Thank you for watching", no_speech_prob=0.9)]

        assert audio.speech_to_text(wav) is None

    def test_low_confidence_returns_none(self, tmp_path, fake_fw):
        """avg_logprob below the floor is likely hallucination — return None."""
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")
        fake_fw.segments = [_FakeSegment(avg_logprob=-1.5)]

        assert audio.speech_to_text(wav) is None

    def test_thresholds_boundary_passes(self, tmp_path, fake_fw):
        """Values just inside the thresholds are kept."""
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")
        fake_fw.segments = [_FakeSegment(no_speech_prob=0.6, avg_logprob=-1.0)]

        result = audio.speech_to_text(wav)
        # Exactly at the thresholds is kept (checks are strict > / <).
        assert result == "olá tudo bem"

    def test_no_segments_returns_empty_string(self, tmp_path, fake_fw):
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")
        fake_fw.segments = []

        assert audio.speech_to_text(wav) == ""

    def test_multi_segment_utterance_concatenated_in_order(self, tmp_path, fake_fw):
        """A pause mid-sentence splits the utterance — all good parts kept."""
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")
        fake_fw.segments = [
            _FakeSegment(text="bom dia "),
            _FakeSegment(text="Thank you for watching", no_speech_prob=0.9),
            _FakeSegment(text=" tudo bem"),
        ]

        assert audio.speech_to_text(wav) == "bom dia tudo bem"

    def test_all_segments_failing_returns_none(self, tmp_path, fake_fw):
        """Drop-to-None applies when NO segment passes the thresholds."""
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")
        fake_fw.segments = [
            _FakeSegment(text="olá", no_speech_prob=0.9),
            _FakeSegment(text="tudo", avg_logprob=-2.0),
        ]

        assert audio.speech_to_text(wav) is None

    def test_model_cached_across_calls(self, tmp_path, fake_fw):
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")

        audio.speech_to_text(wav)
        audio.speech_to_text(wav)

        assert fake_fw.instances == 1  # WhisperModel constructed exactly once


class TestOpenAIWhisperFallback:
    def _fake_whisper_module(self, monkeypatch, text=" bom dia "):
        import sys
        import types

        import audio

        load_calls = []
        fake_model = MagicMock()
        fake_model.transcribe.return_value = {"text": text}
        fake_whisper = types.ModuleType("whisper")
        fake_whisper.load_model = lambda name: load_calls.append(name) or fake_model
        monkeypatch.setitem(sys.modules, "whisper", fake_whisper)
        monkeypatch.setattr(audio, "_fw_model", None)
        monkeypatch.setattr(audio, "_ow_model", None)
        return load_calls, fake_model

    def _disable_faster_whisper(self, monkeypatch):
        import audio

        def _no_fw(path):
            raise ImportError("faster-whisper not installed")

        monkeypatch.setattr(audio, "_fw_transcribe", _no_fw)

    def test_used_when_faster_whisper_missing(self, tmp_path, monkeypatch):
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")
        self._disable_faster_whisper(monkeypatch)
        load_calls, fake_model = self._fake_whisper_module(monkeypatch)

        result = audio.speech_to_text(wav)
        assert result == "bom dia"
        fake_model.transcribe.assert_called_once_with(str(wav), language="pt")
        assert load_calls == [audio.STT_MODEL]  # model name from config

    def test_model_cached_across_calls(self, tmp_path, monkeypatch):
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")
        self._disable_faster_whisper(monkeypatch)
        load_calls, fake_model = self._fake_whisper_module(monkeypatch)

        audio.speech_to_text(wav)
        audio.speech_to_text(wav)

        assert len(load_calls) == 1  # whisper.load_model called exactly once
        assert fake_model.transcribe.call_count == 2


class TestCloudSTTFallback:
    def test_speech_to_text_uses_configured_api_model(self, tmp_path, monkeypatch, no_local_stt):
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

    def test_local_backend_error_falls_through_to_cloud(self, tmp_path, monkeypatch):
        """A corrupt file / decode error in a local backend must not crash —
        it falls through to the cloud fallback (audit #16, verification N-probe)."""
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"garbage")

        def _boom(path):
            raise RuntimeError("corrupt wav")

        def _no_ow(path):
            raise ImportError("whisper not installed")

        monkeypatch.setattr(audio, "_fw_transcribe", _boom)
        monkeypatch.setattr(audio, "_ow_transcribe", _no_ow)

        fake_client = MagicMock()
        fake_client.audio.transcriptions.create.return_value = SimpleNamespace(text="olá")
        monkeypatch.setattr(audio, "_get_openai_client", lambda: fake_client)

        assert audio.speech_to_text(wav) == "olá"
        fake_client.audio.transcriptions.create.assert_called_once()

    def test_hallucination_none_does_not_hit_cloud(self, tmp_path, fake_fw, monkeypatch):
        """A threshold-based None is a normal result — no cloud fallback call."""
        import audio

        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"fake-audio")
        fake_fw.segments = [_FakeSegment(text="Thank you", no_speech_prob=0.9)]

        fake_client = MagicMock()
        monkeypatch.setattr(audio, "_get_openai_client", lambda: fake_client)

        assert audio.speech_to_text(wav) is None
        fake_client.audio.transcriptions.create.assert_not_called()

    def test_speech_to_text_default_model_is_whisper1(self, tmp_path, monkeypatch, no_local_stt):
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


class TestRecordAudio:
    def test_uses_sox_silence_recording_when_available(self, tmp_path, monkeypatch):
        import audio

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr(audio.subprocess, "run", fake_run)

        path = audio.record_audio(duration=30)
        assert path is not None and path.exists()
        path.unlink(missing_ok=True)

        assert len(calls) == 1
        cmd = calls[0]
        assert cmd[0] == "rec"
        assert "silence" in cmd
        assert "2.0" in cmd  # stop after 2s of silence
        assert str(30) in cmd  # trim cap == max duration

    def test_falls_back_to_arecord_without_sox(self, tmp_path, monkeypatch):
        import audio

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "rec":
                raise FileNotFoundError("no sox")
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr(audio.subprocess, "run", fake_run)

        path = audio.record_audio(duration=10)
        assert path is not None
        path.unlink(missing_ok=True)

        assert [c[0] for c in calls] == ["rec", "arecord"]
        assert calls[1] == ["arecord", "-d", "10", "-f", "cd", "-q", str(path)]

    def test_returns_none_when_no_recorder(self, monkeypatch):
        import audio

        monkeypatch.setattr(audio.subprocess, "run", _raise_fnf)

        assert audio.record_audio() is None


def _raise_fnf(*args, **kwargs):
    raise FileNotFoundError("no recorder")


class TestPlayAudio:
    def test_aplay_only_for_wav(self, tmp_path, monkeypatch):
        import audio

        cmds = []

        def fake_run(cmd, **kwargs):
            cmds.append(cmd)
            if cmd[0] != "aplay":  # only aplay "exists" in this test
                raise FileNotFoundError(cmd[0])
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr(audio.subprocess, "run", fake_run)

        mp3 = tmp_path / "x.mp3"
        mp3.write_bytes(b"x")
        assert audio.play_audio(mp3) is False
        assert all(c[0] != "aplay" for c in cmds)  # never offered aplay for mp3

        cmds.clear()
        wav = tmp_path / "x.wav"
        wav.write_bytes(b"x")
        assert audio.play_audio(wav) is True
        assert [c[0] for c in cmds] == ["mpv", "ffplay", "aplay"]  # aplay reached last


class TestExtractSpeechText:
    def test_with_marker(self):
        import audio

        resp = "Bom dia! Vamos praticar.\n---SAY---\nBom dia! Praticar agora."
        display, speech = audio.extract_speech_text(resp)
        assert display == "Bom dia! Vamos praticar."
        assert speech == "Bom dia! Praticar agora."

    def test_with_marker_and_surrounding_whitespace(self):
        import audio

        resp = "Hello  \n\n---SAY---\n\n  Fala português  "
        display, speech = audio.extract_speech_text(resp)
        assert display == "Hello"
        assert speech == "Fala português"

    def test_without_marker_returns_none_speech(self):
        import audio

        display, speech = audio.extract_speech_text("Just a plain reply")
        assert display == "Just a plain reply"
        assert speech is None


class TestStripMarkdown:
    def test_bold_italic_code_headings_links(self):
        import audio

        text = "**Bom** *dia* `tudo` ### Bem? [olá](http://x.pt)"
        assert audio._strip_markdown(text) == "Bom dia tudo Bem? olá"

    def test_plain_text_unchanged(self):
        import audio

        assert audio._strip_markdown("Olá, tudo bem?") == "Olá, tudo bem?"

    def test_stripped_before_synthesis(self, monkeypatch):
        """text_to_speech strips markdown in every provider path."""
        import audio

        seen = {}
        monkeypatch.setattr(audio, "TTS_PROVIDER", "azure")
        monkeypatch.setattr(
            audio, "_azure_text_to_speech", lambda t: seen.setdefault("text", t) or "x"
        )
        audio.text_to_speech("**Olá** [mundo](http://x.pt)")
        assert seen["text"] == "Olá mundo"


class TestAzureSSMLProsody:
    def test_ssml_has_slow_prosody_and_ptpt_lang(self, monkeypatch):
        import audio

        captured = {}

        def fake_urlopen(req, timeout=60):
            captured["body"] = req.data.decode("utf-8")
            return _FakeResp(b"x")

        monkeypatch.setattr(audio, "AZURE_SPEECH_KEY", "azure-key")
        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

        out = audio._azure_text_to_speech("Olá!")
        assert out is not None
        out.unlink(missing_ok=True)
        assert 'prosody rate="-20%"' in captured["body"]
        assert 'xml:lang="pt-PT"' in captured["body"]
        # prosody wraps the escaped voice content, inside the voice element
        assert 'pt-PT-FernandaNeural"><prosody rate="-20%">Olá!' in captured["body"]


class TestGpt4oTTS:
    def _fake_client(self):
        client = MagicMock()
        client.audio.speech.create.return_value = SimpleNamespace(content=b"mp3-bytes")
        return client

    def test_dispatch_when_env_gpt4o(self, tmp_path, monkeypatch):
        import audio

        client = self._fake_client()
        monkeypatch.setattr(audio, "_get_openai_client", lambda: client)
        monkeypatch.setenv("FALA_TTS", "gpt4o")
        monkeypatch.delenv("FALA_TTS_VOICE", raising=False)

        out = audio.text_to_speech("Olá, tudo bem?")
        assert out is not None and out.suffix == ".mp3"
        assert out.read_bytes() == b"mp3-bytes"
        out.unlink(missing_ok=True)

        kwargs = client.audio.speech.create.call_args.kwargs
        assert kwargs["model"] == "gpt-4o-mini-tts"
        assert kwargs["voice"] == "alloy"
        assert kwargs["input"] == "Olá, tudo bem?"
        assert "European Portuguese" in kwargs["instructions"]
        assert "Lisbon" in kwargs["instructions"]

    def test_dispatch_when_config_provider_gpt4o(self, tmp_path, monkeypatch):
        import audio

        client = self._fake_client()
        monkeypatch.setattr(audio, "_get_openai_client", lambda: client)
        monkeypatch.setattr(audio, "TTS_PROVIDER", "gpt4o")
        monkeypatch.setenv("FALA_TTS_VOICE", "coral")

        out = audio.text_to_speech("olá")
        assert out is not None
        out.unlink(missing_ok=True)
        assert client.audio.speech.create.call_args.kwargs["voice"] == "coral"

    def test_env_fallback_to_openai_tts1(self, tmp_path, monkeypatch):
        """Without FALA_TTS=gpt4o the tts-1 fallback is used."""
        import audio

        client = self._fake_client()
        monkeypatch.setattr(audio, "_get_openai_client", lambda: client)
        monkeypatch.delenv("FALA_TTS", raising=False)
        monkeypatch.setattr(audio, "TTS_PROVIDER", "openai")

        out = audio.text_to_speech("olá")
        assert out is not None
        out.unlink(missing_ok=True)
        assert client.audio.speech.create.call_args.kwargs["model"] == "tts-1"

    def test_provider_info_gpt4o(self, monkeypatch):
        import audio

        monkeypatch.setattr(audio, "TTS_PROVIDER", "gpt4o")
        info = audio.get_tts_provider_info()
        assert "gpt-4o-mini-tts" in info
        assert "alloy" in info

    def test_provider_info_gpt4o_via_env(self, monkeypatch):
        import audio

        monkeypatch.setattr(audio, "TTS_PROVIDER", "openai")
        monkeypatch.setenv("FALA_TTS", "gpt4o")
        assert "gpt-4o-mini-tts" in audio.get_tts_provider_info()

    def test_gpt4o_error_returns_none(self, monkeypatch):
        import audio

        client = MagicMock()
        client.audio.speech.create.side_effect = RuntimeError("api down")
        monkeypatch.setattr(audio, "_get_openai_client", lambda: client)
        monkeypatch.setattr(audio, "TTS_PROVIDER", "gpt4o")
        assert audio.text_to_speech("olá") is None


class TestSpeak:
    """The CLI speech path must honor the ---SAY--- contract (verification N1)."""

    def test_speak_synthesizes_only_speech_text(self, monkeypatch, tmp_path):
        import audio

        seen = {}
        fake = tmp_path / "fake.mp3"
        fake.write_bytes(b"x")
        monkeypatch.setattr(audio, "text_to_speech", lambda t: (seen.setdefault("t", t), fake)[1])
        monkeypatch.setattr(audio, "play_audio", lambda p: True)

        assert audio.speak("Bom dia! Good morning.\n---SAY---\nBom dia!") is True
        assert seen["t"] == "Bom dia!"  # no marker, no English display text

    def test_speak_without_marker_synthesizes_display(self, monkeypatch, tmp_path):
        import audio

        seen = {}
        fake = tmp_path / "fake.mp3"
        fake.write_bytes(b"x")
        monkeypatch.setattr(audio, "text_to_speech", lambda t: (seen.setdefault("t", t), fake)[1])
        monkeypatch.setattr(audio, "play_audio", lambda p: True)

        audio.speak("Just a plain reply")
        assert seen["t"] == "Just a plain reply"

    def test_speak_no_synthesis_returns_false(self, monkeypatch):
        import audio

        monkeypatch.setattr(audio, "text_to_speech", lambda t: None)
        assert audio.speak("olá") is False


class TestPiperVoiceCaching:
    def test_voice_loaded_once_across_calls(self, monkeypatch):
        import sys
        import types

        import audio

        monkeypatch.setattr(audio, "_ensure_piper_voice", lambda: True)
        monkeypatch.setattr(audio, "_piper_voice", None)

        loads = []

        def fake_synth(text, wav_file, syn_config=None):
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)

        fake_voice = types.SimpleNamespace(synthesize_wav=fake_synth)

        fake_piper = types.ModuleType("piper")
        fake_piper.PiperVoice = types.SimpleNamespace(load=lambda *a: loads.append(a) or fake_voice)
        fake_config_mod = types.ModuleType("piper.config")
        fake_config_mod.SynthesisConfig = lambda **k: object()
        monkeypatch.setitem(sys.modules, "piper", fake_piper)
        monkeypatch.setitem(sys.modules, "piper.config", fake_config_mod)

        # Two synthesis calls must construct PiperVoice.load exactly once.
        for _ in range(2):
            out = audio._piper_text_to_speech("olá")
            assert out is not None
            out.unlink(missing_ok=True)

        assert len(loads) == 1
        monkeypatch.setattr(audio, "_piper_voice", None)  # don't leak cache

    def test_ensure_piper_voice_skips_download_when_present(self, monkeypatch, tmp_path):
        import audio

        monkeypatch.setattr(audio, "PIPER_MODEL_PATH", tmp_path / "m.onnx")
        monkeypatch.setattr(audio, "PIPER_CONFIG_PATH", tmp_path / "c.json")
        (tmp_path / "m.onnx").write_bytes(b"x")
        (tmp_path / "c.json").write_bytes(b"x")
        called = []
        monkeypatch.setattr(audio.urllib.request, "urlretrieve", lambda *a: called.append(a))
        assert audio._ensure_piper_voice() is True
        assert called == []
