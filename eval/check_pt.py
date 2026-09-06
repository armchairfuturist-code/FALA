"""Offline pt-PT reply fixtures. No API key, runs in pytest and standalone.

Usage: .venv/bin/python eval/check_pt.py
Exits nonzero on the first rule break.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from speech_text import extract_speech_text

GERUND = re.compile(r"\b\w+(ando|endo|indo)\b")
BR_WORDS = ["ônibus", "trem", "menino", "menina", "tchau", "legal", "você está"]


def check(reply: str, needs_say: bool = True) -> list[str]:
    errs = []
    display, speech = extract_speech_text(reply)
    if needs_say and speech is None:
        errs.append("missing ---SAY--- section")
    pt = speech if speech is not None else display
    if GERUND.search(pt):
        errs.append(f"gerund in speech text: {GERUND.search(pt).group(0)}")
    low = pt.lower()
    for w in BR_WORDS:
        if w in low:
            errs.append(f"BR word in speech text: {w}")
    return errs


GOOD = """Vou pedir uma sopa, por favor. (I'll order a soup, please.)
Agora tu: repete.
---SAY---
Vou pedir uma sopa, por favor."""

BAD_GERUND = """Estou falando contigo.
---SAY---
Estou falando contigo."""

BAD_BR = """Vou apanhar o ônibus.
---SAY---
Vou apanhar o ônibus."""

BAD_NOSAY = """Vou pedir uma sopa, por favor."""


def main() -> int:
    cases = [
        ("good glossed reply", GOOD, []),
        ("gerund reply", BAD_GERUND, ["gerund"]),
        ("BR vocab reply", BAD_BR, ["BR word"]),
        ("no SAY section", BAD_NOSAY, ["---SAY---"]),
    ]
    failed = 0
    for name, reply, want in cases:
        errs = check(reply)
        ok = all(any(w in e for e in errs) for w in want) and (bool(errs) == bool(want))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" -> {errs}"))
        failed += not ok
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
