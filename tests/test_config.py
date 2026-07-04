"""Tests for config.py — env var overrides, path defaults, guardrails."""

import os
from pathlib import Path


class TestEnvVarDefaults:
    def test_default_model(self, clear_env):
        import config

        assert config.LLM_MODEL == "gpt-4o"

    def test_default_base_url(self, clear_env):
        import config

        assert config.LLM_BASE_URL == "https://api.openai.com/v1"

    def test_default_api_key_empty(self, clear_env):
        import config

        assert config.LLM_API_KEY == ""

    def test_fala_model_override(self, clear_env):
        os.environ["FALA_MODEL"] = "gpt-4o-mini"
        import importlib

        import config

        importlib.reload(config)
        assert config.LLM_MODEL == "gpt-4o-mini"

    def test_fala_api_key_takes_precedence(self, clear_env):
        os.environ["FALA_API_KEY"] = "from-fala"
        os.environ["OPENAI_API_KEY"] = "from-openai"
        import importlib

        import config

        importlib.reload(config)
        assert config.LLM_API_KEY == "from-fala"

    def test_openai_api_key_fallback(self, clear_env):
        os.environ["OPENAI_API_KEY"] = "from-openai"
        import importlib

        import config

        importlib.reload(config)
        assert config.LLM_API_KEY == "from-openai"

    def test_tts_defaults(self, clear_env):
        import config

        assert config.TTS_PROVIDER == "openai"
        assert config.TTS_VOICE == "alloy"

    def test_stt_default_model(self, clear_env):
        import config

        assert config.STT_MODEL == "base"


class TestPaths:
    def test_project_dir_is_parent_of_config(self):
        import config

        expected = Path(__file__).resolve().parent.parent
        assert config.PROJECT_DIR.resolve() == expected

    def test_data_dir_is_under_project(self):
        import config

        assert config.DATA_DIR == config.PROJECT_DIR / "data"

    def test_data_dirs_exist(self):
        import config

        assert config.DATA_DIR.exists()
        assert config.SESSIONS_DIR.exists()
        assert config.RECORDS_DIR.exists()


class TestGuardrails:
    def test_guardrails_defaults(self, clear_env):
        import config

        assert config.GUARDRAILS["max_new_words_per_session"] == 5
        assert config.GUARDRAILS["min_review_words_per_warmup"] == 3
        assert config.GUARDRAILS["present_tense_confidence_threshold"] == 0.7

    def test_level_order(self, clear_env):
        import config

        assert config.LEVEL_ORDER == ["A1", "A2", "B1"]
