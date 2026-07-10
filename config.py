import os
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
