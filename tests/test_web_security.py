"""Security tests for web.py — cookie opacity, invite-token auth, concurrency,
upload caps, and error-echo suppression. Companion to docs/research/audit-2026.md
findings 1, 3, 4 (plus upload/TTS hardening and error hygiene).
"""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from web import app


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
        instance.get_history.return_value = [{"role": "tutor", "content": "Bem-vindo!"}]
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_web_globals():
    import web

    web._sessions.clear()
    web._rate_windows.clear()
    web._session_tokens.clear()
    web._code_failures.clear()
    yield


@pytest.fixture
def auth_enabled():
    import web

    old_codes, old_enabled = web.AUTH_CODES, web.AUTH_ENABLED
    web.AUTH_CODES = {"test-code-1", "test-code-2"}
    web.AUTH_ENABLED = True
    yield
    web.AUTH_CODES = old_codes
    web.AUTH_ENABLED = old_enabled


class TestForgedCookie:
    """Finding 1: the raw cookie must never act as a user_id/storage key."""

    def test_forged_cookie_rejected_with_401(self, client, mock_engine):
        client.post("/start")  # establish a legit session
        attacker = TestClient(app)
        attacker.cookies.set("fala_session", "forged-arbitrary-token")
        resp = attacker.post("/start")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Not authenticated."

    def test_forged_cookie_cannot_touch_another_users_data(self, mock_engine):
        victim = TestClient(app)
        victim.post("/start")
        victim.post("/message", data={"text": "segredo"})

        attacker = TestClient(app)
        for forged in ("default", "victim", "a" * 32, "x" * 8):
            attacker.cookies.set("fala_session", forged)
            for path, method, kwargs in (
                ("/history", "GET", {}),
                ("/stats", "GET", {}),
                ("/message", "POST", {"data": {"text": "hello"}}),
            ):
                resp = getattr(attacker, method.lower())(path, **kwargs)
                assert resp.status_code == 401, f"{method} {path} with forged={forged!r}"

    def test_fresh_session_cannot_see_victims_transcript(self, mock_engine):
        victim = TestClient(app)
        victim.post("/start")
        victim.post("/message", data={"text": "segredo"})

        attacker = TestClient(app)  # no cookie — gets its own fresh identity
        attacker.post("/start")
        hist = attacker.get("/history").json()
        assert all("segredo" not in m["content"] for m in hist["messages"])

    def test_unknown_cookie_is_cleared_so_client_can_recover(self, client, mock_engine):
        client.cookies.set("fala_session", "stale-unknown-token")
        resp = client.post("/start")
        assert resp.status_code == 401
        # Server sends an expired Set-Cookie so a real browser drops the
        # stale cookie and its next request recovers with a fresh token.
        assert "fala_session=;" in resp.headers.get("set-cookie", "")
        assert "Max-Age=0" in resp.headers.get("set-cookie", "")
        recovered = TestClient(app)  # browser after dropping the cookie
        assert recovered.post("/start").status_code == 200

    def test_cookie_token_is_not_the_user_id(self, client, mock_engine):
        import web

        client.post("/start")
        token = client.cookies.get("fala_session")
        user_id = web._session_tokens[token]
        assert user_id != token  # cookie value is opaque, not a storage key
        assert token not in ("default", user_id)


