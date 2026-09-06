from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from config import DATA_DIR, GUARDRAILS, UserPaths, paths_for_user

# Vocab entries are heterogeneous: "word", "english", "context", "last_reviewed"
# are str; "ease"/"confidence" float; "interval" int; "needs_review" bool.
VocabEntry = dict[str, Any]

# Paths for the default (flat data/) user. Rebuilt on module reload, so tests
# that patch config constants then reload progress keep working.
DEFAULT_PATHS = paths_for_user()


def _resolve(paths: UserPaths | None) -> UserPaths:
    return paths if paths is not None else DEFAULT_PATHS


def atomic_write_text(path: Path, text: str) -> None:
    """Write text to path atomically: tmp file in the same dir + os.replace.

    A crash mid-write can never leave a torn file at path — readers see
    either the old content or the new content, never a partial write.
    """
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# CEFR frequency word list
# ---------------------------------------------------------------------------

_CEFR_BANDS = {
    "A1": 500,
    "A2": 2000,
    "B1": 5000,
}
_frequency_words: dict[str, int] | None = None  # word -> rank (0-indexed)


def _load_frequency_words() -> dict[str, int]:
    """Load pt_50k.txt and return word -> rank mapping."""
    global _frequency_words
    if _frequency_words is not None:
        return _frequency_words
    path = DATA_DIR / "pt_50k.txt"
    if not path.exists():
        _frequency_words = {}
        return _frequency_words
    result: dict[str, int] = {}
    text = path.read_text(encoding="utf-8")
    for i, line in enumerate(text.strip().splitlines()):
        word = line.split(" ", 1)[0] if " " in line else line.strip()
        word = word.strip().lower()
        if word:
            result[word] = i
    _frequency_words = result
    return result


def _cefr_band(rank: int) -> str:
    """Return the CEFR band for a given frequency rank."""
    for band, threshold in [("A1", 500), ("A2", 2000), ("B1", 5000)]:
        if rank < threshold:
            return band
    return "B2+"


def vocabulary_report(entries: list[VocabEntry]) -> VocabEntry:
    """Return a report with CEFR breakdown and SRS stats.

    Returns:
        dict with keys:
        - total_words: int
        - cefr: dict[str, int]  # band -> count
        - mature_words: int  # confidence >= 0.7
        - average_confidence: float
        - due_for_review: int
    """
    freqs = _load_frequency_words()

    cefr_counts: dict[str, int] = {}
    mature = 0
    total_conf = 0.0
    due = 0

    for e in entries:
        word = e.get("word", "").lower()
        confidence = e.get("confidence", 0.0)
        needs_review = e.get("needs_review", True)

        # CEFR band
        rank = freqs.get(word)
        if rank is not None:
            band = _cefr_band(rank)
        else:
            band = "B2+"  # not in top 50k = uncommon
        cefr_counts[band] = cefr_counts.get(band, 0) + 1

        # SRS stats
        if confidence >= 0.7:
            mature += 1
        total_conf += confidence
        if needs_review:
            due += 1

    if not entries:
        return {
            "total_words": 0,
            "cefr": {},
            "mature_words": 0,
            "average_confidence": 0.0,
            "due_for_review": 0,
        }

    return {
        "total_words": len(entries),
        "cefr": cefr_counts,
        "mature_words": mature,
        "average_confidence": total_conf / len(entries),
        "due_for_review": due,
    }


def load_summary(paths: UserPaths | None = None) -> str:
    p = _resolve(paths)
    if p.summary.exists():
        return p.summary.read_text()
    return _default_summary()


def save_summary(text: str, paths: UserPaths | None = None):
    atomic_write_text(_resolve(paths).summary, text)


def _default_summary() -> str:
    return """# Learner Profile
- Learner name: (not yet known)
- Current level: A0
- Sessions completed: 0
- Total vocabulary: 0 words
- Strengths: (none yet)
- Weaknesses: (none yet)

# Recent Sessions
(none yet)

# Grammar Progress
- [ ] Present tense (regular -ar)
- [ ] Present tense (regular -er, -ir)
- [ ] Present tense (ser, estar, ter)
- [ ] Preterite tense
- [ ] Imperfect tense
"""


