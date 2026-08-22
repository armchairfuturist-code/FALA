"""Simulated-learner evaluation harness for FALA tutor prompts.

Runs N simulated sessions: an LLM plays an A0 English-speaking learner, the
real ConversationEngine plays the tutor, then an LLM judge grades each
transcript against eval/rubric.md. Results land in eval/results/<tag>/.

Usage:
    .venv/bin/python eval/run_eval.py --tag baseline --sessions 3 --turns 8
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
REPO_DIR = EVAL_DIR.parent
sys.path.insert(0, str(REPO_DIR))

# Must be set before importing config (config reads env at import time).
# load_dotenv() does not override variables already in the environment.
os.environ.setdefault("FALA_MODEL", "openai/gpt-oss-120b")
os.environ.setdefault("FALA_TTS", "none")
# FALA_EVAL_TUTOR_MODEL overrides the tutor model for eval runs. Useful when
# the default tutor model's provider quota pool is exhausted; all runs in an
# autoresearch loop must use the same tutor model for comparability.
if os.environ.get("FALA_EVAL_TUTOR_MODEL"):
    os.environ["FALA_MODEL"] = os.environ["FALA_EVAL_TUTOR_MODEL"]

from openai import OpenAI, RateLimitError  # noqa: E402

import config  # noqa: E402
from conversation import ConversationEngine  # noqa: E402

LLM_MODEL = os.environ["FALA_MODEL"]
# Learner + judge can run on a different PROVIDER than the tutor (separate
# base URL and key) so eval traffic does not share the tutor's quota pool.
AUX_MODEL = os.environ.get("FALA_EVAL_AUX_MODEL", LLM_MODEL)
AUX_BASE_URL = os.environ.get("FALA_EVAL_AUX_BASE_URL", config.LLM_BASE_URL)
AUX_API_KEY = os.environ.get("FALA_EVAL_AUX_API_KEY", config.LLM_API_KEY)
JUDGE_MODEL = os.environ.get("FALA_EVAL_JUDGE_MODEL", AUX_MODEL)
JUDGE_USES_AUX_CLIENT = os.environ.get("FALA_EVAL_JUDGE_BASE_URL", AUX_BASE_URL) == AUX_BASE_URL
aux_client = OpenAI(base_url=AUX_BASE_URL, api_key=AUX_API_KEY)
judge_client = (
    aux_client
    if JUDGE_USES_AUX_CLIENT
    else OpenAI(
        base_url=os.environ["FALA_EVAL_JUDGE_BASE_URL"],
        api_key=os.environ.get("FALA_EVAL_JUDGE_API_KEY", AUX_API_KEY),
    )
)

# Cap per-message length in judge inputs so one request stays under small
# provider token-per-minute limits.
JUDGE_MSG_CHAR_CAP = int(os.environ.get("FALA_EVAL_JUDGE_MSG_CAP", "1500"))


def _clip(text: str) -> str:
    return text if len(text) <= JUDGE_MSG_CHAR_CAP else text[:JUDGE_MSG_CHAR_CAP] + " …[clipped]"
RESULTS_DIR = EVAL_DIR / "results"
EXPERIMENTS_LOG = EVAL_DIR / "experiments.md"


THINK_RE = re.compile(r"<think>.*?(</think>|$)", re.DOTALL)


def strip_think(text: str) -> str:
    """Remove leaked reasoning traces some models emit inside content."""
    return THINK_RE.sub("", text).strip()


def llm_call(messages, max_tokens=1000, temperature=0.7, model: str | None = None, client=None):
    resp = (client or aux_client).chat.completions.create(
        model=model or AUX_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return strip_think(resp.choices[0].message.content or "")


# Deterministic Brazilian-Portuguese markers (from prompts/system.md table).
BR_MARKERS = [
    r"\bvoc[êe]\b",
    r"\bestou falando\b",
    r"\bestou comendo\b",
    r"\bônibus\b",
    r"\btrem\b",
    r"\btchau\b",
    r"\bmenina\b",
    r"\bseu nome\b",
    r"\bgarçom\b",
]
PT_GERUND_RE = re.compile(r"\b\w+(ando|endo)\b")

LEARNER_SYSTEM = """You are simulating a real adult learner: an English speaker \
on day one of European Portuguese (CEFR A0). You know essentially no \
Portuguese yet.

