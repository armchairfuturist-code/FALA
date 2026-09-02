"""Tests for conversation.py — ConversationEngine."""

import json
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from config import CONTEXT_MESSAGES, GUARDRAILS


@pytest.fixture(autouse=True)
def _hermetic_llm(monkeypatch):
    """No real API key needed: ConversationEngine checks the module-level
    key at construction time, so patch it for every test."""
    monkeypatch.setattr("conversation.LLM_API_KEY", "test-key-not-real")


# ---------------------------------------------------------------------------
# Helper: build a minimal fake OpenAI response
# ---------------------------------------------------------------------------


def _fake_choice(text: str):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    return choice


def _fake_completion(text: str):
    resp = MagicMock()
    resp.choices = [_fake_choice(text)]
    return resp


# ---------------------------------------------------------------------------
# _extract_level
# ---------------------------------------------------------------------------


class TestExtractLevel:
    def _make_engine(self, summary_text=""):
        """Return an engine with a fake summary."""
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=summary_text):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()
        return engine

    def test_default_level(self):
        engine = self._make_engine("No level info here")
        assert engine._extract_level() == "A0"

    def test_parses_a1(self):
        engine = self._make_engine("- Current level: A1\n- Sessions: 0")
        assert engine._extract_level() == "A1"

    def test_parses_a2(self):
        engine = self._make_engine("- Current level: A2")
        assert engine._extract_level() == "A2"

    def test_parses_b1(self):
        engine = self._make_engine("- Current level: B1")
        assert engine._extract_level() == "B1"

    def test_parses_c2(self):
        engine = self._make_engine("- Current level: C2")
        assert engine._extract_level() == "C2"

    def test_substring_fallback_prefers_first_level_not_last(self):
        """'A1 (goal B1)' must yield A1 — the fallback scans in fixed order."""
        engine = self._make_engine("- Current level: A1 (goal B1)")
        assert engine._extract_level() == "A1"

    def test_fallback_is_deterministic_on_equal_length_levels(self):
        """Old code iterated a set: A2/B2 tie resolved nondeterministically."""
        line = "- Current level: moving from A2 towards B2"
        results = {self._make_engine(line)._extract_level() for _ in range(10)}
        assert results == {"A2"}

    def test_strict_parse_strips_trailing_punctuation(self):
        engine = self._make_engine("- Current level: B1.")
        assert engine._extract_level() == "B1"

    def test_current_level_beats_other_level_mentions(self):
        """A 'Current level' line wins even if other lines mention levels."""
        engine = self._make_engine("- Weakness: B2 listening\n- Current level: A1")
        assert engine._extract_level() == "A1"


# ---------------------------------------------------------------------------
# get_status_report
# ---------------------------------------------------------------------------


class TestGetStatusReport:
    def _make_engine(self, summary_text="", vocab=None):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=summary_text):
                with patch("conversation.load_vocabulary", return_value=vocab or []):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()
        return engine

    def test_shows_level_and_date(self):
        engine = self._make_engine("- Current level: A2")
        report = engine.get_status_report()
        assert "Level: A2" in report
        assert "Session started:" in report

    def test_no_words_due_no_count(self):
        engine = self._make_engine("- Current level: A1\n- Sessions completed: 0")
        report = engine.get_status_report()
        assert "Words due" not in report

    def test_sessions_positive_shows_count(self):
        engine = self._make_engine("- Current level: A1\n- Sessions completed: 3")
        report = engine.get_status_report()
        assert "Sessions: 3" in report

    def test_sessions_with_trailing_prose_parsed_tolerantly(self):
        """The summary is LLM-written: '3 (this month)' must still parse as 3."""
        engine = self._make_engine("- Current level: A1\n- Sessions completed: 3 (this month)")
        report = engine.get_status_report()
        assert "Sessions: 3" in report


# ---------------------------------------------------------------------------
# _build_system_prompt
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt:
    def test_formats_template_with_level_and_vocab(self, tmp_path):
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "system.md").write_text(
            "Level: {level}\nSummary: {summary}\nVocab: {vocabulary}"
        )

        from conversation import ConversationEngine

        with patch("conversation.PROMPTS_DIR", prompts_dir):
            with patch("conversation.load_summary", return_value="test summary"):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.get_vocab_for_prompt", return_value="(none)"):
                        with patch("conversation.OpenAI"):
                            engine = ConversationEngine()

        assert engine.messages[0]["role"] == "system"
        content = engine.messages[0]["content"]
        assert "Level: A0" in content
        assert "Summary: test summary" in content
        assert "Vocab: (none)" in content


