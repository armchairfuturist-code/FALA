"""Tests for web.py — FastAPI endpoints wrapping ConversationEngine."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_engine():
    """Patch ConversationEngine with a mock and yield the mock instance."""
    with patch("web.ConversationEngine") as mock_cls:
        instance = MagicMock()
        instance.start_warmup.return_value = "Bem-vindo! Vamos começar."
        instance.user_message.return_value = "Ótimo! Continue assim."
        instance.end_session.return_value = "Até logo!"
        instance.get_status_report.return_value = "Level: A1, Sessions: 0"
        instance.get_stats.return_value = "📊 1 word · 1 review due"
        instance.get_history.return_value = [
            {"role": "tutor", "content": "Bem-vindo! Vamos começar."},
            {"role": "user", "content": "olá"},
        ]
        mock_cls.return_value = instance
        yield instance


@pytest.fixture(autouse=True)
def reset_web_globals():
    """Reset the web module's session/token stores before each test."""
    import web

    web._sessions.clear()
    web._rate_windows.clear()
    web._session_tokens.clear()
    web._code_failures.clear()
    yield


@pytest.fixture
def client():
    from web import app

    return TestClient(app)


class TestIndex:
    def test_returns_html_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "FALA" in resp.text
        assert "text/html" in resp.headers["content-type"]


class TestStart:
    def test_start_returns_warmup_and_status(self, client, mock_engine):
        resp = client.post("/start")
        data = resp.json()
        assert data["response"] == "Bem-vindo! Vamos começar."
        assert "Level: A1" in data["status"]
        mock_engine.start_warmup.assert_called_once()

    def test_double_start_is_idempotent_resume(self, client, mock_engine):
        client.post("/start")  # first call
        resp = client.post("/start")  # second call
        data = resp.json()
        assert data["resumed"] is True
        assert "resumed" in data["response"].lower()
        # start_warmup should only be called once (no double warm-up)
        mock_engine.start_warmup.assert_called_once()

    def test_start_after_quit_allows_new_session(self, client, mock_engine):
        client.post("/start")
        mock_engine.end_session.return_value = "Até logo!"
        client.post("/quit")
        # Now try to start again — should re-create engine
        mock_engine2 = MagicMock()
        mock_engine2.start_warmup.return_value = "Welcome back!"
        mock_engine2.get_status_report.return_value = "Level: A1, Sessions: 1"

        with patch("web.ConversationEngine") as mock_cls:
            mock_cls.return_value = mock_engine2
            resp = client.post("/start")
            data = resp.json()
            assert data["response"] == "Welcome back!"


class TestMessage:
    def test_message_before_start_rejected(self, client):
        resp = client.post("/message", data={"text": "olá"})
        data = resp.json()
        assert "No active session" in data["response"]
        assert "/start first" in data["response"].lower()

    def test_message_returns_tutor_response(self, client, mock_engine):
        client.post("/start")
        resp = client.post("/message", data={"text": "olá"})
        data = resp.json()
        assert data["response"] == "Ótimo! Continue assim."
        mock_engine.user_message.assert_called_once()

    def test_quit_message_ends_session(self, client, mock_engine):
        client.post("/start")
        resp = client.post("/message", data={"text": "quit"})
        data = resp.json()
        assert data["response"] == "Até logo!"
        mock_engine.end_session.assert_called_once()

    def test_message_after_quit_rejected(self, client, mock_engine):
        client.post("/start")
        client.post("/message", data={"text": "quit"})
        resp = client.post("/message", data={"text": "olá de novo"})
        data = resp.json()
        assert "No active session" in data["response"] or "Session ended" in data["response"]


class TestStats:
    def test_stats_returns_data(self, client, mock_engine):
        client.post("/start")
        resp = client.get("/stats")
        data = resp.json()
        assert "1 review due" in data["stats"]

    def test_stats_before_start_returns_data(self, client, mock_engine):
        """get_engine() creates an engine even without /start for /stats."""
        resp = client.get("/stats")
        data = resp.json()
        assert "stats" in data


