import json
from datetime import datetime

from openai import OpenAI

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    PROMPTS_DIR,
    SESSIONS_DIR,
)
from progress import (
    add_vocabulary,
    get_review_words,
    get_vocab_for_prompt,
    load_summary,
    load_vocabulary,
    save_summary,
    save_vocabulary,
)


class ConversationEngine:
    def __init__(self):
        self.client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        self.summary = load_summary()
        self.vocabulary = load_vocabulary()
        self.messages: list[dict] = []
        self.session_log: list[str] = []
        self.new_words: list[dict] = []
        self.session_start = datetime.now()
        self._build_system_prompt()

    def _build_system_prompt(self):
        template = (PROMPTS_DIR / "system.md").read_text()
        level = self._extract_level()
        content = template.format(
            level=level,
            summary=self.summary,
            vocabulary=get_vocab_for_prompt(self.vocabulary),
        )
        self.messages = [{"role": "system", "content": content}]

    def _extract_level(self) -> str:
        for line in self.summary.splitlines():
            if "current level" in line.lower():
                for level in ["A1", "A2", "B1"]:
                    if level in line:
                        return level
        return "A1"

    def get_status_report(self) -> str:
        level = self._extract_level()
        review = get_review_words(self.vocabulary)
        sessions = 0
        for line in self.summary.splitlines():
            if "sessions completed" in line.lower():
                try:
                    sessions = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
                break

        parts = [f"Level: {level}"]
        if sessions > 0:
            parts.append(f"Sessions: {sessions}")
        if review:
            parts.append(f"Words due for review: {len(review)}")
        parts.append(f"Session started: {self.session_start.strftime('%Y-%m-%d %H:%M')}")
        return " | ".join(parts)

    def start_warmup(self) -> str:
        template = (PROMPTS_DIR / "warmup.md").read_text()
        content = template.format(
            summary=self.summary,
            vocabulary=get_vocab_for_prompt(self.vocabulary),
        )
        self.messages.append({"role": "user", "content": content})
        response = self._call_llm()
        self._log("system", "(warm-up started)")
        self._log("assistant", response)
        return response

    def user_message(self, text: str, is_voice: bool = False) -> str:
        prefix = "[voice] " if is_voice else ""
        self.messages.append({"role": "user", "content": f"{prefix}{text}"})
        self._log("user", f"{prefix}{text}")

        response = self._call_llm()
        self.messages.append({"role": "assistant", "content": response})
        self._log("assistant", response)

        self._extract_vocab_from_exchange(text, response)
        return response

    def _call_llm(self) -> str:
        resp = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=self.messages,
            max_tokens=500,
            temperature=0.7,
        )
        return resp.choices[0].message.content or ""

    def _extract_vocab_from_exchange(self, user_msg: str, assistant_msg: str):
        extract_prompt = [
            {
                "role": "system",
                "content": (
                    "Extract any new Portuguese vocabulary words "
                    "introduced in this exchange. "
                    "Return JSON array: "
                    '[{"word": "...", "english": "...", "context": "..."}]. '
                    "Return empty array [] if no new words. ONLY return JSON, no other text."
                ),
            },
            {"role": "user", "content": f"User: {user_msg}\nTutor: {assistant_msg}"},
        ]
        try:
            resp = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=extract_prompt,
                max_tokens=300,
                temperature=0,
            )
            text = resp.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            words = json.loads(text)
            for w in words:
                if isinstance(w, dict) and "word" in w and "english" in w:
                    self.vocabulary = add_vocabulary(
                        self.vocabulary,
                        w["word"],
                        w["english"],
                        w.get("context", ""),
                    )
                    self.new_words.append(w)
        except Exception:
            pass

    def _log(self, role: str, text: str):
        self.session_log.append(f"[{role}] {text}")

    def end_session(self) -> str:
        save_vocabulary(self.vocabulary)

        session_path = SESSIONS_DIR / f"{self.session_start.strftime('%Y-%m-%d-%H%M')}.md"
        session_path.write_text("\n\n".join(self.session_log))

        summary_prompt = [
            {
                "role": "system",
                "content": (
                    "You are updating a learner's progress summary. Given the current summary "
                    "and the session transcript, produce an UPDATED summary that:\n"
                    "1. Increments sessions completed\n"
                    "2. Adds this session to Recent Sessions (keep only last 5)\n"
                    "3. Updates strengths/weaknesses based on performance\n"
                    "4. Updates grammar progress if applicable\n"
                    "5. Sets the correct current level (A1/A2/B1)\n"
                    "Keep the same markdown format. Be concise."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## Current Summary\n{self.summary}\n\n"
                    f"## Session Transcript\n" + "\n".join(self.session_log[-20:])
                ),
            },
        ]
        try:
            resp = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=summary_prompt,
                max_tokens=800,
                temperature=0,
            )
            new_summary = resp.choices[0].message.content.strip()
            if new_summary:
                save_summary(new_summary)
        except Exception:
            pass

        word_count = len(self.new_words)
        return f"Session saved. {word_count} new words added. See you next time!"