# ---------------------------------------------------------------------------
# start_warmup
# ---------------------------------------------------------------------------


class TestStartWarmup:
    def test_returns_tutor_text(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion("Bem-vindo! Vamos começar.")
                        )
                        engine = ConversationEngine()
                        engine._call_llm = lambda: "Bem-vindo! Vamos começar."
                        result = engine.start_warmup()
                        assert "Bem-vindo" in result
                        # Warm-up keeps the exchange: user prompt (now the
                        # concise marker) + assistant greeting
                        assert [m["role"] for m in engine.messages] == ["user", "assistant"]

    def test_second_call_returns_early_no_extra_message(self):
        """Calling start_warmup() twice does not append a second prompt."""
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion("Bem-vindo!")
                        )
                        engine = ConversationEngine()
                        engine._call_llm = lambda: "Bem-vindo!"

                        # First call — user prompt (replaced by marker) +
                        # assistant greeting stay in the message list
                        engine.start_warmup()
                        assert len(engine.messages) == 2
                        assert engine._warmup_done is True

                        # Second call — should be a no-op, no extra messages
                        result = engine.start_warmup()
                        assert len(engine.messages) == 2  # no extra messages
                        assert "already completed" in result

    def test_second_call_does_not_invoke_llm(self):
        """Second call to start_warmup() must not call _call_llm."""
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion("Bem-vindo!")
                        )
                        engine = ConversationEngine()
                        call_count = 0
                        original_llm = engine._call_llm

                        def counting_llm():
                            nonlocal call_count
                            call_count += 1
                            return original_llm()

                        engine._call_llm = counting_llm

                        engine.start_warmup()
                        first_count = call_count
                        engine.start_warmup()
                        assert call_count == first_count  # no extra LLM call


# ---------------------------------------------------------------------------
# user_message and _extract_vocab_from_exchange
# ---------------------------------------------------------------------------