class TestMultiUserIsolation:
    def test_session_cookie_set_and_stable(self, client, mock_engine):
        client.post("/start")
        sid = client.cookies.get("fala_session")
        assert sid
        client.post("/message", data={"text": "olá"})
        assert client.cookies.get("fala_session") == sid

    def test_two_clients_get_isolated_engines(self):
        from web import app

        engines = []

        def make_engine(user_id):
            m = MagicMock()
            m.start_warmup.return_value = f"warmup-{user_id}"
            m.get_status_report.return_value = "status"
            engines.append((user_id, m))
            return m

        with patch("web.ConversationEngine", side_effect=make_engine):
            client_a = TestClient(app)
            client_b = TestClient(app)
            ra = client_a.post("/start")
            rb = client_b.post("/start")

            assert ra.json()["response"] != rb.json()["response"]
            assert len(engines) == 2
            assert engines[0][0] != engines[1][0]
            assert client_a.cookies.get("fala_session") != client_b.cookies.get("fala_session")

            # Messaging on A touches only A's engine
            client_a.post("/message", data={"text": "olá"})
            engines[0][1].user_message.assert_called_once()
            engines[1][1].user_message.assert_not_called()

            # B's session is unaffected by A quitting
            client_a.post("/quit")
            resp = client_b.post("/message", data={"text": "olá"})
            assert "No active session" not in resp.json()["response"]


class TestQuit:
    def test_quit_ends_session(self, client, mock_engine):
        client.post("/start")
        resp = client.post("/quit")
        data = resp.json()
        assert data["response"] == "Até logo!"
        mock_engine.end_session.assert_called_once()

    def test_double_quit_rejected(self, client, mock_engine):
        client.post("/start")
        client.post("/quit")
        resp = client.post("/quit")
        data = resp.json()
        assert "No active session" in data["response"]


class TestSTT:
    def test_stt_returns_transcript(self, client):
        with patch("web.speech_to_text", return_value="olá tudo bem"):
            resp = client.post("/stt", files={"file": ("voice.webm", b"audio", "audio/webm")})
        assert resp.json()["transcript"] == "olá tudo bem"

    def test_stt_empty_transcript(self, client):
        with patch("web.speech_to_text", return_value=None):
            resp = client.post("/stt", files={"file": ("voice.webm", b"audio", "audio/webm")})
        assert resp.json()["transcript"] == ""

    def test_stt_error_is_generic(self, client):
        with patch("web.speech_to_text", side_effect=RuntimeError("STT failed")):
            resp = client.post("/stt", files={"file": ("voice.webm", b"audio", "audio/webm")})
        data = resp.json()
        assert data["transcript"] == ""
        assert "STT failed" not in data["error"]  # no internal detail echoed

    @staticmethod
    def _wav_bytes(seconds: float, byte_rate: int = 8000) -> bytes:
        import struct

        data_size = int(seconds * byte_rate)
        fmt = struct.pack("<HHIIHH", 1, 1, 8000, byte_rate, 2, 16)  # PCM mono 16-bit
        return (
            b"RIFF"
            + (36 + data_size).to_bytes(4, "little")
            + b"WAVE"
            + b"fmt "
            + (16).to_bytes(4, "little")
            + fmt
            + b"data"
            + data_size.to_bytes(4, "little")
            + b"\x00" * 8
        )

    def test_stt_rejects_wav_longer_than_cap(self, client):
        """A .wav whose header claims > 120 s is rejected without transcription."""
        with patch("web.speech_to_text") as mock_stt:
            resp = client.post(
                "/stt", files={"file": ("voice.wav", self._wav_bytes(121), "audio/wav")}
            )
        assert resp.status_code == 413
        mock_stt.assert_not_called()

    def test_stt_accepts_wav_within_cap(self, client):
        with patch("web.speech_to_text", return_value="olá") as mock_stt:
            resp = client.post(
                "/stt", files={"file": ("voice.wav", self._wav_bytes(5), "audio/wav")}
            )
        assert resp.json()["transcript"] == "olá"
        mock_stt.assert_called_once()

    def test_non_wav_has_no_header_duration_cap(self, client):
        """Non-wav formats rely on the 10 MB cap — no header parse possible."""
        with patch("web.speech_to_text", return_value="olá"):
            resp = client.post(
                "/stt", files={"file": ("voice.webm", b"\x1aE\xdf\xa3garbage", "audio/webm")}
            )
        assert resp.json()["transcript"] == "olá"


