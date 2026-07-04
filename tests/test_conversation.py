"""Tests for conversation.py — ConversationEngine."""

from unittest.mock import MagicMock, patch

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

    def test_default_level_a1(self):
        engine = self._make_engine("No level info here")
        assert engine._extract_level() == "A1"

    def test_parses_a1(self):
        engine = self._make_engine("- Current level: A1\n- Sessions: 0")
        assert engine._extract_level() == "A1"

    def test_parses_a2(self):
        engine = self._make_engine("- Current level: A2")
        assert engine._extract_level() == "A2"

    def test_parses_b1(self):
        engine = self._make_engine("- Current level: B1")
        assert engine._extract_level() == "B1"


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
        assert "Level: A1" in content
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


class TestExtractVocabFromExchange:
    def test_extracts_json_words(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion(
                                '[{"word": "livro", "english": "book", "context": '
                                '"O livro é azul."}]'
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
                                '```json\n[{"word": "casa", '
                                '"english": "house", "context": ""}]\n```'
                            )
                        )
                        engine = ConversationEngine()
                        engine.vocabulary = []
                        engine._extract_vocab_from_exchange("x", "y")
                        assert len(engine.vocabulary) == 1

    def test_handles_empty_array(self):
        from conversation import ConversationEngine

        with patch("conversation.ConversationEngine._build_system_prompt"):
            with patch("conversation.load_summary", return_value=""):
                with patch("conversation.load_vocabulary", return_value=[]):
                    with patch("conversation.OpenAI") as mock_client:
                        mock_client.return_value.chat.completions.create.return_value = (
                            _fake_completion("[]")
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
