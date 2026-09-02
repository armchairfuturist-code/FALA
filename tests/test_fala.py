"""Smoke tests for fala.py — CLI entrypoint."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock


def test_cli_banner_shown():
    """Running fala.py should show the tutor banner before any error."""
    project_dir = Path(__file__).resolve().parent.parent
    fala_script = project_dir / "fala.py"
    venv_python = project_dir / ".venv" / "bin" / "python"

    # Use the venv python; pass dummy API key so OpenAI client init passes
    env = {"FALA_API_KEY": "sk-test-dummy", "PYTHONPATH": str(project_dir)}
    result = subprocess.run(
        [str(venv_python), str(fala_script)],
        input="quit\n",
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )

    # The banner should appear in either stdout or stderr
    combined = result.stdout + result.stderr
    assert "fala" in combined.lower() or "FALA" in combined
    assert "Portuguese" in combined or "portugu" in combined.lower()


def test_cli_quit_exits():
    """Sending 'quit' should terminate the process."""
    project_dir = Path(__file__).resolve().parent.parent
    fala_script = project_dir / "fala.py"
    venv_python = project_dir / ".venv" / "bin" / "python"

    env = {"FALA_API_KEY": "sk-test-dummy", "PYTHONPATH": str(project_dir)}
    result = subprocess.run(
        [str(venv_python), str(fala_script)],
        input="quit\n",
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )

    # Process should exit (returncode may be 0 or 1 depending on where
    # in the flow 'quit' is processed — the key is that it terminates)
    assert result.returncode in (0, 1)


class TestPrintTutor:
    """The CLI panel must show display text, never the ---SAY--- marker (N1)."""

    def _capture_panel(self, monkeypatch):
        import fala

        panels = []
        fake_console = MagicMock()
        monkeypatch.setattr(fala, "console", fake_console)
        monkeypatch.setattr(fala, "AUDIO_AVAILABLE", False)

        class FakePanel:
            def __init__(self, text, **kwargs):
                panels.append(text)

        monkeypatch.setattr(fala, "Panel", FakePanel)
        return fala, panels

    def test_panel_shows_display_text_marker_stripped(self, monkeypatch):
        fala, panels = self._capture_panel(monkeypatch)
        fala.print_tutor("Bom dia! Good morning.\n---SAY---\nBom dia!")
        assert panels == ["Bom dia! Good morning."]

    def test_panel_without_marker_shows_text(self, monkeypatch):
        fala, panels = self._capture_panel(monkeypatch)
        fala.print_tutor("Plain reply")
        assert panels == ["Plain reply"]

    def test_print_tutor_speaks_only_speech_text(self, monkeypatch):
        import fala

        spoken = {}
        fake_console = MagicMock()
        monkeypatch.setattr(fala, "console", fake_console)
        monkeypatch.setattr(fala, "AUDIO_AVAILABLE", True)
        monkeypatch.setattr(fala, "speak", lambda t: spoken.update(t=t) or True)
        fala.print_tutor("Display.\n---SAY---\nFala isto.", speak_audio=True)
        assert spoken["t"] == "Fala isto."


def test_cli_voice_toggle_in_banner():
    """Banner should mention /voice toggle."""
    project_dir = Path(__file__).resolve().parent.parent
    fala_script = project_dir / "fala.py"
    venv_python = project_dir / ".venv" / "bin" / "python"

    env = {"FALA_API_KEY": "sk-test-dummy", "PYTHONPATH": str(project_dir)}
    result = subprocess.run(
        [str(venv_python), str(fala_script)],
        input="quit\n",
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )

    combined = result.stdout + result.stderr
    assert "/voice" in combined
