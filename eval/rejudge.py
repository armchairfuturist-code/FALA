"""Re-judge saved eval transcripts with the current judge model.

Use when the judge model changes between arms: re-scoring all arms with one
judge keeps comparisons fair without re-running sessions.

Usage:
    FALA_EVAL_JUDGE_MODEL=hf:Qwen/Qwen3.8-27B ... \
    .venv/bin/python eval/rejudge.py baseline-venice iter1-two-track-venice
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))

import run_eval as re_mod  # noqa: E402


def rejudge(tag: str) -> None:
    out_dir = re_mod.RESULTS_DIR / tag
    files = sorted(out_dir.glob("session_*.json"))
    if not files:
        print(f"[rejudge] {tag}: no sessions found")
        return
    all_scores, all_counts = [], []
    for path in files:
        data = json.loads(path.read_text())
        try:
            data["judge_scores"] = re_mod.judge_session(data["transcript"])
            data["judge_counts"] = re_mod.judge_counts(data["transcript"])
        except Exception as e:
            print(f"[rejudge] {tag}/{path.name}: judging failed: {e}")
            continue
        all_scores.append(data["judge_scores"])
        all_counts.append(data["judge_counts"])
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    summary_path = out_dir / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    if all_scores:
        summary["rubric"] = re_mod.aggregate(all_scores)
    styles: dict[str, int] = {}
    for c in all_counts:
        for k, v in c.get("correction_styles", {}).items():
            styles[k] = styles.get(k, 0) + int(v)
    if all_counts:
        summary["counts"] = {
            "learner_pt_production_turns_mean": round(
                sum(c["learner_pt_production_turns"] for c in all_counts) / len(all_counts), 2
            ),
            "correction_styles_total": styles,
        }
    summary["judge_model"] = re_mod.JUDGE_MODEL
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"[rejudge] {tag}: overall={summary['rubric']['overall']} "
          f"counts={summary['counts']}")


if __name__ == "__main__":
    for tag in sys.argv[1:]:
        rejudge(tag)