def load_vocabulary(paths: UserPaths | None = None) -> list[VocabEntry]:
    p = _resolve(paths)
    if not p.vocabulary.exists():
        return []
    entries = []
    text = p.vocabulary.read_text()
    for block in text.strip().split("\n- word: "):
        if not block.strip():
            continue
        # Values are JSON-escaped on write, so they never contain a raw
        # newline — "- word: " inside a value cannot create a split point.
        # The first block already starts with "- word:"; later blocks need
        # the prefix re-added after the split consumed it.
        if not block.lstrip().startswith("- word:"):
            block = "- word: " + block
        entry = _parse_vocab_entry(block)
        if entry:
            entries.append(entry)
    return entries


def _unescape_value(value: str) -> str:
    """Undo the JSON escaping applied by _escape_value.

    Tolerates legacy files: a bare unquoted value fails json.loads and
    falls back to strip('"'), which is the old (lossy) behavior.
    """
    try:
        out = json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return value.strip('"')
    return out if isinstance(out, str) else value


def _escape_value(value: str) -> str:
    """JSON-encode a value: stays on one line, round-trips quotes/newlines."""
    return json.dumps(value, ensure_ascii=False)


def _parse_vocab_entry(block: str) -> VocabEntry | None:
    entry: VocabEntry = {}
    for line in block.strip().splitlines():
        line = line.strip()
        if line.startswith("- word:"):
            entry["word"] = _unescape_value(line.split(":", 1)[1].strip())
        elif line.startswith("english:"):
            entry["english"] = _unescape_value(line.split(":", 1)[1].strip())
        elif line.startswith("context:"):
            entry["context"] = _unescape_value(line.split(":", 1)[1].strip())
        elif line.startswith("ease:"):
            try:
                entry["ease"] = float(line.split(":", 1)[1].strip())
            except ValueError:
                entry["ease"] = 2.5
        elif line.startswith("interval:"):
            try:
                entry["interval"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                entry["interval"] = 1
        elif line.startswith("last_reviewed:"):
            entry["last_reviewed"] = line.split(":", 1)[1].strip()
        elif line.startswith("confidence:"):
            try:
                entry["confidence"] = float(line.split(":", 1)[1].strip())
            except ValueError:
                entry["confidence"] = 0.5
        elif line.startswith("needs_review:"):
            entry["needs_review"] = "true" in line.lower()
    if "word" in entry:
        entry.setdefault("ease", 2.5)
        entry.setdefault("interval", 1)
        entry.setdefault("last_reviewed", "1970-01-01")
        entry.setdefault("confidence", 0.5)
        entry.setdefault("needs_review", True)
        return entry
    return None


def save_vocabulary(entries: list[VocabEntry], paths: UserPaths | None = None):
    """Persist entries atomically. Writes exactly what is passed — callers
    own correctness: an empty list legitimately empties the file (deletions
    must be persistable); only None is rejected as a caller bug."""
    if entries is None:
        raise ValueError("save_vocabulary: entries must be a list, not None")
    p = _resolve(paths)
    lines = []
    for e in entries:
        lines.append(f"- word: {_escape_value(e['word'])}")
        lines.append(f"  english: {_escape_value(e.get('english', ''))}")
        lines.append(f"  context: {_escape_value(e.get('context', ''))}")
        lines.append(f"  ease: {e.get('ease', 2.5)}")
        lines.append(f"  interval: {e.get('interval', 1)}")
        lines.append(f"  last_reviewed: {e.get('last_reviewed', '1970-01-01')}")
        lines.append(f"  confidence: {e.get('confidence', 0.5)}")
        lines.append(f"  needs_review: {'true' if e.get('needs_review', True) else 'false'}")
        lines.append("")
    atomic_write_text(p.vocabulary, "\n".join(lines))


# ---------------------------------------------------------------------------
# SRS core: decay, dual EMA, balanced pick (open-course-cli port)
# ---------------------------------------------------------------------------

# Confidence scale is 0..1. Due below 0.5, done at/above 0.8.
MASTERY_DUE = 0.5
MASTERY_DONE = 0.8
# Forgetting: ~5%/day. effective = confidence * exp(-0.05 * days).
DECAY_RATE = 0.05
# Review cadence: every 3rd session, every 2nd when backlog >= 5.
REVIEW_EVERY = 3
REVIEW_BACKLOG = 5
REVIEW_BACKLOG_EVERY = 2
# CEFR band order for the frontier gate.
_BAND_ORDER = ("A1", "A2", "B1", "B2+")


def _days_since(date_str: str, now: datetime) -> float:
    try:
        then = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0.0
    return max(0, (now.date() - then).days)


def effective_confidence(entry: VocabEntry, now: datetime | None = None) -> float:
    """Decayed confidence: what the learner likely retains today."""
    base = float(entry.get("confidence", 0.0))
    days = _days_since(entry.get("last_reviewed", "1970-01-01"), now or datetime.now())
    return round(base * math.exp(-DECAY_RATE * days), 4)


def get_due_with_decay(
    entries: list[VocabEntry], count: int | None = None
) -> list[VocabEntry]:
    """Due words by decayed confidence, weakest first.

    Due = effective confidence below MASTERY_DUE or needs_review flag set.
    """
    if count is None:
        count = int(GUARDRAILS["min_review_words_per_warmup"])
    now = datetime.now()
    due = [
        e
        for e in entries
        if e.get("needs_review", False) or effective_confidence(e, now) < MASTERY_DUE
    ]
    due.sort(key=lambda x: effective_confidence(x, now))
    return due[:count]


def adaptive_alpha(confidence: float) -> float:
    """EMA rate for correct answers: 0.45 weak … 0.1 strong."""
    return 0.1 + 0.35 * (1.0 - min(1.0, max(0.0, confidence)))


ITEM_ALPHA = 0.34  # EMA rate toward 0.0 on wrong answers.


def _band_of(word: str) -> str:
    rank = _load_frequency_words().get(word.lower())
    if rank is None:
        return "B2+"
    return _cefr_band(rank)


def pick_session_mode(entries: list[VocabEntry], session_count: int) -> str:
    """'review' or 'new': every 3rd session reviews (2nd when backlog >= 5).

    A 'new' word above frontier+1 still yields 'review' when anything is due:
    close lower-band gaps before fresh hard material.
    """
    now = datetime.now()
    due = [e for e in entries if effective_confidence(e, now) < MASTERY_DUE]
    if not due:
        return "new"
    every = REVIEW_BACKLOG_EVERY if len(due) >= REVIEW_BACKLOG else REVIEW_EVERY
    if (session_count + 1) % every == 0:
        return "review"
    unfinished = [b for e in entries if (b := _band_of(e.get("word", ""))) in _BAND_ORDER]
    if unfinished:
        frontier = min(_BAND_ORDER.index(b) for b in unfinished)
        if frontier + 1 < len(_BAND_ORDER) - 1:
            return "review"
    return "new"


def get_review_words(entries: list[VocabEntry], count: int | None = None) -> list[VocabEntry]:
    if count is None:
        count = int(GUARDRAILS["min_review_words_per_warmup"])
    today = datetime.now().strftime("%Y-%m-%d")
    due = []
    for e in entries:
        last = e.get("last_reviewed", "1970-01-01")
        interval = e.get("interval", 1)
        try:
            next_review = datetime.strptime(last, "%Y-%m-%d") + timedelta(days=interval)
        except ValueError:
            next_review = datetime.min
        if next_review.strftime("%Y-%m-%d") <= today or e.get("needs_review", False):
            due.append(e)
    due.sort(key=lambda x: x.get("confidence", 0))
    return due[:count]


def get_review_words_with_direction(
    entries: list[VocabEntry], count: int | None = None
) -> list[VocabEntry]:
    """Return words due for review tagged with a retrieval direction.

    Testing effect: successful recall (EN -> PT production) beats recognition
    (PT -> EN). Words the learner already knows well (confidence >= 0.5) get
    direction "recall"; weak or new words stay on "recognition".

    Returns copies of the due entries (see get_review_words) with an extra
    "retrieval_direction" key. Originals are not mutated.
    """
    tagged = []
    for e in get_review_words(entries, count):
        item = dict(e)
        item["retrieval_direction"] = (
            "recall" if e.get("confidence", 0.0) >= 0.5 else "recognition"
        )
        tagged.append(item)
    return tagged


def update_vocab_after_review(
    entries: list[VocabEntry], word: str, correct: bool
) -> list[VocabEntry]:
    word_lower = word.lower()
    for e in entries:
        if e["word"].lower() == word_lower:
            today = datetime.now().strftime("%Y-%m-%d")
            e["last_reviewed"] = today
            base = float(e.get("confidence", 0.5))
            if correct:
                # Topic-style adaptive EMA toward 1.0: weak moves fast.
                e["confidence"] = min(1.0, base + adaptive_alpha(base) * (1.0 - base))
                e["ease"] = max(1.3, e.get("ease", 2.5) + 0.1)
                e["interval"] = max(1, int(e.get("interval", 1) * e["ease"]))
                if e["confidence"] >= MASTERY_DONE:
                    e["needs_review"] = False
            else:
                # Item-style fixed EMA toward 0.0.
                e["confidence"] = max(0.0, base * (1.0 - ITEM_ALPHA))
                e["ease"] = max(1.3, e.get("ease", 2.5) - 0.2)
                e["interval"] = 1
                e["needs_review"] = True
            break
    return entries


def add_vocabulary(
    entries: list[VocabEntry], word: str, english: str, context: str = ""
) -> list[VocabEntry]:
    word_lower = word.lower()
    for e in entries:
        if e["word"].lower() == word_lower:
            # Update english/context if they were empty
            if not e.get("english") and english:
                e["english"] = english
            if not e.get("context") and context:
                e["context"] = context
            return entries
    entries.append(
        {
            "word": word,
            "english": english,
            "context": context,
            "ease": 2.5,
            "interval": 1,
            "last_reviewed": datetime.now().strftime("%Y-%m-%d"),
            "confidence": 0.3,
            "needs_review": True,
        }
    )
    return entries


def save_learning_record(title: str, content: str, paths: UserPaths | None = None):
    up = _resolve(paths)
    existing = list(up.records.glob("*.md"))
    nums = [int(p.stem.split("-")[0]) for p in existing if p.stem.split("-")[0].isdigit()]
    num = max(nums) + 1 if nums else 1
    slug = title.lower().replace(" ", "-")[:40]
    path = up.records / f"{num:04d}-{slug}.md"
    stamp = datetime.now().strftime("%Y-%m-%d")
    atomic_write_text(path, f"# {title}\n\nDate: {stamp}\n\n{content}\n")


def get_vocab_for_prompt(entries: list[VocabEntry], count: int = 15) -> str:
    review = get_review_words_with_direction(entries, count)
    if not review:
        return "(no vocabulary yet — this is the first session)"
    lines = []
    for e in review:
        conf = e.get("confidence", 0.5)
        direction = e.get("retrieval_direction", "recognition")
        lines.append(
            f"- {e['word']} ({e.get('english', '?')}) — confidence: {conf:.0%} "
            f"[review direction: {direction}]"
        )
    return "\n".join(lines)


def normalize_answer(text: str) -> str:
    """Accent/case/punct-blind compare form: 'Você Está Bem?' -> 'voce esta bem'."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def check_review_answer(expected: str, given: str) -> bool:
    """True when the learner's PT production matches, ignoring accents/case."""
    return bool(given.strip()) and normalize_answer(given) == normalize_answer(expected)
