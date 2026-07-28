import os
import re
from dataclasses import dataclass
from pathlib import Path

# Load .env file if present (for development convenience)
# Skip if FALA_SKIP_DOTENV is set (used by tests)
try:
    from dotenv import load_dotenv

    if not os.getenv("FALA_SKIP_DOTENV"):
        _env_path = Path(__file__).parent / ".env"
        if _env_path.exists():
            load_dotenv(_env_path)
except ImportError:
    pass

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
RECORDS_DIR = DATA_DIR / "records"
PROMPTS_DIR = PROJECT_DIR / "prompts"

SUMMARY_PATH = DATA_DIR / "summary.md"
VOCABULARY_PATH = DATA_DIR / "vocabulary.md"

for d in [DATA_DIR, SESSIONS_DIR, RECORDS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Per-user paths
# ---------------------------------------------------------------------------

# The special user id "default" maps to the EXISTING flat data/ layout so the
# current single-user CLI keeps working with zero file migration.
DEFAULT_USER = "default"

_USER_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class UserPaths:
    """Filesystem locations for one user's persisted data."""

    user_id: str
    data_dir: Path
    summary: Path
    vocabulary: Path
    sessions: Path
    records: Path


def paths_for_user(user_id: str = DEFAULT_USER) -> UserPaths:
    """Resolve storage paths for a user, creating directories as needed.

    "default" -> the flat data/ layout (existing CLI behavior, no migration).
    Any other id -> data/users/<user_id>/{summary.md, vocabulary.md,
    sessions/, records/}.

    Reads module-level path constants at call time so tests can monkeypatch
    DATA_DIR & friends before calling.
    """
    if not _USER_ID_RE.match(user_id):
        raise ValueError(f"Invalid user id {user_id!r}: only letters, digits, '-' and '_' allowed")
    if user_id == DEFAULT_USER:
        return UserPaths(
            user_id=user_id,
            data_dir=DATA_DIR,
            summary=SUMMARY_PATH,
            vocabulary=VOCABULARY_PATH,
            sessions=SESSIONS_DIR,
            records=RECORDS_DIR,
        )
    base = DATA_DIR / "users" / user_id
    sessions = base / "sessions"
    records = base / "records"
    for d in (base, sessions, records):
        d.mkdir(parents=True, exist_ok=True)
    return UserPaths(
        user_id=user_id,
        data_dir=base,
        summary=base / "summary.md",
        vocabulary=base / "vocabulary.md",
        sessions=sessions,
        records=records,
    )


LLM_MODEL = os.getenv("FALA_MODEL", "gpt-4o")
LLM_BASE_URL = os.getenv("FALA_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("FALA_API_KEY") or os.getenv("OPENAI_API_KEY", "")

TTS_PROVIDER = os.getenv("FALA_TTS", "openai")
TTS_VOICE = os.getenv("FALA_TTS_VOICE", "alloy")

STT_MODEL = os.getenv("FALA_STT_MODEL", "base")

GUARDRAILS = {
    "max_new_words_per_session": 5,
    "min_review_words_per_warmup": 3,
    "present_tense_confidence_threshold": 0.7,
}

LEVEL_ORDER = ["A1", "A2", "B1"]