class TestInviteTokenAuth:
    """Finding 3: the invite code never becomes the cookie or the user_id."""

    def test_login_mints_token_not_code(self, client, auth_enabled):
        import web

        resp = client.post("/auth", data={"code": "test-code-1"})
        assert resp.json()["ok"] is True
        token = client.cookies.get("fala_session")
        assert token
        assert token != "test-code-1"
        assert "test-code-1" not in token
        # Server-side mapping resolves to a derived user_id, not the code.
        assert web._session_tokens[token] == web._user_id_for_code("test-code-1")
        assert web._session_tokens[token] != "test-code-1"

    def test_forged_code_as_cookie_fails(self, client, auth_enabled):
        client.cookies.set("fala_session", "test-code-2")  # attacker knows the code...?
        # Even with a valid code as the cookie, it is not a token -> rejected.
        resp = client.post("/start")
        assert resp.status_code == 401

    def test_code_comparison_is_constant_time_path(self, client, auth_enabled):
        """Wrong code length / content must not 500 (compare_digest path)."""
        for bad in ("x", "a" * 500, "tëst-code-1", "test-code-1 extra", "test-code-2x"):
            resp = client.post("/auth", data={"code": bad})
            assert resp.status_code == 200
            assert resp.json()["ok"] is False

    def test_per_code_lockout_after_repeated_failures(self, client, auth_enabled, monkeypatch):
        import web

        monkeypatch.setattr(web, "CODE_MAX_FAILURES", 3)
        monkeypatch.setattr(web, "CODE_LOCKOUT_SECONDS", 300)
        for _ in range(3):
            resp = client.post("/auth", data={"code": "guess-me"})
            assert resp.json()["ok"] is False
        # The brute-forced code string is now locked out even before the
        # per-IP rate limit (3 < 30) would trip.
        resp = client.post("/auth", data={"code": "guess-me"})
        assert resp.json()["ok"] is False
        assert "Too many attempts" in resp.json()["error"]

    def test_lockout_does_not_block_other_codes(self, client, auth_enabled, monkeypatch):
        import web

        monkeypatch.setattr(web, "CODE_MAX_FAILURES", 2)
        monkeypatch.setattr(web, "CODE_LOCKOUT_SECONDS", 300)
        for _ in range(5):
            client.post("/auth", data={"code": "wrong-code"})
        resp = client.post("/auth", data={"code": "test-code-1"})
        assert resp.json()["ok"] is True

    def test_successful_login_clears_failure_count(self, client, auth_enabled):
        import web

        web.CODE_MAX_FAILURES = 3
        client.post("/auth", data={"code": "oops"})
        client.post("/auth", data={"code": "oops"})
        assert client.post("/auth", data={"code": "test-code-1"}).json()["ok"] is True
        assert "test-code-1" not in web._code_failures


class TestSessionConcurrency:
    """Finding 4: /message racing /quit must not corrupt session state."""

    def test_message_then_quit_serialized(self, mock_engine):
        client = TestClient(app)
        client.post("/start")
        token = client.cookies.get("fala_session")

        mock_engine.user_message.side_effect = lambda text: (
            time.sleep(0.2),
            "Ótimo! Continue assim.",
        )[1]

        results = {}

        def do_message():
            c = TestClient(app)
            c.cookies.set("fala_session", token)
            r = c.post("/message", data={"text": "olá"})
            results["message"] = (r.status_code, r.json())

        def do_quit():
            time.sleep(0.05)  # /message acquires the lock first
            c = TestClient(app)
            c.cookies.set("fala_session", token)
            r = c.post("/quit")
            results["quit"] = (r.status_code, r.json())

        t1, t2 = threading.Thread(target=do_message), threading.Thread(target=do_quit)
        t1.start()
        time.sleep(0.02)
        t2.start()
        t1.join(5)
        t2.join(5)

        assert results["message"][0] == 200
        assert results["message"][1]["response"] == "Ótimo! Continue assim."
        assert results["quit"][0] == 200
        assert results["quit"][1]["response"] == "Até logo!"
        # Final state is consistent: ended, engine dropped, no half-state.
        state = __import__("web")._sessions[token]
        assert state.session_ended is True
        assert state.engine is None

    def test_quit_then_message_gets_clean_error(self, mock_engine):
        import web

        client = TestClient(app)
        client.post("/start")
        token = client.cookies.get("fala_session")

        mock_engine.end_session.side_effect = lambda: (time.sleep(0.2), "Até logo!")[1]

        results = {}

        def do_quit():
            c = TestClient(app)
            c.cookies.set("fala_session", token)
            r = c.post("/quit")
            results["quit"] = (r.status_code, r.json())

        def do_message():
            time.sleep(0.05)  # /quit acquires the lock first
            c = TestClient(app)
            c.cookies.set("fala_session", token)
            r = c.post("/message", data={"text": "olá"})
            results["message"] = (r.status_code, r.json())

        t1, t2 = threading.Thread(target=do_quit), threading.Thread(target=do_message)
        t1.start()
        time.sleep(0.02)
        t2.start()
        t1.join(5)
        t2.join(5)

        assert results["quit"][1]["response"] == "Até logo!"
        assert results["message"][0] == 200
        # In-flight /message waited on the lock, saw session_ended, and got a
        # clean error — the engine was never touched after quit.
        assert "Session ended" in results["message"][1]["response"]
        mock_engine.user_message.assert_not_called()
        state = web._sessions[token]
        assert state.session_ended is True
        assert state.engine is None


