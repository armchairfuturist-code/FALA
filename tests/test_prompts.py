"""Tests that the tutor prompts implement the 2026 research-backed pedagogy.

See docs/research/pedagogy-2026.md ("Concrete prompt changes") and
docs/research/synthesis-2026.md (P0 list).
"""

import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def read(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


def test_system_md_exists_and_has_placeholders():
    text = read("system.md")
    assert "{level}" in text
    assert "{summary}" in text
    assert "{vocabulary}" in text


def test_no_never_reveal_language_anywhere():
    for name in ("system.md", "warmup.md"):
        text = read(name).lower()
        assert "never reveal" not in text
        assert "do not reveal" not in text
        assert "don't reveal" not in text
        assert "no reveal" not in text


def test_two_strike_correction_protocol():
    text = read("system.md")
    assert "Correction protocol (two strikes)" in text
    # Strike 1: prompt/hint
    assert "First attempt, wrong" in text
    assert "hint" in text
    # Strike 2: plain answer + reason + learner repeats
    assert "give the correct answer plainly" in text
    assert "one-line reason" in text
    # Corrected exchanges always end with learner production
    assert "learner producing the correct form once" in text
    # Minor slips: model and move on
    assert "Minor slips" in text


def test_voce_is_valid_ptpt_register():
    text = read("system.md")
    assert "register choice" in text
    assert "o senhor" in text and "a senhora" in text
    assert "você" in text
    assert "VALID pt-PT" in text
    assert 'Never correct "você" as a mistake' in text
    # você must no longer be listed as a Brazilian error
    table_row = re.search(r"você \(you\)", text)
    assert table_row is None
    # other pt-BR entries kept
    for kept in ("autocarro", "comboio", "rapariga", "a falar"):
        assert kept in text


def test_micro_explanations_not_no_grammar():
    text = read("system.md")
    assert "Micro-explanations" in text
    assert "1-3 sentence" in text
    assert "2-3 sentences" in text
    assert "always followed by a usage example" in text
    # A0 weeks 1-2 stay grammar-free
    assert "Weeks 1-2" in text and "grammar-free" in text
    # A1 level description agrees with the rule
    assert "Brief grammar explanations in English" in text


def test_production_in_phase_1():
    text = read("system.md")
    assert "Agora tu: repete" in text
    assert "at least once per session" in text


def test_voice_section_replaces_pronunciation_feedback():
    text = read("system.md")
    # No [voice]-prefixed pronunciation feedback instruction
    assert "[voice]" not in text
    assert "NEVER comment on pronunciation" in text
    assert "transcript" in text.lower()


def test_vocabulary_coverage_constraint():
    text = read("system.md")
    assert "≥95%" in text
    assert "≤5 taught items" in text


def test_graduated_voice_invitation():
    text = read("system.md")
    assert "Se quiseres, tenta dizer a frase em voz alta (/voice) — sem pressão" in text
    assert "Never require voice" in text
    assert "more than once per session" in text
    assert "Treat any voice attempt as success" in text
    # Wait time in voice mode
    assert "do not re-prompt or answer for the learner" in text


def test_error_priority_list_clitics_first():
    text = read("system.md")
    priority = text[text.index("Correction priority list") :]
    clitic = priority.index("Clitic placement")
    gerund = priority.index("a + infinitive")
    meaning = priority.index("Meaning-breaking errors")
    assert clitic < gerund < meaning


def test_speech_channel_contract():
    text = read("system.md")
    assert "---SAY---" in text
    assert "ONLY the European-Portuguese text" in text
    assert "one to three short sentences" in text


def test_warmup_production_oriented_retrieval():
    text = read("warmup.md")
    assert "Diz em português: I'll order a soup" in text
    assert "SAY the past sentences in Portuguese" in text


def test_warmup_grammar_and_production_rules():
    text = read("warmup.md")
    assert "micro-explanation" in text
    assert "1-3 sentences" in text
    assert "grammar-free" in text
    assert "at least once per session" in text
    assert "≥95%" in text


def test_progression_table_accent_example():
    text = read("system.md")
    assert '"voce esta bem?" instead of "você está bem?"' in text


def test_new_sentences_carry_english_gloss():
    system = read("system.md")
    assert "WITH its English gloss" in system
    assert "never present a new sentence bare" in system
    warmup = read("warmup.md")
    assert "always carry the gloss at once" in warmup


def test_gloss_free_recall_reserved_for_review():
    system = read("system.md")
    assert "REVIEW sentences only" in system