class TestTTS:
    def test_tts_returns_mp3_audio(self, client):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake-mp3")
            tmp = Path(f.name)
        with patch("web.text_to_speech", return_value=tmp):
            resp = client.post("/tts", data={"text": "olá"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/mpeg"
        assert resp.content == b"fake-mp3"
        assert not tmp.exists()

    def test_tts_returns_wav_audio(self, client):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"fake-wav")
            tmp = Path(f.name)
        with patch("web.text_to_speech", return_value=tmp):
            resp = client.post("/tts", data={"text": "olá"})
        assert resp.headers["content-type"] == "audio/wav"
        assert not tmp.exists()

    def test_tts_synthesis_failure(self, client):
        with patch("web.text_to_speech", return_value=None):
            resp = client.post("/tts", data={"text": "olá"})
        assert "error" in resp.json()


class TestAuth:
    @pytest.fixture
    def auth_enabled(self):
        import web

        old_codes, old_enabled = web.AUTH_CODES, web.AUTH_ENABLED
        web.AUTH_CODES = {"test-code-1", "test-code-2"}
        web.AUTH_ENABLED = True
        web._sessions.clear()
        yield
        web.AUTH_CODES = old_codes
        web.AUTH_ENABLED = old_enabled

    def test_index_shows_auth_page_when_enabled(self, client, auth_enabled):
        resp = client.get("/")
        assert "invite code" in resp.text.lower()

    def test_index_shows_chat_when_authenticated(self, client, auth_enabled, mock_engine):
        client.post("/auth", data={"code": "test-code-1"})
        resp = client.get("/")
        assert "invite" not in resp.text.lower()

    def test_valid_code_mints_opaque_token(self, client, auth_enabled):
        import web

        resp = client.post("/auth", data={"code": "test-code-1"})
        assert resp.json()["ok"] is True
        token = client.cookies.get("fala_session")
        assert token and token != "test-code-1"
        assert token in web._session_tokens
        assert web._session_tokens[token] == web._user_id_for_code("test-code-1")

    def test_invalid_code_rejected(self, client, auth_enabled):
        resp = client.post("/auth", data={"code": "wrong"})
        assert resp.json()["ok"] is False

    def test_unauthenticated_start_rejected(self, client, auth_enabled):
        resp = client.post("/start")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated."

    def test_authenticated_start_works(self, client, auth_enabled, mock_engine):
        client.post("/auth", data={"code": "test-code-1"})
        resp = client.post("/start")
        assert "Bem-vindo" in resp.json()["response"]


class TestHistory:
    def test_history_empty_before_start(self, client, mock_engine):
        resp = client.get("/history")
        assert resp.json() == {"messages": []}

    def test_history_returns_transcript(self, client, mock_engine):
        client.post("/start")
        resp = client.get("/history")
        data = resp.json()
        assert [m["role"] for m in data["messages"]] == ["tutor", "user"]

    def test_history_empty_after_quit(self, client, mock_engine):
        client.post("/start")
        client.post("/quit")
        resp = client.get("/history")
        assert resp.json() == {"messages": []}

    def test_history_tutor_entry_uses_stored_speech(self, client, mock_engine):
        mock_engine.get_history.return_value = [
            {"role": "tutor", "content": "Boa!", "speech": "Boa mesmo."},
            {"role": "user", "content": "olá"},
        ]
        client.post("/start")
        resp = client.get("/history")
        msgs = resp.json()["messages"]
        assert msgs[0]["content"] == "Boa!"
        assert msgs[0]["speech"] == "Boa mesmo."

    def test_history_normalizes_legacy_raw_say_content(self, client, mock_engine):
        """Legacy checkpoints store the RAW ---SAY--- response as content."""
        mock_engine.get_history.return_value = [
            {"role": "tutor", "content": "Boa!\n---SAY---\nBoa mesmo."},
        ]
        client.post("/start")
        resp = client.get("/history")
        m = resp.json()["messages"][0]
        assert "---SAY---" not in m["content"]
        assert m["content"] == "Boa!"
        assert m["speech"] == "Boa mesmo."

    def test_history_user_entries_pass_through(self, client, mock_engine):
        mock_engine.get_history.return_value = [{"role": "user", "content": "olá"}]
        client.post("/start")
        resp = client.get("/history")
        assert resp.json()["messages"] == [{"role": "user", "content": "olá"}]


class TestRateLimit:
    def test_rate_limit_returns_429(self, client, mock_engine, monkeypatch):
        import web

        monkeypatch.setattr(web, "RATE_LIMIT_PER_MIN", 3)
        client.post("/start")
        for _ in range(3):
            resp = client.post("/message", data={"text": "olá"})
            assert resp.status_code == 200
        resp = client.post("/message", data={"text": "olá de novo"})
        assert resp.status_code == 429
        assert "Too many requests" in resp.json()["detail"]

    def test_rate_limit_recovers_after_window(self, client, mock_engine, monkeypatch):
        import web

        monkeypatch.setattr(web, "RATE_LIMIT_PER_MIN", 2)
        client.post("/start")
        client.post("/message", data={"text": "a"})
        client.post("/message", data={"text": "b"})
        assert client.post("/message", data={"text": "c"}).status_code == 429
        # Rewind the recorded timestamps past the 60s window
        web._rate_windows = {k: [t - 61 for t in v] for k, v in web._rate_windows.items()}
        assert client.post("/message", data={"text": "d"}).status_code == 200


class TestSessionTokenCap:
    def test_token_map_capped_at_1000(self):
        """_session_tokens is bounded — oldest token evicted past the cap."""
        import web

        for i in range(web.MAX_SESSION_TOKENS + 10):
            web._remember_session_token(f"tok-{i}", f"user-{i}")

        assert len(web._session_tokens) == web.MAX_SESSION_TOKENS
        assert "tok-0" not in web._session_tokens  # oldest dropped
        assert f"tok-{web.MAX_SESSION_TOKENS + 9}" in web._session_tokens  # newest kept

    def test_existing_token_refreshed_not_evicted(self):
        import web

        web._remember_session_token("a", "u-a")
        for i in range(web.MAX_SESSION_TOKENS - 1):
            web._remember_session_token(f"filler-{i}", f"u-{i}")
        web._remember_session_token("a", "u-a")  # touch old token -> move_to_end
        for i in range(5):
            web._remember_session_token(f"new-{i}", f"u-{i}")
        assert "a" in web._session_tokens


class TestHealthz:
    def test_healthz(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestSecurityHeaders:
    def test_csp_and_nosniff_on_html(self, client):
        resp = client.get("/")
        assert "Content-Security-Policy" in resp.headers
        assert "default-src 'self'" in resp.headers["Content-Security-Policy"]
        assert resp.headers["X-Content-Type-Options"] == "nosniff"

    def test_cookie_flags(self, client, mock_engine):
        client.post("/start")
        set_cookie = client.cookies.get("fala_session")
        assert set_cookie  # cookie is set
        # Verify flags via a fresh response's Set-Cookie header
        resp = client.get("/stats")
        header = resp.headers.get("set-cookie", "")
        assert "HttpOnly" in header
        assert "SameSite=lax" in header
        assert "Max-Age" in header
        assert "Secure" not in header  # plain http in tests


class TestVoiceAuthGate:
    @pytest.fixture
    def auth_enabled(self):
        import web

        old_codes, old_enabled = web.AUTH_CODES, web.AUTH_ENABLED
        web.AUTH_CODES = {"test-code-1", "test-code-2"}
        web.AUTH_ENABLED = True
        web._sessions.clear()
        yield
        web.AUTH_CODES = old_codes
        web.AUTH_ENABLED = old_enabled

    def test_stt_requires_auth(self, client, auth_enabled):
        resp = client.post("/stt", files={"file": ("v.webm", b"x", "audio/webm")})
        assert resp.status_code == 401

    def test_tts_requires_auth(self, client, auth_enabled):
        resp = client.post("/tts", data={"text": "olá"})
        assert resp.status_code == 401

    def test_stt_works_when_authenticated(self, client, auth_enabled):
        client.post("/auth", data={"code": "test-code-1"})
        with patch("web.speech_to_text", return_value="olá tudo bem"):
            resp = client.post("/stt", files={"file": ("v.webm", b"x", "audio/webm")})
        assert resp.status_code == 200
        assert resp.json()["transcript"] == "olá tudo bem"

    def test_tts_works_when_authenticated(self, client, auth_enabled):
        client.post("/auth", data={"code": "test-code-1"})
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake-mp3")
            tmp = Path(f.name)
        with patch("web.text_to_speech", return_value=tmp):
            resp = client.post("/tts", data={"text": "olá"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/mpeg"


class TestResume:
    """End-to-end: a session checkpointed to disk survives a 'restart'."""

    def test_resume_after_restart(self, temp_data_dir, monkeypatch):
        import config
        import conversation
        import web

        monkeypatch.setattr(web, "DATA_DIR", config.DATA_DIR)
        monkeypatch.setattr(conversation, "LLM_API_KEY", "sk-test")
        monkeypatch.setattr(conversation, "OpenAI", MagicMock())
        replies = iter(["Bem-vindo! Vamos começar.", "Olá! Tudo bem?"])
        monkeypatch.setattr(
            conversation.ConversationEngine, "_call_llm", lambda self: next(replies)
        )

        from web import app

        # Phase 1: real session, warmup + one message, checkpoint written
        client = TestClient(app)
        r1 = client.post("/start")
        assert "Bem-vindo" in r1.json()["response"]
        client.post("/message", data={"text": "ola"})
        token = client.cookies.get("fala_session")
        user_id = web._session_tokens[token]
        assert user_id

        # Phase 2: simulate server restart — RAM session store is gone
        web._sessions.clear()

        client2 = TestClient(app)
        client2.cookies.set("fala_session", token)

        # History must be rebuilt from the on-disk checkpoint
        hist = client2.get("/history")
        assert hist.status_code == 200
        msgs = hist.json()["messages"]
        assert [m["role"] for m in msgs] == ["tutor", "user", "tutor"]
        assert msgs[0]["content"] == "Bem-vindo! Vamos começar."

        # /start resumes instead of re-running the warm-up
        r2 = client2.post("/start")
        assert r2.json()["resumed"] is True
        assert "resumed" in r2.json()["response"].lower()

    def test_quit_clears_checkpoint(self, temp_data_dir, monkeypatch):
        import config
        import conversation
        import web

        monkeypatch.setattr(web, "DATA_DIR", config.DATA_DIR)
        monkeypatch.setattr(conversation, "LLM_API_KEY", "sk-test")
        monkeypatch.setattr(conversation, "OpenAI", MagicMock())
        monkeypatch.setattr(conversation.ConversationEngine, "_call_llm", lambda self: "Bem-vindo!")

        from web import app

        client = TestClient(app)
        client.post("/start")
        token = client.cookies.get("fala_session")
        user_id = web._session_tokens[token]
        assert web._checkpoint_exists(user_id)

        client.post("/quit")
        assert not web._checkpoint_exists(user_id)


class TestSpeechChannel:
    def test_message_response_includes_speech_field(self, client, mock_engine):
        mock_engine.user_message.return_value = (
            "Boa! Veja isto.\n---SAY---\nBoa! Veja isto, sem markdown."
        )
        client.post("/start")
        resp = client.post("/message", data={"text": "olá"})
        data = resp.json()
        assert data["response"] == "Boa! Veja isto."
        assert data["speech"] == "Boa! Veja isto, sem markdown."

    def test_message_without_marker_speech_is_none(self, client, mock_engine):
        client.post("/start")
        resp = client.post("/message", data={"text": "olá"})
        data = resp.json()
        assert data["response"] == "Ótimo! Continue assim."
        assert data["speech"] is None

    def test_tts_endpoint_speaks_say_section_only(self, client, tmp_path):
        """POST /tts with a ---SAY--- response synthesizes only the SAY text."""
        audio_file = tmp_path / "x.mp3"
        audio_file.write_bytes(b"mp3")
        with patch("web.text_to_speech", return_value=audio_file) as mock_tts:
            resp = client.post(
                "/tts",
                data={"text": "Display text\n---SAY---\nSó isto se fala."},
            )
        assert resp.status_code == 200
        mock_tts.assert_called_once_with("Só isto se fala.")

    def test_tts_endpoint_without_marker_speaks_text(self, client, tmp_path):
        audio_file = tmp_path / "x.mp3"
        audio_file.write_bytes(b"mp3")
        with patch("web.text_to_speech", return_value=audio_file) as mock_tts:
            client.post("/tts", data={"text": "texto simples"})
        mock_tts.assert_called_once_with("texto simples")

    def test_html_page_has_no_tts_autoplay_on_load(self):
        """Autoplay on window.onload is silently blocked by browsers — must not exist."""
        from web import HTML_PAGE

        assert "playTTS(data.response)" not in HTML_PAGE
        assert "window.onload" in HTML_PAGE  # warmup still starts on load

    def test_html_page_has_replay_and_toggle(self):
        from web import HTML_PAGE

        assert "toggleTTS" in HTML_PAGE
        assert "localStorage.getItem('fala_tts')" in HTML_PAGE
        assert "replay-btn" in HTML_PAGE
        assert "audioCache" in HTML_PAGE


class TestWebHardening:
    @pytest.fixture
    def auth_enabled(self):
        import web

        old_codes, old_enabled = web.AUTH_CODES, web.AUTH_ENABLED
        web.AUTH_CODES = {"test-code-1", "test-code-2"}
        web.AUTH_ENABLED = True
        web._sessions.clear()
        yield
        web.AUTH_CODES = old_codes
        web.AUTH_ENABLED = old_enabled

    def test_secure_flag_behind_proxy(self):
        from unittest.mock import MagicMock

        import web

        plain = MagicMock()
        plain.url.scheme = "http"
        plain.headers = {}
        assert web._is_secure(plain) is False
        proxied = MagicMock()
        proxied.url.scheme = "http"
        proxied.headers = {"x-forwarded-proto": "https"}
        assert web._is_secure(proxied) is True

    def test_stt_timeout_returns_error(self, client, auth_enabled, monkeypatch):
        import time

        import web

        client.post("/auth", data={"code": "test-code-1"})
        monkeypatch.setattr(web, "STT_TIMEOUT_SECONDS", 0.1)
        with patch("web.speech_to_text", side_effect=lambda p: (time.sleep(0.5), "x")[1]):
            resp = client.post("/stt", files={"file": ("v.webm", b"x", "audio/webm")})
        assert resp.status_code == 200
        assert resp.json()["error"] == "Transcription timed out."