class TestUploadLimits:
    def test_oversize_stt_rejected_413(self, client):
        big = b"x" * (10 * 1024 * 1024 + 1)
        with patch("web.speech_to_text") as stt_mock:
            resp = client.post("/stt", files={"file": ("voice.webm", big, "audio/webm")})
        assert resp.status_code == 413
        stt_mock.assert_not_called()

    def test_oversize_exactly_at_limit_accepted(self, client):
        ok = b"x" * (10 * 1024 * 1024)
        with patch("web.speech_to_text", return_value="olá"):
            resp = client.post("/stt", files={"file": ("voice.webm", ok, "audio/webm")})
        assert resp.status_code == 200
        assert resp.json()["transcript"] == "olá"

    @pytest.mark.parametrize("name", ["evil.exe", "notes.txt", "voice.flac", "noext", ""])
    def test_disallowed_suffix_rejected_415(self, client, name):
        with patch("web.speech_to_text") as stt_mock:
            resp = client.post(
                "/stt",
                files={"file": (name or "x", b"audio", "application/octet-stream")},
            )
        assert resp.status_code == 415
        stt_mock.assert_not_called()

    @pytest.mark.parametrize("name", ["a.wav", "b.mp3", "c.webm", "d.ogg", "e.m4a"])
    def test_allowed_suffixes_accepted(self, client, name):
        with patch("web.speech_to_text", return_value="olá"):
            resp = client.post("/stt", files={"file": (name, b"audio", "audio/mpeg")})
        assert resp.status_code == 200

    def test_stt_error_does_not_echo_exception(self, client):
        with patch("web.speech_to_text", side_effect=RuntimeError("/home/alex/secret")):
            resp = client.post("/stt", files={"file": ("voice.webm", b"x", "audio/webm")})
        data = resp.json()
        assert data["transcript"] == ""
        assert "secret" not in data["error"]
        assert data["error"] == "Transcription failed."


class TestTTSLimits:
    def test_long_text_rejected_400(self, client):
        with patch("web.text_to_speech") as tts_mock:
            resp = client.post("/tts", data={"text": "a" * 4001})
        assert resp.status_code == 400
        assert "too long" in resp.json()["detail"].lower()
        tts_mock.assert_not_called()

    def test_text_at_limit_accepted(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"fake-mp3")
            tmp = Path(f.name)
        with patch("web.text_to_speech", return_value=tmp):
            client = TestClient(app)
            resp = client.post("/tts", data={"text": "a" * 4000})
        assert resp.status_code == 200

    def test_tts_error_does_not_echo_exception(self, client):
        with patch("web.text_to_speech", side_effect=RuntimeError("api key sk-live-123")):
            resp = client.post("/tts", data={"text": "olá"})
        assert resp.status_code == 200
        data = resp.json()
        assert "sk-live-123" not in str(data)
        assert data["error"] == "Speech synthesis failed."


class TestRateWindowBounds:
    def test_stale_windows_pruned(self, monkeypatch):
        import web

        now = time.time()
        # 500 stale keys + a few live ones
        for i in range(500):
            web._rate_windows[f"ip:10.0.0.{i}"] = [now - 120]
        web._rate_windows["ip:live"] = [now - 1]
        web._rate_last_prune = 0.0  # force prune on next check
        web._rate_limited("ip:new")
        assert len(web._rate_windows) <= 2
        assert "ip:live" in web._rate_windows

    def test_windows_stay_bounded_under_churn(self, client, mock_engine, monkeypatch):
        import web

        monkeypatch.setattr(web, "RATE_LIMIT_PER_MIN", 100000)
        for i in range(300):
            c = TestClient(app)
            c.cookies.set("fala_session", f"tok-{i}")
            c.get("/stats")
        assert len(web._rate_windows) < 300  # old entries pruned along the way