Rules:
- Stay in character. You are friendly but a complete beginner.
- When the tutor says a Portuguese sentence and asks what it means, give your \
best English translation guess. You are often wrong or half-right — guess from \
context like a real beginner.
- Make mistakes: in roughly one third of your answers, mistranslate at least \
one word or give a clearly wrong guess. Vary which words you get wrong.
- When asked to try Portuguese, attempt it with plausible beginner mistakes \
(missing articles, English word order, no accents).
- Never write more than 2 short sentences. Never ask meta questions about the \
simulation.
- Output ONLY your reply as the learner. No role labels, no quotes, no stage \
directions.
"""


def with_backoff(fn, *args, **kwargs):
    """Call fn, retrying provider rate limits with exponential backoff."""
    delay = 90
    for attempt in range(4):
        try:
            return fn(*args, **kwargs)
        except RateLimitError:
            if attempt == 3:
                raise
            print(f"[run_eval] rate limited — sleeping {delay}s", flush=True)
            time.sleep(delay)
            delay *= 2


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def llm_call_json(
    messages, max_tokens=2500, retries: int = 2, model: str | None = None, client=None
) -> dict:
    """llm_call + JSON parsing, retrying once per failure with a repair prompt."""
    msgs = list(messages)
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        text = with_backoff(
            llm_call, msgs, max_tokens=max_tokens, temperature=0, model=model, client=client
        )
        try:
            return parse_json(text)
        except json.JSONDecodeError as err:
            last_err = err
            msgs = msgs + [
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": (
                        "That was not valid JSON. Return exactly the same "
                        "content as one strictly valid JSON object. Escape any "
                        'double quotation marks inside string values as \\" . '
                        "Output only the JSON."
                    ),
                },
            ]
    raise last_err  # type: ignore[misc]


def run_session(session_index: int, turns: int) -> dict:
    user_id = f"eval_{os.getpid()}_{session_index}"
    engine = ConversationEngine(user_id=user_id)
    transcript = [{"role": "tutor", "content": strip_think(with_backoff(engine.start_warmup))}]
    for _ in range(turns):
        learner_messages = [
            {"role": "system", "content": LEARNER_SYSTEM},
            {
                "role": "user",
                "content": "Tutor's last message:\n" + transcript[-1]["content"]
                + "\n\nReply as the learner.",
            },
        ]
        learner_reply = ""
        for attempt_tokens in (700, 1200):
            learner_reply = strip_think(
                with_backoff(
                    llm_call, learner_messages, max_tokens=attempt_tokens, temperature=0.8
                )
            )
            if learner_reply:
                break
        if not learner_reply:
            learner_reply = "(says nothing)"
        transcript.append({"role": "learner", "content": learner_reply})
        tutor_reply = strip_think(with_backoff(engine.user_message, learner_reply))
        transcript.append({"role": "tutor", "content": tutor_reply})
    engine.end_session()
    shutil.rmtree(config.paths_for_user(user_id).data_dir, ignore_errors=True)
    return {"session": session_index, "turns": turns, "transcript": transcript}


def deterministic_checks(transcript: list[dict]) -> dict:
    tutor_text = "\n".join(
        m["content"] for m in transcript if m["role"] == "tutor"
    )
    br_hits = [pat for pat in BR_MARKERS if re.search(pat, tutor_text, re.IGNORECASE)]
    gerund_hits = sorted(set(PT_GERUND_RE.findall(tutor_text)))
    return {
        "brazilian_markers": br_hits,
        "possible_gerund_endings": gerund_hits,
    }


def _transcript_text(transcript: list[dict]) -> str:
    return "\n\n".join(
        f"{'TUTOR' if m['role'] == 'tutor' else 'LEARNER'}: {_clip(m['content'])}"
        for m in transcript
    )


def judge_session(transcript: list[dict]) -> dict:
    rubric = (EVAL_DIR / "rubric.md").read_text()
    judge_messages = [
        {
            "role": "system",
            "content": (
                "You are a strict applied-linguistics evaluator. Grade the "
                "TUTOR (not the learner) in the transcript below against the "
                "rubric. The learner is a simulated A0 beginner; their errors "
                "are expected and must not lower tutor scores.\n\n" + rubric
            ),
        },
        {"role": "user", "content": _transcript_text(transcript)},
    ]
    data = llm_call_json(judge_messages, max_tokens=6000, model=JUDGE_MODEL, client=judge_client)
    return data["scores"]


def judge_counts(transcript: list[dict]) -> dict:
    """Structured counts from a second, cheap judge pass."""
    rubric = (EVAL_DIR / "rubric.md").read_text()
    section = rubric[rubric.index("## Structured counts") : rubric.index("## Output format")]
    try:
        counts = llm_call_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You are an applied-linguistics annotator. Apply ONLY the "
                        "following section to the transcript. Return ONLY JSON.\n\n"
                        + section
                    ),
                },
                {"role": "user", "content": _transcript_text(transcript)},
            ],
            max_tokens=3000,
            model=JUDGE_MODEL,
            client=judge_client,
        )
        styles = counts.get("correction_styles", {})
        if isinstance(styles, list):
            normalized = {"prompt": 0, "recast": 0, "reveal": 0}
            for item in styles:
                key = str(item).lower().strip('"{} ')
                for k in normalized:
                    if k in key:
                        normalized[k] += 1
            styles = normalized
        return {
            "learner_pt_production_turns": int(counts.get("learner_pt_production_turns", 0)),
            "correction_styles": styles,
        }
    except Exception:
        return {"learner_pt_production_turns": -1, "correction_styles": {}}


def aggregate(all_scores: list[dict]) -> dict:
    per_criterion: dict[str, list[float]] = {}
    for scores in all_scores:
        for name, entry in scores.items():
            per_criterion.setdefault(name, []).append(entry["score"])
    means = {k: round(sum(v) / len(v), 2) for k, v in per_criterion.items()}
    overall = round(sum(means.values()) / len(means), 2) if means else 0.0
    return {"per_criterion": means, "overall": overall}


def append_experiment_log(
    tag: str, summary: dict, sessions: int, turns: int, tutor: str = "", aux: str = ""
):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not EXPERIMENTS_LOG.exists():
        EXPERIMENTS_LOG.write_text(
            "# FALA Autoresearch Experiment Log\n\n"
            "One entry per eval run. Metric: mean rubric score (1–5, higher "
            "is better). Rubric: `eval/rubric.md`.\n"
        )
    lines = [
        f"\n## {tag} — {stamp}",
        f"- Sessions: {sessions} × {turns} learner turns",
    ]
    if tutor or aux:
        lines.append(f"- Models: tutor `{tutor}` / aux `{aux}`")
    lines.append(f"- **Overall: {summary['overall']}**")
    for name, mean in summary["per_criterion"].items():
        lines.append(f"- {name}: {mean}")
    with EXPERIMENTS_LOG.open("a") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True, help="Label for this run, e.g. baseline")
    ap.add_argument("--sessions", type=int, default=3)
    ap.add_argument("--turns", type=int, default=8)
    ap.add_argument("--no-judge", action="store_true", help="Skip LLM judging")
    args = ap.parse_args()

    out_dir = RESULTS_DIR / args.tag
    out_dir.mkdir(parents=True, exist_ok=True)

    transcripts, all_scores, all_checks = [], [], []
    all_counts = []
    for i in range(args.sessions):
        print(f"[run_eval] session {i + 1}/{args.sessions} …", flush=True)
        result = run_session(i, args.turns)
        result["deterministic"] = deterministic_checks(result["transcript"])
        # Persist the transcript before judging so a judge crash loses nothing.
        (out_dir / f"session_{i}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2)
        )
        if not args.no_judge:
            try:
                result["judge_scores"] = judge_session(result["transcript"])
                result["judge_counts"] = judge_counts(result["transcript"])
            except Exception as e:
                print(f"[run_eval] judging failed for session {i}: {e}", flush=True)
            else:
                all_counts.append(result["judge_counts"])
                all_scores.append(result["judge_scores"])
        all_checks.append(result["deterministic"])
        transcripts.append(result)
        (out_dir / f"session_{i}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2)
        )

    summary = {
        "tag": args.tag,
        "sessions": args.sessions,
        "turns": args.turns,
        "tutor_model": LLM_MODEL,
        "aux_model": AUX_MODEL,
    }
    if all_scores:
        summary["rubric"] = aggregate(all_scores)
    if all_counts:
        styles: dict[str, int] = {}
        for c in all_counts:
            for k, v in c.get("correction_styles", {}).items():
                styles[k] = styles.get(k, 0) + int(v)
        summary["counts"] = {
            "learner_pt_production_turns_mean": round(
                sum(c["learner_pt_production_turns"] for c in all_counts) / len(all_counts), 2
            ),
            "correction_styles_total": styles,
        }
    summary["deterministic"] = {
        "runs_with_brazilian_markers": sum(1 for c in all_checks if c["brazilian_markers"])
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    if all_scores:
        append_experiment_log(
            args.tag,
            summary["rubric"],
            args.sessions,
            args.turns,
            tutor=LLM_MODEL,
            aux=AUX_MODEL,
        )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
