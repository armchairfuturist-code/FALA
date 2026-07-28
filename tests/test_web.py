"""Tests for web.py — FastAPI endpoints wrapping ConversationEngine."""

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
        mock_cls.return_value = instance
        yield instance


@pytest.fixture(autouse=True)
def reset_web_globals():
    """Reset the web module's session store before each test."""
    import web

    web._sessions.clear()
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

    def test_double_start_returns_already_active(self, client, mock_engine):
        client.post("/start")  # first call
        resp = client.post("/start")  # second call
        data = resp.json()
        assert "already started" in data["response"].lower()
        assert data["status"] == "already active"
        # start_warmup should only be called once
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
        assert "No active session" in data["response"]


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
