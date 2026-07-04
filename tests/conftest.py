"""Shared test fixtures and helpers."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_data_dir():
    """Provide a temporary directory and patch config paths to use it."""
    with tempfile.TemporaryDirectory() as tmp:
        orig_dir = Path(tmp)
        data_dir = orig_dir / "data"
        sessions_dir = data_dir / "sessions"
        records_dir = data_dir / "records"
        data_dir.mkdir()
        sessions_dir.mkdir()
        records_dir.mkdir()

        patches = {
            "config.DATA_DIR": data_dir,
            "config.SESSIONS_DIR": sessions_dir,
            "config.RECORDS_DIR": records_dir,
            "config.SUMMARY_PATH": data_dir / "summary.md",
            "config.VOCABULARY_PATH": data_dir / "vocabulary.md",
        }
        yield patches


@pytest.fixture
def clear_env():
    """Remove FALA_* env vars for clean tests."""
    saved = {}
    for key in list(os.environ):
        if key.startswith("FALA_"):
            saved[key] = os.environ.pop(key)
    yield
    for key, val in saved.items():
        os.environ[key] = val
