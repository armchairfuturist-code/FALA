"""Tests for config.py — env var overrides, path defaults, guardrails."""

import os
from pathlib import Path

import pytest


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

    def test_stt_api_model_defaults_to_openai(self, clear_env):
        import config

        assert config.STT_API_MODEL == "whisper-1"

    def test_stt_api_model_auto_detects_groq(self, clear_env):
        os.environ["FALA_BASE_URL"] = "https://api.groq.com/openai/v1"
        import importlib

        import config

        importlib.reload(config)
        assert config.STT_API_MODEL == "whisper-large-v3-turbo"

    def test_stt_api_model_override(self, clear_env):
        os.environ["FALA_STT_API_MODEL"] = "my-custom-model"
        import importlib

        import config

        importlib.reload(config)
        assert config.STT_API_MODEL == "my-custom-model"

    def test_azure_defaults(self, clear_env):
        import config

        assert config.AZURE_SPEECH_KEY == ""
        assert config.AZURE_SPEECH_REGION == "westeurope"
        assert config.AZURE_TTS_VOICE == "pt-PT-FernandaNeural"

    def test_azure_env_overrides(self, clear_env):
        os.environ["FALA_AZURE_KEY"] = "azure-key-123"
        os.environ["FALA_AZURE_REGION"] = "northeurope"
        os.environ["FALA_AZURE_VOICE"] = "pt-PT-RaquelNeural"
        import importlib

        import config

        importlib.reload(config)
        assert config.AZURE_SPEECH_KEY == "azure-key-123"
        assert config.AZURE_SPEECH_REGION == "northeurope"
        assert config.AZURE_TTS_VOICE == "pt-PT-RaquelNeural"

    def test_azure_key_falls_back_to_azure_speech_key(self, clear_env):
        os.environ["AZURE_SPEECH_KEY"] = "fallback-key"
        import importlib

        import config

        importlib.reload(config)
        assert config.AZURE_SPEECH_KEY == "fallback-key"


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


class TestPathsForUser:
    def test_default_maps_to_flat_layout(self):
        import config

        p = config.paths_for_user("default")
        assert p.user_id == "default"
        assert p.data_dir == config.DATA_DIR
        assert p.summary == config.SUMMARY_PATH
        assert p.vocabulary == config.VOCABULARY_PATH
        assert p.sessions == config.SESSIONS_DIR
        assert p.records == config.RECORDS_DIR

    def test_default_is_the_default_argument(self):
        import config

        assert config.paths_for_user() == config.paths_for_user("default")

    def test_named_user_lives_under_users_dir(self, tmp_path, monkeypatch):
        import config

        monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
        p = config.paths_for_user("alice")
        assert p.data_dir == tmp_path / "data" / "users" / "alice"
        assert p.summary == p.data_dir / "summary.md"
        assert p.vocabulary == p.data_dir / "vocabulary.md"
        assert p.sessions == p.data_dir / "sessions"
        assert p.records == p.data_dir / "records"

    def test_named_user_dirs_created(self, tmp_path, monkeypatch):
        import config

        monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
        p = config.paths_for_user("alice")
        assert p.data_dir.is_dir()
        assert p.sessions.is_dir()
        assert p.records.is_dir()

    def test_named_users_are_isolated(self, tmp_path, monkeypatch):
        import config

        monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
        alice = config.paths_for_user("alice")
        bob = config.paths_for_user("bob")
        assert alice.data_dir != bob.data_dir
        assert alice.vocabulary != bob.vocabulary

    def test_default_does_not_create_users_dir(self, tmp_path, monkeypatch):
        import config

        monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
        config.paths_for_user("default")
        assert not (tmp_path / "data" / "users").exists()

    def test_path_traversal_user_id_rejected(self):
        import config

        for bad in ("../evil", "a/b", "a\\b", "", "white space", "dot.name"):
            with pytest.raises(ValueError):
                config.paths_for_user(bad)

    def test_valid_user_id_characters_accepted(self, tmp_path, monkeypatch):
        import config

        monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
        for ok in ("alice", "user-1", "user_2", "ABC123"):
            assert config.paths_for_user(ok).user_id == ok


class TestGuardrails:
    def test_guardrails_defaults(self, clear_env):
        import config

        assert config.GUARDRAILS["max_new_words_per_session"] == 5
        assert config.GUARDRAILS["min_review_words_per_warmup"] == 3
        assert config.GUARDRAILS["present_tense_confidence_threshold"] == 0.7

    def test_level_order(self, clear_env):
        import config

        assert config.LEVEL_ORDER == ["A1", "A2", "B1"]
