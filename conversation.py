import json
import logging
import re
from datetime import datetime

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from audio import extract_speech_text
from config import (
    CONTEXT_MESSAGES,
    GUARDRAILS,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    PROMPTS_DIR,
    paths_for_user,
)
from progress import (
    add_confusion,
    add_vocabulary,
    atomic_write_text,
    check_review_answer,
    confused_words,
    get_review_words,
    get_vocab_for_prompt,
    load_confusions,
    load_summary,
    load_vocabulary,
    log_review,
    pick_session_mode,
    review_accuracy,
    save_confusions,
    save_learning_record,
    save_summary,
    save_vocabulary,
    update_vocab_after_review,
    vocabulary_report,
    weak_words,
)

logger = logging.getLogger(__name__)


class ConversationEngine:
    def __init__(self, user_id: str = "default"):
        if not LLM_API_KEY:
            raise ValueError(
                "No API key configured. Set FALA_API_KEY or OPENAI_API_KEY environment variable.\n"
                "Get a free key at https://console.groq.com/keys, then:\n"
                "  cp .env.example .env\n"
                "  # edit .env with your key\n"
                "  source .env\n"
                "Or see .env.example for instructions."
            )
        self.user_id = user_id
        self.paths = paths_for_user(user_id)
        self.client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        self.summary = load_summary(paths=self.paths)
        self.vocabulary = load_vocabulary(paths=self.paths)
        self.confusions = load_confusions(paths=self.paths)
        self.messages: list[ChatCompletionMessageParam] = []
        self.session_log: list[str] = []
        self.history: list[dict] = []  # [{role: user|tutor, content}] for the web UI
        self.new_words: list[dict] = []
        self.session_start = datetime.now()
        self._warmup_done = False
        self._build_system_prompt()

    def _build_system_prompt(self):
        template = (PROMPTS_DIR / "system.md").read_text()
        level = self._extract_level()
        content = template.format(
            level=level,
            summary=self.summary,
            vocabulary=get_vocab_for_prompt(self.vocabulary, confusions=self.confusions),
        )
        self.messages = [{"role": "system", "content": content}]

    _KNOWN_LEVELS = ("A0", "A1", "A2", "B1", "B2", "C1", "C2")

    def _extract_level(self) -> str:
        """Extract the learner's current level from the summary.

        Deterministic: first try a strict parse of the value after the colon;
        if that fails, return the FIRST known level appearing in the line,
        scanning in fixed A0..C2 order (so "Current level: A1 (goal B1)"
        always yields A1, never B1).
        """
        for line in self.summary.splitlines():
            if "current level" in line.lower():
                # Strict parse: the value after the colon must be exactly a level
                parts = line.split(":", 1)
                if len(parts) == 2:
                    candidate = parts[1].strip().strip(".,;")
                    if candidate in self._KNOWN_LEVELS:
                        return candidate
                # Fallback: first known level in the line, fixed order
                for level in self._KNOWN_LEVELS:
                    if level in line:
                        return level
        return "A0"

    def get_status_report(self) -> str:
        level = self._extract_level()
        review = get_review_words(self.vocabulary)
        sessions = 0
        for line in self.summary.splitlines():
            if "sessions completed" in line.lower():
                # Tolerant parse: the LLM writes this line, so it may carry
                # trailing prose — "Sessions completed: 3 (this month)".
                match = re.search(r"\d+", line.split(":")[-1])
                if match:
                    sessions = int(match.group())
                break

        parts = [f"Level: {level}"]
        if sessions > 0:
            parts.append(f"Sessions: {sessions}")
        parts.append(f"Focus: {pick_session_mode(self.vocabulary, sessions)}")
        if review:
            parts.append(f"Words due for review: {len(review)}")
        parts.append(f"Session started: {self.session_start.strftime('%Y-%m-%d %H:%M')}")
        return " | ".join(parts)

    def get_review_drill(self, count: int = 5) -> list[dict]:
        """Due words as production prompts: cloze gap-fill when the word has
        a context sentence, else EN→PT. No LLM call, works offline."""
        from progress import get_due_with_decay, make_cloze

        drill = []
        due = get_due_with_decay(self.vocabulary, count)
        mixed = confused_words(self.confusions)
        due.sort(key=lambda e: (e["word"].lower() not in mixed))
        for e in due:
            cloze = make_cloze(self.vocabulary, e["word"])
            drill.append(
                {
                    "word": e["word"],
                    "english": e.get("english", ""),
                    "cloze": cloze["prompt"],
                    "options": cloze["options"],
                }
            )
        return drill

    def submit_review_answer(self, word: str, given: str) -> bool:
        """Grade one drill answer, update SRS, persist. Returns True if right."""
        expected = next(
            (e["word"] for e in self.vocabulary if e["word"].lower() == word.lower()), word
        )
        correct = check_review_answer(expected, given)
        self.vocabulary = update_vocab_after_review(self.vocabulary, expected, correct)
        save_vocabulary(self.vocabulary, paths=self.paths)
        log_review(expected, correct, paths=self.paths)
        return correct

    def get_stats(self) -> str:
        """Return CEFR breakdown + SRS stats for mid-session /stats command."""
        report = vocabulary_report(self.vocabulary)
        total = report["total_words"]
        if total == 0:
            return "No vocabulary yet. Start a session to build your word bank!"

        cefr_parts = " · ".join(
            f"{band}: {count}" for band, count in sorted(report["cefr"].items())
        )
        lines = [
            f"Vocabulary: {total} words ({cefr_parts})",
            f"Mature words (≥0.7): {report['mature_words']}",
            f"Avg confidence: {report['average_confidence']:.0%}",
            f"Due for review: {report['due_for_review']}",
        ]
        acc, n = review_accuracy(paths=self.paths)
        lines.append(
            f"Review accuracy (7d): {acc:.0%} ({n} answers)" if n else "Review accuracy: -"
        )
        weak = [e for e in weak_words(self.vocabulary) if e.get("needs_review", True)][:5]
        if weak:
            lines.append(
                "Weakest: " + ", ".join(f"{e['word']} ({e.get('confidence', 0):.0%})" for e in weak)
            )
        return "\n".join(lines)

    def start_warmup(self) -> str:
        if self._warmup_done:
            return "[Warm-up already completed this session]"
        template = (PROMPTS_DIR / "warmup.md").read_text()
        # count=5 (not the default 15): warmup.md asks the tutor to pick 1-2
        # past sentences — 15 candidates oversell the review load.
        content = template.format(
            summary=self.summary,
            vocabulary=get_vocab_for_prompt(
                self.vocabulary, count=5, confusions=self.confusions
            ),
        )
        self.messages.append({"role": "user", "content": content})
        prompt_idx = len(self.messages) - 1
        response = self._call_llm()
        # Keep the tutor's greeting in the message history so later turns have
        # the full warm-up exchange (system / user / assistant alternation).
        self.messages.append({"role": "assistant", "content": response})
        self._append_tutor_history(response)
        self._log("system", "(warm-up started)")
        self._log("assistant", response)
        # Replace the warmup template with a concise context marker so the LLM
        # doesn't re-read the entire template on every subsequent turn. It
        # stays a *user* message so roles keep alternating (system/user/
        # assistant) — adjacent system messages break some OpenAI-compatible
        # backends (vLLM, some Groq models).
        if prompt_idx > 0:
            self.messages[prompt_idx] = {
                "role": "user",
                "content": (
                    "[The warm-up phase is complete. You greeted the learner and "
                    "started the conversation. Now continue naturally in response "
                    "to their messages.]"
                ),
            }
        self._warmup_done = True
        self.save_checkpoint()
        return response

    def user_message(self, text: str, is_voice: bool = False) -> str:
        prefix = "[voice] " if is_voice else ""
        self.messages.append({"role": "user", "content": f"{prefix}{text}"})
        self.history.append({"role": "user", "content": text})
        self._log("user", f"{prefix}{text}")

        response = self._call_llm()
        self.messages.append({"role": "assistant", "content": response})
        self._append_tutor_history(response)
        self._log("assistant", response)

        self._extract_vocab_from_exchange(text, response)
        self.save_checkpoint()
        return response

    def _append_tutor_history(self, response: str):
        """Append a tutor turn to the web-display history.

        The LLM context (self.messages) keeps the RAW response, but history is
        rendered/resumed as chat text, so it stores the display text (marker
        stripped) plus the speech text alongside for faithful replay.
        """
        display, speech = extract_speech_text(response)
        self.history.append({"role": "tutor", "content": display, "speech": speech})

    def get_history(self) -> list[dict]:
        """Return the conversation transcript for display (user/tutor turns)."""
        return list(self.history)

    def _windowed_messages(self) -> list[ChatCompletionMessageParam]:
        """Return the messages to send to the LLM.

        Keeps the system prompt and the warm-up context marker (first
        non-system message after it) always in view, plus the most recent
        messages, capped at CONTEXT_MESSAGES. Without this, context size and
        per-turn cost grow quadratically over a long session.
        """
        msgs = self.messages
        if len(msgs) <= CONTEXT_MESSAGES:
            return list(msgs)
        head = [msgs[0]]
        marker: list[ChatCompletionMessageParam] = []
        if (
            len(msgs) > 1
            and msgs[1].get("role") in ("system", "user")
            and str(msgs[1].get("content", "")).startswith("[The warm-up phase is complete")
        ):
            marker = [msgs[1]]
        remaining = CONTEXT_MESSAGES - len(head) - len(marker)
        tail = list(msgs[-remaining:]) if remaining > 0 else []
        return head + marker + tail

    def _call_llm(self) -> str:
        resp = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=self._windowed_messages(),
            max_tokens=500,
            temperature=0.7,
            timeout=30,
        )
        return resp.choices[0].message.content or ""

    def _extract_vocab_from_exchange(self, user_msg: str, assistant_msg: str):
        """Extract new words and assess review words from an exchange."""
        # Per-session guardrail: cap counts ALL new words this session, not
        # just this exchange. Once the cap is reached, skip the whole vocab
        # extraction LLM call (saves a call per turn) — audit 2026 #2.
        remaining = GUARDRAILS["max_new_words_per_session"] - len(self.new_words)
        if remaining <= 0:
            return

        # Collect words currently needing review so we can assess them
        review_candidates = [e["word"] for e in self.vocabulary if e.get("needs_review", False)]

        prompt_text = (
            "Analyse this learner-tutor exchange and return a JSON object.\n\n"
            "1. Extract any NEW Portuguese vocabulary words introduced by the tutor.\n"
            "2. For each review word that the LEARNER attempted to use (not the tutor), "
            "assess whether the learner used it correctly.\n"
            "3. Note any pair of words the learner mixed up "
            '(e.g. "ser" vs "estar").\n\n'
            "Return ONLY JSON with this shape, no other text:\n"
            "{\n"
            '  "new_words": [{"word": "...", "english": "...", "context": "..."}],\n'
            '  "assessments": [{"word": "...", "correct": true}],\n'
            '  "confusions": [{"pair": ["...", "..."], "note": "..."}],\n'
            '  "notes": "..."\n'
            "}\n\n"
        )
        if review_candidates:
            prompt_text += (
                f"Review words the learner may have attempted: {', '.join(review_candidates)}\n\n"
            )
        prompt_text += f"User: {user_msg}\nTutor: {assistant_msg}"

        extract_prompt: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": prompt_text},
        ]
        try:
            resp = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=extract_prompt,
                max_tokens=300,
                temperature=0,
                timeout=30,
            )
            text = (resp.choices[0].message.content or "").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            data = json.loads(text)

            # Cap the slice at the remaining per-session allowance
            new_words_raw = data.get("new_words", [])[:remaining]

            # Extract new words
            for w in new_words_raw:
                if isinstance(w, dict) and "word" in w and "english" in w:
                    self.vocabulary = add_vocabulary(
                        self.vocabulary,
                        w["word"],
                        w["english"],
                        w.get("context", ""),
                    )
                    self.new_words.append(w)

            # Assess review words
            for a in data.get("assessments", []):
                if isinstance(a, dict) and "word" in a and "correct" in a:
                    self.vocabulary = update_vocab_after_review(
                        self.vocabulary, a["word"], a["correct"]
                    )

            # Track mix-up pairs apart from word records
            for c in data.get("confusions", []):
                pair = c.get("pair", []) if isinstance(c, dict) else []
                if len(pair) == 2:
                    self.confusions = add_confusion(
                        self.confusions, pair[0], pair[1], c.get("note", "")
                    )
            if data.get("confusions"):
                save_confusions(self.confusions, paths=self.paths)
        except Exception:
            # Vocabulary extraction failing must not kill the conversation
            # turn, but it must not be silent either (audit 2026 #6).
            logger.warning(
                "Vocabulary extraction failed for exchange %r",
                user_msg[:80],
                exc_info=True,
            )

    def _log(self, role: str, text: str):
        self.session_log.append(f"[{role}] {text}")

    # ------------------------------------------------------------------
    # Session checkpoints — durable in-progress state so a web session can
    # survive a server restart or a page refresh (file-based, JSON).
    # ------------------------------------------------------------------

    CHECKPOINT_FILENAME = "session_checkpoint.json"

    @property
    def checkpoint_path(self):
        """Path of this session's checkpoint file (per-user data dir)."""
        return self.paths.data_dir / self.CHECKPOINT_FILENAME

    def has_checkpoint(self) -> bool:
        return self.checkpoint_path.exists()

    def save_checkpoint(self):
        """Persist in-progress session state so it can be restored later."""
        atomic_write_text(
            self.checkpoint_path,
            json.dumps(
                {
                    "version": 1,
                    "session_start": self.session_start.isoformat(),
                    "warmup_done": self._warmup_done,
                    "messages": self.messages,
                    "history": self.history,
                    "new_words": self.new_words,
                    "vocabulary": self.vocabulary,
                    "confusions": self.confusions,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )

    def load_checkpoint(self) -> bool:
        """Restore session state from a checkpoint file. Returns True if restored.

        A torn/corrupt checkpoint must never permanently break /start: the
        file is moved aside as <name>.corrupt-<timestamp> and a fresh session
        begins (audit 2026 #5).
        """
        if not self.has_checkpoint():
            return False
        try:
            data = json.loads(self.checkpoint_path.read_text())
            self.session_start = datetime.fromisoformat(data["session_start"])
            self.messages = data["messages"]
            self.history = data.get("history", [])
            self.new_words = data["new_words"]
            self.vocabulary = data["vocabulary"]
            self.confusions = data.get("confusions", [])
            self._warmup_done = data["warmup_done"]
            return True
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            logger.warning(
                "Corrupt checkpoint at %s: %s — starting a fresh session",
                self.checkpoint_path,
                exc,
                exc_info=True,
            )
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            corrupt_path = self.checkpoint_path.with_name(
                f"{self.checkpoint_path.name}.corrupt-{stamp}"
            )
            try:
                self.checkpoint_path.rename(corrupt_path)
            except OSError:
                logger.warning("Could not move corrupt checkpoint aside", exc_info=True)
            return False

    def clear_checkpoint(self):
        """Remove the checkpoint file (e.g. after the session is saved)."""
        self.checkpoint_path.unlink(missing_ok=True)

    def end_session(self) -> str:
        save_vocabulary(self.vocabulary, paths=self.paths)

        session_path = self.paths.sessions / f"{self.session_start.strftime('%Y-%m-%d-%H%M%S')}.md"
        atomic_write_text(session_path, "\n\n".join(self.session_log))

        # Build actual vocabulary list for the LLM so word count is accurate
        actual_vocab_list = (
            ", ".join(e["word"] for e in self.vocabulary) if self.vocabulary else "(none)"
        )

        summary_prompt: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": (
                    "You are updating a learner's progress summary. Given the current summary "
                    "and the session transcript, produce an UPDATED summary that:\n"
                    "1. Increments sessions completed\n"
                    "2. Adds this session to Recent Sessions (keep only last 5)\n"
                    "3. Updates strengths/weaknesses based on performance\n"
                    "4. Updates grammar progress if applicable\n"
                    "5. Sets the correct current level (A0/A1/A2/B1)\n"
                    "6. If the learner gave their name, set the Learner name field\n"
                    "7. Write EXACTLY one line 'Current level: <LEVEL>' "
                    "(e.g. 'Current level: A1') — parsers read that line.\n"
                    "IMPORTANT: For 'Total vocabulary', use ONLY the actual vocabulary list "
                    "provided below — do NOT carry over word lists from the old summary. "
                    "Count the words in the actual list.\n"
                    "Keep the same markdown format. Be concise."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## Actual Vocabulary (source of truth)\n{actual_vocab_list}\n\n"
                    f"## Current Summary\n{self.summary}\n\n"
                    f"## Session Transcript (full — nothing omitted)\n"
                    + "\n".join(self.session_log)
                ),
            },
        ]
        try:
            resp = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=summary_prompt,
                max_tokens=800,
                temperature=0,
                timeout=30,
            )
            new_summary = (resp.choices[0].message.content or "").strip()
            if new_summary:
                save_summary(new_summary, paths=self.paths)
            summary_ok = True
        except Exception:
            # The rest of the session still saves (vocabulary, transcript,
            # records), but the failure must not be silent (audit 2026 #20).
            logger.warning("Session summary update failed", exc_info=True)
            summary_ok = False

        word_count = len(self.new_words)

        # Save learning records for words that graduated
        graduated = [
            e
            for e in self.vocabulary
            if e.get("confidence", 0) >= 0.8 and not e.get("needs_review", True)
        ]
        new_graduated = [
            gw for gw in self.new_words if any(v["word"] == gw["word"] for v in graduated)
        ]
        for gw in new_graduated:
            title = f"Learned: {gw['word']}"
            content = (
                f"Word: {gw['word']}\n"
                f"English: {gw['english']}\n"
                f"Context: {gw.get('context', '')}\n"
                f"You've learned this word!"
            )
            save_learning_record(title, content, paths=self.paths)

        # Build vocab/SRS report
        report = vocabulary_report(self.vocabulary)
        cefr_parts = (
            " · ".join(f"{band}: {count}" for band, count in sorted(report["cefr"].items()))
            if report["cefr"]
            else "(none)"
        )
        stats_line = (
            f"Vocabulary: {report['total_words']} words ({cefr_parts})"
            f" | Mature: {report['mature_words']}"
            f" | Avg confidence: {report['average_confidence']:.0%}"
        )

        # Session fully saved — drop the in-progress checkpoint.
        self.clear_checkpoint()

        saved_msg = "Session saved." if summary_ok else "Session saved, but summary update failed."
        return (
            f"{saved_msg} {word_count} new words added, "
            f"{len(new_graduated)} words learned.\n{stats_line}\n"
            "See you next time!"
        )
