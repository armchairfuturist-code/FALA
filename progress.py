from datetime import datetime, timedelta

from config import GUARDRAILS, RECORDS_DIR, SUMMARY_PATH, VOCABULARY_PATH


def load_summary() -> str:
    if SUMMARY_PATH.exists():
        return SUMMARY_PATH.read_text()
    return _default_summary()


def save_summary(text: str):
    SUMMARY_PATH.write_text(text)


def _default_summary() -> str:
    return """# Learner Profile
- Current level: A1
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


def load_vocabulary() -> list[dict]:
    if not VOCABULARY_PATH.exists():
        return []
    entries = []
    text = VOCABULARY_PATH.read_text()
    for block in text.strip().split("\n- word: "):
        if not block.strip():
            continue
        # The first block (before any "\n- word: " split) already starts
        # with "- word:" — pass it through directly.
        # Later blocks start with the word content after the split point
        # and need the "- word: " prefix re-added.
        if block.lstrip().startswith("- word:"):
            entry = _parse_vocab_entry(block)
        elif block.startswith('"'):
            entry = _parse_vocab_entry("- word: " + block)
        else:
            block = '"' + block
            entry = _parse_vocab_entry("- word: " + block)
        if entry:
            entries.append(entry)
    return entries


def _parse_vocab_entry(block: str) -> dict | None:
    entry = {}
    for line in block.strip().splitlines():
        line = line.strip()
        if line.startswith("- word:"):
            entry["word"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("english:"):
            entry["english"] = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("context:"):
            entry["context"] = line.split(":", 1)[1].strip().strip('"')
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


def save_vocabulary(entries: list[dict]):
    lines = []
    for e in entries:
        lines.append(f'- word: "{e["word"]}"')
        lines.append(f'  english: "{e.get("english", "")}"')
        lines.append(f'  context: "{e.get("context", "")}"')
        lines.append(f"  ease: {e.get('ease', 2.5)}")
        lines.append(f"  interval: {e.get('interval', 1)}")
        lines.append(f"  last_reviewed: {e.get('last_reviewed', '1970-01-01')}")
        lines.append(f"  confidence: {e.get('confidence', 0.5)}")
        lines.append(f"  needs_review: {'true' if e.get('needs_review', True) else 'false'}")
        lines.append("")
    VOCABULARY_PATH.write_text("\n".join(lines))


def get_review_words(entries: list[dict], count: int | None = None) -> list[dict]:
    if count is None:
        count = GUARDRAILS["min_review_words_per_warmup"]
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


def update_vocab_after_review(entries: list[dict], word: str, correct: bool) -> list[dict]:
    for e in entries:
        if e["word"] == word:
            today = datetime.now().strftime("%Y-%m-%d")
            e["last_reviewed"] = today
            if correct:
                e["confidence"] = min(1.0, e.get("confidence", 0.5) + 0.15)
                e["ease"] = max(1.3, e.get("ease", 2.5) + 0.1)
                e["interval"] = max(1, int(e.get("interval", 1) * e["ease"]))
                if e["confidence"] >= 0.8:
                    e["needs_review"] = False
            else:
                e["confidence"] = max(0.0, e.get("confidence", 0.5) - 0.2)
                e["ease"] = max(1.3, e.get("ease", 2.5) - 0.2)
                e["interval"] = 1
                e["needs_review"] = True
            break
    return entries


def add_vocabulary(entries: list[dict], word: str, english: str, context: str = "") -> list[dict]:
    for e in entries:
        if e["word"] == word:
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


def save_learning_record(title: str, content: str):
    existing = list(RECORDS_DIR.glob("*.md"))
    num = len(existing) + 1
    slug = title.lower().replace(" ", "-")[:40]
    path = RECORDS_DIR / f"{num:04d}-{slug}.md"
    path.write_text(f"# {title}\n\nDate: {datetime.now().strftime('%Y-%m-%d')}\n\n{content}\n")


def get_vocab_for_prompt(entries: list[dict], count: int = 15) -> str:
    review = get_review_words(entries, count)
    if not review:
        return "(no vocabulary yet — this is the first session)"
    lines = []
    for e in review:
        conf = e.get("confidence", 0.5)
        lines.append(f"- {e['word']} ({e.get('english', '?')}) — confidence: {conf:.0%}")
    return "\n".join(lines)