class TestUserMessage:
    def test_appends_to_log_and_returns(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()

        engine._call_llm = lambda: "Muito bem!"
        engine._extract_vocab_from_exchange = MagicMock()
        result = engine.user_message("Olá", is_voice=False)
        assert result == "Muito bem!"
        assert any("[user] Olá" in line for line in engine.session_log)

    def test_voice_prefix(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()

        engine._call_llm = lambda: "ok"
        engine._extract_vocab_from_exchange = MagicMock()
        engine.user_message("sim", is_voice=True)
        # The user msg in messages should have [voice] prefix
        assert "[voice] sim" in str(engine.messages)


class TestHistorySpeechSplit:
    """History stores display text + speech, never the raw ---SAY--- response
    (verification N3): resume rendering must not show the marker as chat text."""

    def _make_engine(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()
        engine._extract_vocab_from_exchange = MagicMock()
        return engine

    def test_user_message_history_stores_display_and_speech(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()

        engine._call_llm = lambda: "Boa! Veja isto.\n---SAY---\nBoa! Veja isto."
        engine.user_message("olá")

        entry = engine.history[-1]
        assert entry["role"] == "tutor"
        assert "---SAY---" not in entry["content"]
        assert entry["content"] == "Boa! Veja isto."
        assert entry["speech"] == "Boa! Veja isto."

    def test_user_message_without_marker_speech_is_none(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()

        engine._call_llm = lambda: "Muito bem!"
        engine._extract_vocab_from_exchange = MagicMock()
        engine.user_message("olá")

        entry = engine.history[-1]
        assert entry["content"] == "Muito bem!"
        assert entry["speech"] is None

    def test_warmup_history_stores_display_and_speech(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()

        with patch(
            "conversation.ConversationEngine._call_llm",
            return_value="Bem-vindo!\n---SAY---\nBem-vindo!",
        ):
            engine.start_warmup()

        entry = engine.history[-1]
        assert entry["content"] == "Bem-vindo!"
        assert entry["speech"] == "Bem-vindo!"

    def test_llm_context_keeps_raw_response_with_marker(self):
        """self.messages (LLM context) must keep the RAW response, not display."""
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()

        raw = "Boa!\n---SAY---\nBoa mesmo."
        with patch("conversation.ConversationEngine._call_llm", return_value=raw):
            engine.user_message("olá")

        assert engine.messages[-1]["content"] == raw

    def test_checkpoint_roundtrip_preserves_display_and_speech(self, tmp_path):
        from config import UserPaths
        from conversation import ConversationEngine

        data_dir = tmp_path / "ud"
        (data_dir / "sessions").mkdir(parents=True)
        (data_dir / "records").mkdir(parents=True)
        paths = UserPaths(
            user_id="u1",
            data_dir=data_dir,
            summary=data_dir / "summary.md",
            vocabulary=data_dir / "vocabulary.md",
            sessions=data_dir / "sessions",
            records=data_dir / "records",
        )
        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()
        engine.paths = paths
        with patch(
            "conversation.ConversationEngine._call_llm",
            return_value="Boa!\n---SAY---\nBoa!",
        ):
            engine.start_warmup()

        fresh = self._roundtrip_engine(paths)
        assert fresh.load_checkpoint() is True
        entry = fresh.history[-1]
        assert "---SAY---" not in entry["content"]
        assert entry["content"] == "Boa!"
        assert entry["speech"] == "Boa!"

    @staticmethod
    def _roundtrip_engine(paths):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        fresh = ConversationEngine()
        fresh.paths = paths
        return fresh


class TestExtractVocabFromExchange:
    def test_extracts_json_words(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion(
                                '{"new_words": [{"word": "livro", "english": "book", '
                                '"context": "O livro é azul."}], "assessments": []}'
                            )
                        )
                        engine = ConversationEngine()
                        engine.vocabulary = []
                        engine._extract_vocab_from_exchange("user", "tutor")
                        assert len(engine.vocabulary) == 1
                        assert engine.vocabulary[0]["word"] == "livro"

    def test_handles_markdown_wrapped_json(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion(
                                '```json\n{"new_words": [{"word": "casa", '
                                '"english": "house", "context": ""}], '
                                '"assessments": []}\n```'
                            )
                        )
                        engine = ConversationEngine()
                        engine.vocabulary = []
                        engine._extract_vocab_from_exchange("x", "y")
                        assert len(engine.vocabulary) == 1

    def test_handles_empty_response(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion('{"new_words": [], "assessments": []}')
                        )
                        engine = ConversationEngine()
                        engine.vocabulary = []
                        engine._extract_vocab_from_exchange("x", "y")
                        assert len(engine.vocabulary) == 0

    def test_handles_invalid_json_gracefully(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion("this is not json")
                        )
                        engine = ConversationEngine()
                        engine.vocabulary = [{"word": "existing"}]
                        engine._extract_vocab_from_exchange("x", "y")
                        assert len(engine.vocabulary) == 1

    def test_processes_assessments(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion(
                                '{"new_words": [], "assessments": '
                                '[{"word": "olá", "correct": true}]}'
                            )
                        )
                        engine = ConversationEngine()
                        engine.vocabulary = [
                            {
                                "word": "olá",
                                "english": "hello",
                                "ease": 2.5,
                                "interval": 1,
                                "last_reviewed": "2026-01-01",
                                "confidence": 0.5,
                                "needs_review": True,
                            }
                        ]
                        engine._extract_vocab_from_exchange("Olá!", "Boa! Olá!")
                        entry = engine.vocabulary[0]
                        assert entry["confidence"] == 0.65  # 0.5 + 0.15
                        assert entry["interval"] > 1
                        assert entry["last_reviewed"] != "2026-01-01"

    def test_assessment_wrong_answer_resets_interval(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion(
                                '{"new_words": [], "assessments": '
                                '[{"word": "bom", "correct": false}]}'
                            )
                        )
                        engine = ConversationEngine()
                        engine.vocabulary = [
                            {
                                "word": "bom",
                                "english": "good",
                                "ease": 2.5,
                                "interval": 5,
                                "last_reviewed": "2026-06-01",
                                "confidence": 0.7,
                                "needs_review": False,
                            }
                        ]
                        engine._extract_vocab_from_exchange("bom dia", "correction")
                        entry = engine.vocabulary[0]
                        assert entry["confidence"] == pytest.approx(0.5, rel=1e-6)  # 0.7 - 0.2
                        assert entry["interval"] == 1
                        assert entry["needs_review"] is True


# ---------------------------------------------------------------------------
# Per-user paths / isolation
# ---------------------------------------------------------------------------


class TestPerUserPaths:
    def _make_engine(self, user_id="default"):
        """Engine with mocked LLM + real (tmp) per-user filesystem."""
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.OpenAI") as mock_client:
                mock_client.return_value.chat.completions.create.return_value = _fake_completion(
                    "new summary"
                )
                return ConversationEngine(user_id=user_id)

    def _patch_data_dir(self, monkeypatch, tmp_path):
        import config

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        monkeypatch.setattr(config, "DATA_DIR", data_dir)
        return data_dir

    def test_default_user_resolves_flat_paths(self, tmp_path, monkeypatch):
        import config

        data_dir = self._patch_data_dir(monkeypatch, tmp_path)
        (data_dir / "sessions").mkdir()
        (data_dir / "records").mkdir()
        monkeypatch.setattr(config, "SUMMARY_PATH", data_dir / "summary.md")
        monkeypatch.setattr(config, "VOCABULARY_PATH", data_dir / "vocabulary.md")
        monkeypatch.setattr(config, "SESSIONS_DIR", data_dir / "sessions")
        monkeypatch.setattr(config, "RECORDS_DIR", data_dir / "records")

        engine = self._make_engine()
        assert engine.user_id == "default"
        assert engine.paths.summary == data_dir / "summary.md"
        assert engine.paths.vocabulary == data_dir / "vocabulary.md"
        assert engine.paths.sessions == data_dir / "sessions"
        assert engine.paths.records == data_dir / "records"

    def test_vocab_isolated_between_users(self, tmp_path, monkeypatch):
        data_dir = self._patch_data_dir(monkeypatch, tmp_path)

        alice = self._make_engine("alice")
        alice.vocabulary = [
            {
                "word": "livro",
                "english": "book",
                "context": "O livro é azul.",
                "ease": 2.5,
                "interval": 1,
                "last_reviewed": "2026-07-28",
                "confidence": 0.3,
                "needs_review": True,
            }
        ]
        result = alice.end_session()
        assert "Session saved" in result

        # Bob sees none of Alice's words
        bob = self._make_engine("bob")
        assert bob.vocabulary == []

        # Alice's data persists across engine instances
        alice2 = self._make_engine("alice")
        assert [e["word"] for e in alice2.vocabulary] == ["livro"]

        # Files land under data/users/<id>/; the flat default layout is untouched
        assert (data_dir / "users" / "alice" / "vocabulary.md").exists()
        assert (data_dir / "users" / "alice" / "summary.md").exists()
        assert not (data_dir / "vocabulary.md").exists()
        assert not (data_dir / "summary.md").exists()

    def test_engines_do_not_share_state(self, tmp_path, monkeypatch):
        self._patch_data_dir(monkeypatch, tmp_path)
        alice = self._make_engine("alice")
        bob = self._make_engine("bob")
        assert alice.paths != bob.paths
        alice.vocabulary.append({"word": "casa", "english": "house"})
        assert bob.vocabulary == []

    def test_invalid_user_id_raises(self):
        from conversation import ConversationEngine

        with patch("conversation.OpenAI"):
            with pytest.raises(ValueError):
                ConversationEngine(user_id="../evil")


# ---------------------------------------------------------------------------
# end_session
# ---------------------------------------------------------------------------


class TestEndSession:
    def test_saves_vocab_and_returns_string(self, tmp_path):
        import config

        old_summary_path = config.SUMMARY_PATH
        old_vocab_path = config.VOCABULARY_PATH
        old_sessions_dir = config.SESSIONS_DIR

        # Point to tmp
        config.SUMMARY_PATH = tmp_path / "summary.md"
        config.VOCABULARY_PATH = tmp_path / "vocabulary.md"
        config.SESSIONS_DIR = tmp_path / "sessions"
        config.SESSIONS_DIR.mkdir()

        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value="- Current level: A1"):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()

        engine.new_words = [{"word": "teste", "english": "test"}]

        with patch("conversation.save_summary"):
            with patch("conversation.ConversationEngine._call_llm", return_value="new summary"):
                result = engine.end_session()

        assert "teste" in str(engine.new_words)
        assert "Session saved" in result

        # Restore
        config.SUMMARY_PATH = old_summary_path
        config.VOCABULARY_PATH = old_vocab_path
        config.SESSIONS_DIR = old_sessions_dir

    def test_graduated_words_save_learning_record(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value="- Current level: A1"):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()

        engine.new_words = [{"word": "aprendido", "english": "learned"}]
        engine.vocabulary = [
            {
                "word": "aprendido",
                "english": "learned",
                "ease": 2.5,
                "interval": 30,
                "last_reviewed": "2026-07-04",
                "confidence": 0.85,
                "needs_review": False,
            }
        ]

        with patch("conversation.save_summary"):
            with patch("conversation.save_vocabulary"):
                with patch("conversation.save_learning_record") as mock_save:
                    with patch(
                        "conversation.ConversationEngine._call_llm",
                        return_value="new summary",
                    ):
                        result = engine.end_session()

        assert "1 words learned" in result
        mock_save.assert_called_once()
        args, _ = mock_save.call_args
        assert "aprendido" in args[0]

    def test_no_graduated_words_no_record(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value="- Current level: A1"):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()

        engine.new_words = []
        engine.vocabulary = []

        with patch("conversation.save_summary"):
            with patch("conversation.save_vocabulary"):
                with patch("conversation.save_learning_record") as mock_save:
                    with patch(
                        "conversation.ConversationEngine._call_llm",
                        return_value="new summary",
                    ):
                        result = engine.end_session()

        assert "0 words learned" in result
        assert "Session saved" in result
        mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# Session checkpoints
# ---------------------------------------------------------------------------


class TestCheckpoint:
    """Checkpoint save/restore/clear + lifecycle hooks."""

    def _make_engine(self, tmp_path, vocab=None):
        from config import UserPaths
        from conversation import ConversationEngine

        data_dir = tmp_path / "user-data"
        sessions = data_dir / "sessions"
        records = data_dir / "records"
        sessions.mkdir(parents=True, exist_ok=True)
        records.mkdir(parents=True, exist_ok=True)
        paths = UserPaths(
            user_id="u1",
            data_dir=data_dir,
            summary=data_dir / "summary.md",
            vocabulary=data_dir / "vocabulary.md",
            sessions=sessions,
            records=records,
        )

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value="- Current level: A0"):
                with patch("conversation.load_vocabulary", return_value=vocab or []):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()
        engine.paths = paths
        return engine

    def test_no_checkpoint_initially(self, tmp_path):
        engine = self._make_engine(tmp_path)
        assert not engine.has_checkpoint()

    def test_save_then_load_roundtrip(self, tmp_path):
        engine = self._make_engine(tmp_path)
        engine.session_start = datetime(2026, 8, 6, 10, 30, 0)
        engine.messages = [
            {"role": "system", "content": "sys"},
            {"role": "assistant", "content": "Olá!"},
        ]
        engine.new_words = [{"word": "olá", "english": "hello", "context": "Olá!"}]
        engine.vocabulary = [
            {
                "word": "obrigado",
                "english": "thank you",
                "context": "",
                "ease": 2.5,
                "interval": 1,
                "last_reviewed": "2026-08-06",
                "confidence": 0.3,
                "needs_review": True,
            }
        ]
        engine._warmup_done = True

        engine.save_checkpoint()
        assert engine.has_checkpoint()

        fresh = self._make_engine(tmp_path)
        assert fresh.messages != engine.messages  # untouched until load
        assert fresh.load_checkpoint() is True
        assert fresh.session_start == engine.session_start
        assert fresh.messages == engine.messages
        assert fresh.new_words == engine.new_words
        assert fresh.vocabulary == engine.vocabulary
        assert fresh._warmup_done is True

    def test_load_without_checkpoint_returns_false(self, tmp_path):
        engine = self._make_engine(tmp_path)
        assert engine.load_checkpoint() is False

    def test_clear_checkpoint_removes_file(self, tmp_path):
        engine = self._make_engine(tmp_path)
        engine.save_checkpoint()
        engine.clear_checkpoint()
        assert not engine.has_checkpoint()

    def test_start_warmup_saves_checkpoint(self, tmp_path):
        engine = self._make_engine(tmp_path)
        with patch("conversation.ConversationEngine._call_llm", return_value="Bem-vindo!"):
            engine.start_warmup()
        assert engine.has_checkpoint()

    def test_user_message_saves_checkpoint(self, tmp_path):
        engine = self._make_engine(tmp_path)
        with patch("conversation.ConversationEngine._call_llm", return_value="Olá!"):
            engine.start_warmup()
        with patch("conversation.ConversationEngine._call_llm", return_value="Ótimo!"):
            engine.user_message("oi")
        assert engine.has_checkpoint()

    def test_end_session_clears_checkpoint(self, tmp_path):
        engine = self._make_engine(tmp_path)
        engine._warmup_done = True
        engine.save_checkpoint()
        assert engine.has_checkpoint()

        with patch("conversation.save_summary"):
            with patch("conversation.save_vocabulary"):
                with patch("conversation.save_learning_record"):
                    result = engine.end_session()

        assert "Session saved" in result
        assert not engine.has_checkpoint()


# ---------------------------------------------------------------------------
# Per-session new-word cap (audit 2026 #2)
# ---------------------------------------------------------------------------


class TestPerSessionWordCap:
    CAP = GUARDRAILS["max_new_words_per_session"]

    def _make_engine(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()
        return engine

    def _exchange_with_words(self, engine, i: int, count: int):
        """Run one vocab extraction whose LLM returns `count` new words."""
        words = [{"word": f"w{i}-{j}", "english": f"e{i}-{j}", "context": ""} for j in range(count)]
        engine.client.chat.completions.create.return_value = _fake_completion(
            json.dumps({"new_words": words, "assessments": []})
        )
        engine._extract_vocab_from_exchange(f"user {i}", f"tutor {i}")

    def test_six_exchanges_cannot_exceed_cap(self):
        """6 exchanges x 3 words would be 18 under per-call capping."""
        engine = self._make_engine()
        for i in range(6):
            self._exchange_with_words(engine, i, 3)
        assert len(engine.new_words) == self.CAP
        assert len({w["word"] for w in engine.new_words}) == self.CAP

    def test_final_exchange_is_sliced_not_dropped(self):
        """Cap 5: 3 words then 3 more -> only 2 from the second exchange."""
        engine = self._make_engine()
        self._exchange_with_words(engine, 0, 3)
        self._exchange_with_words(engine, 1, 3)
        assert len(engine.new_words) == self.CAP
        assert [w["word"] for w in engine.new_words] == [
            "w0-0",
            "w0-1",
            "w0-2",
            "w1-0",
            "w1-1",
        ]

    def test_extraction_llm_call_skipped_once_cap_reached(self):
        engine = self._make_engine()
        self._exchange_with_words(engine, 0, self.CAP)
        create_mock = engine.client.chat.completions.create
        calls_at_cap = create_mock.call_count
        for i in range(3):
            self._exchange_with_words(engine, 10 + i, 2)
        assert create_mock.call_count == calls_at_cap
        assert len(engine.new_words) == self.CAP


# ---------------------------------------------------------------------------
# Vocab extraction failure -> logged warning, no crash (audit 2026 #6)
# ---------------------------------------------------------------------------


class TestVocabExtractionErrorHandling:
    def _make_engine_with_raising_llm(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.side_effect = RuntimeError(
                            "api auth failed"
                        )
                        engine = ConversationEngine()
        return engine

    def test_llm_failure_does_not_crash_and_logs_warning(self, caplog):
        engine = self._make_engine_with_raising_llm()
        with caplog.at_level(logging.WARNING, logger="conversation"):
            engine._extract_vocab_from_exchange("olá", "Olá! Tudo bem?")
        assert len(engine.vocabulary) == 0
        assert any("Vocabulary extraction failed" in r.message for r in caplog.records)
        assert any(r.exc_info for r in caplog.records)

    def test_vocab_extraction_passes_timeout(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion('{"new_words": [], "assessments": []}')
                        )
                        engine = ConversationEngine()
        engine._extract_vocab_from_exchange("x", "y")
        _, kwargs = engine.client.chat.completions.create.call_args
        assert kwargs["timeout"] == 30


# ---------------------------------------------------------------------------
# end_session: summary LLM failure is loud, not silent (audit 2026 #20)
# ---------------------------------------------------------------------------


class TestEndSessionSummaryFailure:
    def _make_engine(self, tmp_path):
        from config import UserPaths
        from conversation import ConversationEngine

        data_dir = tmp_path / "user-data"
        (data_dir / "sessions").mkdir(parents=True)
        (data_dir / "records").mkdir(parents=True)
        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value="- Current level: A1"):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.side_effect = RuntimeError(
                            "api down"
                        )
                        engine = ConversationEngine()
        engine.paths = UserPaths(
            user_id="u1",
            data_dir=data_dir,
            summary=data_dir / "summary.md",
            vocabulary=data_dir / "vocabulary.md",
            sessions=data_dir / "sessions",
            records=data_dir / "records",
        )
        return engine

    def test_summary_failure_does_not_crash_and_is_loud(self, tmp_path, caplog):

        engine = self._make_engine(tmp_path)
        with patch("conversation.save_summary") as mock_save_summary:
            with patch("conversation.save_vocabulary"):
                with patch("conversation.save_learning_record"):
                    with caplog.at_level(logging.WARNING, logger="conversation"):
                        result = engine.end_session()
        # No crash; summary never saved; message does not claim full success
        mock_save_summary.assert_not_called()
        assert "summary update failed" in result
        assert any("Session summary update failed" in r.message for r in caplog.records)

    def test_summary_success_still_reports_saved(self, tmp_path):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value="- Current level: A1"):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion("updated summary")
                        )
                        engine = ConversationEngine()
        data_dir = engine.paths.data_dir
        (data_dir / "sessions").mkdir(parents=True, exist_ok=True)
        (data_dir / "records").mkdir(parents=True, exist_ok=True)
        with patch("conversation.save_summary"):
            with patch("conversation.save_vocabulary"):
                result = engine.end_session()
        assert result.startswith("Session saved.")
        assert "summary update failed" not in result


# ---------------------------------------------------------------------------
# Corrupt checkpoint handling (audit 2026 #5)
# ---------------------------------------------------------------------------


class TestCorruptCheckpoint:
    def _make_engine(self, tmp_path):
        from config import UserPaths
        from conversation import ConversationEngine

        data_dir = tmp_path / "user-data"
        (data_dir / "sessions").mkdir(parents=True)
        (data_dir / "records").mkdir(parents=True)
        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()
        engine.paths = UserPaths(
            user_id="u1",
            data_dir=data_dir,
            summary=data_dir / "summary.md",
            vocabulary=data_dir / "vocabulary.md",
            sessions=data_dir / "sessions",
            records=data_dir / "records",
        )
        return engine

    def test_corrupt_json_moves_aside_and_returns_false(self, tmp_path, caplog):
        engine = self._make_engine(tmp_path)
        engine.checkpoint_path.write_text('{"messages": [torn wr', encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="conversation"):
            assert engine.load_checkpoint() is False
        corrupt = list(engine.paths.data_dir.glob("*.corrupt-*"))
        assert len(corrupt) == 1
        assert not engine.has_checkpoint()  # original path is gone
        assert any("Corrupt checkpoint" in r.message for r in caplog.records)

    def test_missing_keys_moves_aside_and_returns_false(self, tmp_path):
        engine = self._make_engine(tmp_path)
        engine.checkpoint_path.write_text('{"foo": 1}', encoding="utf-8")
        assert engine.load_checkpoint() is False
        assert len(list(engine.paths.data_dir.glob("*.corrupt-*"))) == 1

    def test_fresh_session_works_after_corrupt(self, tmp_path):
        engine = self._make_engine(tmp_path)
        engine.checkpoint_path.write_text("not json at all", encoding="utf-8")
        assert engine.load_checkpoint() is False
        # A fresh session can then save a new checkpoint at the same path
        engine.save_checkpoint()
        assert engine.has_checkpoint()
        assert engine.load_checkpoint() is True


# ---------------------------------------------------------------------------
# Warm-up message role alternation (audit 2026 #24) + no first-user-message
# injection (audit 2026 #25)
# ---------------------------------------------------------------------------


class TestWarmupRoleAlternation:
    def _make_engine(self, tmp_path):
        """Engine with the REAL system prompt and a tmp checkpoint dir."""
        from config import UserPaths
        from conversation import ConversationEngine

        data_dir = tmp_path / "user-data"
        (data_dir / "sessions").mkdir(parents=True)
        (data_dir / "records").mkdir(parents=True)
        with patch("conversation.load_summary", return_value="- Current level: A0"):
            with patch("conversation.load_vocabulary", return_value=[]):
                with patch("conversation.OpenAI") as mock_client:
                    mock_client.return_value.chat.completions.create.return_value = (
                        _fake_completion("Olá! Como te chamas?")
                    )
                    engine = ConversationEngine()
        engine.paths = UserPaths(
            user_id="u1",
            data_dir=data_dir,
            summary=data_dir / "summary.md",
            vocabulary=data_dir / "vocabulary.md",
            sessions=data_dir / "sessions",
            records=data_dir / "records",
        )
        return engine

    def test_after_warmup_roles_alternate(self, tmp_path):
        engine = self._make_engine(tmp_path)
        engine.start_warmup()
        roles = [m["role"] for m in engine.messages]
        assert roles[0] == "system"
        assert roles == ["system", "user", "assistant"]
        assert all(roles[i] != roles[i + 1] for i in range(len(roles) - 1))

    def test_no_two_adjacent_system_messages_ever(self, tmp_path):
        engine = self._make_engine(tmp_path)
        engine.start_warmup()
        with patch.object(engine, "_extract_vocab_from_exchange", MagicMock()):
            with patch.object(engine, "_call_llm", return_value="Muito prazer, Alex!"):
                engine.user_message("Chamo-me Alex")
        roles = [m["role"] for m in engine.messages]
        assert all(roles[i] != roles[i + 1] for i in range(len(roles) - 1))

    def test_first_user_message_has_no_persistent_framing_injection(self, tmp_path):
        engine = self._make_engine(tmp_path)
        engine.start_warmup()
        with patch.object(engine, "_extract_vocab_from_exchange", MagicMock()):
            with patch.object(engine, "_call_llm", return_value="Ótimo!"):
                engine.user_message("Alex")
        joined = " ".join(str(m.get("content")) for m in engine.messages)
        assert "learner is now answering" not in joined
        # The framing must not linger in later turns either
        with patch.object(engine, "_extract_vocab_from_exchange", MagicMock()):
            with patch.object(engine, "_call_llm", return_value="ok"):
                engine.user_message("segunda mensagem")
        joined = " ".join(str(m.get("content")) for m in engine.messages)
        assert "learner is now answering" not in joined


# ---------------------------------------------------------------------------
# Context windowing (audit 2026 #18) + LLM call timeouts (audit 2026 #19)
# ---------------------------------------------------------------------------


class TestContextWindowing:
    def _make_engine(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()
        return engine

    def _capture_client(self, engine):
        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            return _fake_completion("ok")

        engine.client = MagicMock()
        engine.client.chat.completions.create.side_effect = fake_create
        return captured

    def test_window_capped_at_context_messages(self):
        engine = self._make_engine()
        engine.messages = [{"role": "system", "content": "sys"}] + [
            {"role": "user", "content": f"u{i}"} for i in range(40)
        ]
        captured = self._capture_client(engine)
        engine._call_llm()
        sent = captured["messages"]
        assert len(sent) == CONTEXT_MESSAGES
        assert sent[0]["content"] == "sys"  # system prompt always kept
        assert sent[-1]["content"] == "u39"  # most recent kept

    def test_warmup_marker_kept_in_window(self):
        engine = self._make_engine()
        engine.messages = [
            {"role": "system", "content": "sys"},
            {
                "role": "user",
                "content": "[The warm-up phase is complete. You greeted the learner and "
                "started the conversation. Now continue naturally in response "
                "to their messages.]",
            },
        ] + [{"role": "assistant", "content": f"a{i}"} for i in range(40)]
        window = engine._windowed_messages()
        assert len(window) == CONTEXT_MESSAGES
        assert window[0]["content"] == "sys"
        assert str(window[1]["content"]).startswith("[The warm-up phase is complete")

    def test_small_history_sent_unchanged(self):
        engine = self._make_engine()
        engine.messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "olá"},
        ]
        window = engine._windowed_messages()
        assert window == engine.messages

    def test_call_llm_timeout(self):
        engine = self._make_engine()
        captured = self._capture_client(engine)
        engine._call_llm()
        assert captured["timeout"] == 30

    def test_checkpoint_still_saves_full_messages(self, tmp_path):
        from config import UserPaths
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI"):
                        engine = ConversationEngine()
        data_dir = tmp_path / "d"
        data_dir.mkdir()
        engine.paths = UserPaths(
            user_id="u1",
            data_dir=data_dir,
            summary=data_dir / "summary.md",
            vocabulary=data_dir / "vocabulary.md",
            sessions=data_dir / "sessions",
            records=data_dir / "records",
        )
        engine.messages = [{"role": "system", "content": "sys"}] + [
            {"role": "user", "content": f"u{i}"} for i in range(40)
        ]
        engine.save_checkpoint()
        fresh = engine.__class__.__new__(engine.__class__)
        fresh.paths = engine.paths
        fresh.session_start = datetime.now()
        fresh.messages = []
        fresh.history = []
        fresh.new_words = []
        fresh.vocabulary = []
        fresh._warmup_done = False
        assert fresh.load_checkpoint() is True
        assert len(fresh.messages) == 41  # full list, not the window
