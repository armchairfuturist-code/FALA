"""Tests for progress.py — SRS logic, vocab persistence, summary management."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config_patches(data_dir: Path):
    """Return a dict of config attributes to swap for testing."""
    return {
        "DATA_DIR": data_dir,
        "SUMMARY_PATH": data_dir / "summary.md",
        "VOCABULARY_PATH": data_dir / "vocabulary.md",
        "RECORDS_DIR": data_dir / "records",
        "GUARDRAILS": {
            "max_new_words_per_session": 5,
            "min_review_words_per_warmup": 3,
            "present_tense_confidence_threshold": 0.7,
        },
    }


def _apply_patches(patches):
    """Swap config module attributes with test values."""
    import config

    for key, val in patches.items():
        setattr(config, key, val)


def _reload_progress():
    """Reload progress so it picks up patched config values."""
    import importlib

    import progress

    importlib.reload(progress)
    return progress


# ---------------------------------------------------------------------------
# Vocabulary: add_vocabulary
# ---------------------------------------------------------------------------


class TestAddVocabulary:
    def test_add_new_word(self):
        p = _reload_progress()
        entries = []
        entries = p.add_vocabulary(entries, "olá", "hello", "Olá, tudo bem?")
        assert len(entries) == 1
        assert entries[0]["word"] == "olá"
        assert entries[0]["english"] == "hello"
        assert entries[0]["confidence"] == 0.3
        assert entries[0]["needs_review"] is True

    def test_duplicate_word_skipped(self):
        p = _reload_progress()
        entries = [
            {
                "word": "olá",
                "english": "hello",
                "ease": 2.5,
                "interval": 1,
                "last_reviewed": "2026-01-01",
                "confidence": 0.5,
                "needs_review": False,
            }
        ]
        entries = p.add_vocabulary(entries, "olá", "hello")
        assert len(entries) == 1

    def test_multiple_words(self):
        p = _reload_progress()
        entries = []
        for word, eng in [("sim", "yes"), ("não", "no"), ("obrigado", "thank you")]:
            entries = p.add_vocabulary(entries, word, eng)
        assert len(entries) == 3


# ---------------------------------------------------------------------------
# Vocabulary: update_vocab_after_review
# ---------------------------------------------------------------------------


class TestUpdateVocabAfterReview:
    def _make_entry(self, word="teste", confidence=0.5, ease=2.5, interval=1, needs_review=True):
        return {
            "word": word,
            "english": "test",
            "context": "",
            "ease": ease,
            "interval": interval,
            "last_reviewed": "2026-01-01",
            "confidence": confidence,
            "needs_review": needs_review,
        }

    def test_correct_answer_increases_confidence(self):
        p = _reload_progress()
        entries = [self._make_entry(confidence=0.5)]
        entries = p.update_vocab_after_review(entries, "teste", correct=True)
        assert entries[0]["confidence"] == 0.65  # 0.5 + 0.15
        assert entries[0]["interval"] > 1

    def test_correct_answer_caps_confidence(self):
        p = _reload_progress()
        entries = [self._make_entry(confidence=0.95)]
        entries = p.update_vocab_after_review(entries, "teste", correct=True)
        assert entries[0]["confidence"] == 1.0

    def test_incorrect_answer_resets(self):
        p = _reload_progress()
        entries = [self._make_entry(confidence=0.7, interval=10, ease=2.5)]
        entries = p.update_vocab_after_review(entries, "teste", correct=False)
        assert entries[0]["confidence"] == pytest.approx(0.5, rel=1e-6)
        assert entries[0]["interval"] == 1
        assert entries[0]["needs_review"] is True

    def test_high_confidence_clears_review_flag(self):
        p = _reload_progress()
        entries = [self._make_entry(confidence=0.7)]
        entries = p.update_vocab_after_review(entries, "teste", correct=True)
        assert entries[0]["confidence"] == 0.85
        assert entries[0]["needs_review"] is False

    def test_unknown_word_no_op(self):
        p = _reload_progress()
        entries = [self._make_entry(word="a")]
        entries = p.update_vocab_after_review(entries, "nonexistent", correct=True)
        assert len(entries) == 1
        assert entries[0]["word"] == "a"


# ---------------------------------------------------------------------------
# Vocabulary: get_review_words
# ---------------------------------------------------------------------------


class TestGetReviewWords:
    def _make_entry(self, word, confidence=0.5, interval=1, last_reviewed=None, needs_review=False):
        if last_reviewed is None:
            last_reviewed = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        return {
            "word": word,
            "english": "",
            "context": "",
            "ease": 2.5,
            "interval": interval,
            "last_reviewed": last_reviewed,
            "confidence": confidence,
            "needs_review": needs_review,
        }

    def test_returns_due_words(self):
        p = _reload_progress()
        entries = [
            self._make_entry("due1", interval=1),  # 7 days ago + 1 day interval = due
            self._make_entry("due2", interval=30),  # 7 days ago + 30 day interval = not due
        ]
        due = p.get_review_words(entries, count=5)
        words = [e["word"] for e in due]
        assert "due1" in words
        assert "due2" not in words

    def test_needs_review_always_included(self):
        p = _reload_progress()
        entries = [
            self._make_entry("always", interval=100, needs_review=True),
        ]
        due = p.get_review_words(entries, count=5)
        assert any(e["word"] == "always" for e in due)

    def test_respects_count(self):
        p = _reload_progress()
        entries = [self._make_entry(f"word{i}", interval=1) for i in range(10)]
        due = p.get_review_words(entries, count=3)
        assert len(due) == 3

    def test_sorts_by_confidence_ascending(self):
        p = _reload_progress()
        entries = [
            self._make_entry("high", confidence=0.9, interval=1),
            self._make_entry("low", confidence=0.2, interval=1),
            self._make_entry("mid", confidence=0.5, interval=1),
        ]
        due = p.get_review_words(entries, count=3)
        confs = [e["confidence"] for e in due]
        assert confs == sorted(confs)

    def test_empty_list_returns_empty(self):
        p = _reload_progress()
        assert p.get_review_words([], count=5) == []


# ---------------------------------------------------------------------------
# Vocabulary: get_review_words_with_direction
# ---------------------------------------------------------------------------


class TestGetReviewWordsWithDirection:
    def _make_entry(self, word, confidence=0.5, interval=1):
        last_reviewed = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        return {
            "word": word,
            "english": "",
            "context": "",
            "ease": 2.5,
            "interval": interval,
            "last_reviewed": last_reviewed,
            "confidence": confidence,
            "needs_review": False,
        }

    def test_high_confidence_gets_recall(self):
        p = _reload_progress()
        entries = [self._make_entry("forte", confidence=0.8)]
        tagged = p.get_review_words_with_direction(entries)
        assert len(tagged) == 1
        assert tagged[0]["retrieval_direction"] == "recall"

    def test_low_confidence_gets_recognition(self):
        p = _reload_progress()
        entries = [self._make_entry("fraco", confidence=0.3)]
        tagged = p.get_review_words_with_direction(entries)
        assert len(tagged) == 1
        assert tagged[0]["retrieval_direction"] == "recognition"

    def test_boundary_at_half_gets_recall(self):
        p = _reload_progress()
        entries = [self._make_entry("meio", confidence=0.5)]
        tagged = p.get_review_words_with_direction(entries)
        assert tagged[0]["retrieval_direction"] == "recall"

    def test_mixed_entries_tagged_individually(self):
        p = _reload_progress()
        entries = [
            self._make_entry("known", confidence=0.9),
            self._make_entry("newish", confidence=0.2),
        ]
        tagged = p.get_review_words_with_direction(entries, count=5)
        directions = {e["word"]: e["retrieval_direction"] for e in tagged}
        assert directions == {"known": "recall", "newish": "recognition"}

    def test_originals_not_mutated(self):
        p = _reload_progress()
        entries = [self._make_entry("word", confidence=0.8)]
        p.get_review_words_with_direction(entries)
        assert "retrieval_direction" not in entries[0]

    def test_empty_list_returns_empty(self):
        p = _reload_progress()
        assert p.get_review_words_with_direction([]) == []


# ---------------------------------------------------------------------------
# Vocabulary: save / load round-trip
# ---------------------------------------------------------------------------


class TestVocabPersistence:
    def test_write_then_read(self, tmp_path):
        from config import VOCABULARY_PATH

        # Patch paths
        old_path = VOCABULARY_PATH
        test_path = tmp_path / "vocabulary.md"

        import config

        config.VOCABULARY_PATH = test_path
        p = _reload_progress()

        entries = []
        entries = p.add_vocabulary(entries, "bom", "good")
        entries = p.add_vocabulary(entries, "mau", "bad")
        p.save_vocabulary(entries)

        loaded = p.load_vocabulary()
        assert len(loaded) == 2
        assert loaded[0]["word"] == "bom"
        assert loaded[1]["word"] == "mau"

        # Restore
        config.VOCABULARY_PATH = old_path

    def test_load_nonexistent_returns_empty(self, tmp_path):
        import config

        old = config.VOCABULARY_PATH
        config.VOCABULARY_PATH = tmp_path / "nonexistent.md"
        p = _reload_progress()
        assert p.load_vocabulary() == []
        config.VOCABULARY_PATH = old


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_default_summary(self, tmp_path):
        import config

        old = config.SUMMARY_PATH
        config.SUMMARY_PATH = tmp_path / "summary.md"
        p = _reload_progress()
        summary = p.load_summary()
        assert "Current level: A0" in summary
        assert "Learner name: (not yet known)" in summary
        assert "Sessions completed: 0" in summary
        config.SUMMARY_PATH = old

    def test_save_and_load_summary(self, tmp_path):
        import config

        test_path = tmp_path / "summary.md"
        old = config.SUMMARY_PATH
        config.SUMMARY_PATH = test_path
        p = _reload_progress()

        text = "# Learner Profile\n- Current level: A2\n- Sessions completed: 5"
        p.save_summary(text)
        loaded = p.load_summary()
        assert "A2" in loaded
        assert "5" in loaded

        config.SUMMARY_PATH = old


# ---------------------------------------------------------------------------
# get_vocab_for_prompt
# ---------------------------------------------------------------------------


class TestGetVocabForPrompt:
    def _make_entry(self, word, confidence=0.5, interval=1, **kw):
        return {
            "word": word,
            "english": "?",
            "context": "",
            "ease": 2.5,
            "interval": interval,
            "last_reviewed": "2026-01-01",
            "confidence": confidence,
            "needs_review": True,
            **kw,
        }

    def test_returns_formatted_string(self):
        p = _reload_progress()
        entries = [self._make_entry("obrigado", confidence=0.7)]
        result = p.get_vocab_for_prompt(entries)
        assert "obrigado" in result
        assert "70%" in result or "70 %" in result

    def test_empty_returns_placeholder(self):
        p = _reload_progress()
        result = p.get_vocab_for_prompt([])
        assert "no vocabulary yet" in result

    def test_respects_count(self):
        p = _reload_progress()
        entries = [self._make_entry(f"word{i}") for i in range(20)]
        result = p.get_vocab_for_prompt(entries, count=5)
        lines = [ln for ln in result.split("\n") if ln.strip().startswith("-")]
        assert len(lines) <= 5


# ---------------------------------------------------------------------------
# Regression tests for Group B fixes
# ---------------------------------------------------------------------------


class TestCaseInsensitiveDuplicates:
    def test_add_vocabulary_case_insensitive(self):
        p = _reload_progress()
        entries = []
        entries = p.add_vocabulary(entries, "Olá", "hello")
        entries = p.add_vocabulary(entries, "olá", "hello")
        assert len(entries) == 1, "Case variants should be treated as same word"

    def test_update_vocab_after_review_case_insensitive(self):
        p = _reload_progress()
        entries = [
            {
                "word": "Olá",
                "english": "hello",
                "context": "",
                "ease": 2.5,
                "interval": 1,
                "last_reviewed": "2026-01-01",
                "confidence": 0.5,
                "needs_review": True,
            }
        ]
        entries = p.update_vocab_after_review(entries, "olá", correct=True)
        assert entries[0]["confidence"] == 0.65, "Case-insensitive match should work"


class TestSaveVocabularyEmptyGuard:
    """save_vocabulary writes exactly what is passed — callers own correctness."""

    def test_save_empty_empties_file(self, tmp_path):
        """An empty list legitimately empties the file — deletions persist."""
        import config

        old_path = config.VOCABULARY_PATH
        test_path = tmp_path / "vocabulary.md"
        config.VOCABULARY_PATH = test_path
        p = _reload_progress()

        entries = p.add_vocabulary([], "bom", "good")
        p.save_vocabulary(entries)
        assert "bom" in test_path.read_text()

        p.save_vocabulary([])  # user deleted all words
        assert test_path.read_text() == ""
        assert p.load_vocabulary() == []

        config.VOCABULARY_PATH = old_path

    def test_save_none_raises(self, tmp_path):
        import pytest

        import config

        old_path = config.VOCABULARY_PATH
        config.VOCABULARY_PATH = tmp_path / "vocabulary.md"
        p = _reload_progress()

        with pytest.raises(ValueError):
            p.save_vocabulary(None)  # type: ignore[arg-type]

        config.VOCABULARY_PATH = old_path


class TestAtomicWriteText:
    def test_atomic_write_roundtrip_no_tmp_leftover(self, tmp_path):
        p = _reload_progress()
        target = tmp_path / "out.md"
        p.atomic_write_text(target, "hello\nworld")
        assert target.read_text() == "hello\nworld"
        assert list(tmp_path.glob("*.tmp")) == []

    def test_atomic_write_overwrites(self, tmp_path):
        p = _reload_progress()
        target = tmp_path / "out.md"
        p.atomic_write_text(target, "first")
        p.atomic_write_text(target, "second")
        assert target.read_text() == "second"


class TestVocabRoundTripAdversarial:
    """Values with quotes/newlines/looks-like-a-record text survive a save+load."""

    def _roundtrip(self, tmp_path, entries):
        import config

        old_path = config.VOCABULARY_PATH
        config.VOCABULARY_PATH = tmp_path / "vocabulary.md"
        p = _reload_progress()
        p.save_vocabulary(entries)
        loaded = p.load_vocabulary()
        config.VOCABULARY_PATH = old_path
        return loaded

    def _entry(self, word, english, context):
        return {
            "word": word,
            "english": english,
            "context": context,
            "ease": 2.5,
            "interval": 1,
            "last_reviewed": "2026-01-01",
            "confidence": 0.3,
            "needs_review": True,
        }

    def test_quotes_in_values(self, tmp_path):
        entries = [self._entry('dizer "olá"', 'say "hello"', 'Ele disse "adeus" hoje.')]
        loaded = self._roundtrip(tmp_path, entries)
        assert loaded[0]["word"] == 'dizer "olá"'
        assert loaded[0]["english"] == 'say "hello"'
        assert loaded[0]["context"] == 'Ele disse "adeus" hoje.'

    def test_newlines_in_values(self, tmp_path):
        entries = [self._entry("bom dia", "good morning", "line one\nline two")]
        loaded = self._roundtrip(tmp_path, entries)
        assert loaded[0]["word"] == "bom dia"
        assert loaded[0]["context"] == "line one\nline two"

    def test_record_marker_inside_context_does_not_split(self, tmp_path):
        marker = "\n- word: fake"
        entries = [self._entry("real", "real word", f"note {marker} trap")]
        loaded = self._roundtrip(tmp_path, entries)
        assert len(loaded) == 1
        assert loaded[0]["context"] == f"note {marker} trap"

    def test_unicode_roundtrip(self, tmp_path):
        entries = [self._entry("pão", "bread", "O pão está na mesação ção")]
        loaded = self._roundtrip(tmp_path, entries)
        assert loaded[0]["word"] == "pão"
        assert loaded[0]["context"] == "O pão está na mesação ção"

    def test_backslashes_roundtrip(self, tmp_path):
        entries = [self._entry("a\\b", "c\\d", "e\\nf")]
        loaded = self._roundtrip(tmp_path, entries)
        assert loaded[0]["word"] == "a\\b"
        assert loaded[0]["english"] == "c\\d"
        assert loaded[0]["context"] == "e\\nf"

    def test_multiple_adversarial_entries(self, tmp_path):
        entries = [
            self._entry('um "dois"', "one", "\n- word: impostor"),
            self._entry("três\nquatro", "three", "cols: a: b"),
            self._entry("cinco", "five", ""),
        ]
        loaded = self._roundtrip(tmp_path, entries)
        assert [(e["word"], e["english"], e["context"]) for e in loaded] == [
            ('um "dois"', "one", "\n- word: impostor"),
            ("três\nquatro", "three", "cols: a: b"),
            ("cinco", "five", ""),
        ]
        # SRS fields still parse
        assert all(e["ease"] == 2.5 and e["confidence"] == 0.3 for e in loaded)

    def test_legacy_quoted_file_still_loads(self, tmp_path):
        import config

        old_path = config.VOCABULARY_PATH
        test_path = tmp_path / "vocabulary.md"
        test_path.write_text('- word: "bom"\n  english: "good"\n  context: "É bom!"\n')
        config.VOCABULARY_PATH = test_path
        p = _reload_progress()
        loaded = p.load_vocabulary()
        assert loaded[0]["word"] == "bom"
        assert loaded[0]["english"] == "good"
        assert loaded[0]["context"] == "É bom!"
        config.VOCABULARY_PATH = old_path


# ---------------------------------------------------------------------------
# vocabulary_report
# ---------------------------------------------------------------------------


class TestVocabularyReport:
    def _mock_freqs(self, p):
        """Patch _load_frequency_words to return known rank data."""
        import progress as prog_mod

        prog_mod._load_frequency_words = lambda: {
            "ser": 10,
            "ter": 200,
            "bom": 498,
            "livro": 501,
            "janela": 1500,
            "cadeira": 2001,
            "edifício": 4000,
            "responsabilidade": 5001,
            "constitucional": 10000,
        }
        return prog_mod

    def test_empty_vocabulary(self):
        p = _reload_progress()
        report = p.vocabulary_report([])
        assert report["total_words"] == 0
        assert report["cefr"] == {}
        assert report["average_confidence"] == 0.0
        assert report["mature_words"] == 0
        assert report["due_for_review"] == 0

    def test_cefr_bands_at_boundaries(self):
        p = _reload_progress()
        self._mock_freqs(p)
        entries = [
            {"word": "bom", "confidence": 0.5, "needs_review": False},
            {"word": "janela", "confidence": 0.5, "needs_review": False},
            {"word": "cadeira", "confidence": 0.5, "needs_review": False},
            {"word": "responsabilidade", "confidence": 0.5, "needs_review": False},
        ]
        report = p.vocabulary_report(entries)
        assert report["cefr"] == {"A1": 1, "A2": 1, "B1": 1, "B2+": 1}

    def test_word_not_in_frequency_list(self):
        p = _reload_progress()
        self._mock_freqs(p)
        entries = [{"word": "xpto", "confidence": 0.5, "needs_review": False}]
        report = p.vocabulary_report(entries)
        assert report["cefr"].get("B2+", 0) == 1

    def test_srs_stats(self):
        p = _reload_progress()
        self._mock_freqs(p)
        entries = [
            {"word": "ser", "confidence": 0.9, "needs_review": False},
            {"word": "ter", "confidence": 0.7, "needs_review": False},
            {"word": "livro", "confidence": 0.5, "needs_review": True},
            {"word": "janela", "confidence": 0.3, "needs_review": False},
        ]
        report = p.vocabulary_report(entries)
        assert report["total_words"] == 4
        assert report["mature_words"] == 2
        assert report["average_confidence"] == pytest.approx(0.6, rel=1e-6)
        assert report["due_for_review"] == 1
