"""Speech-channel contract shared by CLI, web, and audio backends.

A tutor response may end with a ``---SAY---`` line; everything after it is
the ONLY text to speak (pt-PT, no markdown). Dep-free so fala.py imports it
without pulling the audio stack.
"""

_SAY_MARKER = "---SAY---"


def extract_speech_text(response: str) -> tuple[str, str | None]:
    """Split a tutor response into (display_text, speech_text|None).

    Returns speech_text=None when no ---SAY--- marker is present; the caller
    speaks the display text (markdown-stripped) instead.
    """
    if _SAY_MARKER in response:
        display, _, speech = response.partition(_SAY_MARKER)
        return display.strip(), speech.strip()
    return response, None
