# FALA Autoresearch Experiment Log

One entry per eval run. Metric: mean rubric score (1–5, higher is better).
Rubric: `eval/rubric.md`. Raw transcripts live in `eval/results/` (not committed).

## History (annotated)

### smoke — 2026-08-22 12:20 — 7-criterion rubric
1 session × 2 turns, tutor `openai/gpt-oss-120b`. Pipeline validation only.
Overall 5.0 — happy path, learner never erred; not comparable.

### pipeline-check — 2026-08-22 12:33 — 7-criterion rubric
3 × 8 turns, tutor `openai/gpt-oss-120b`. Overall **4.9**.
Learner had no error-injection yet, so correction paths got little pressure.
Kept as reference only.

### baseline-degraded-qwen — 2026-08-22 13:56 — INVALID, do not compare
Tutor/aux `qwen/qwen3.6-27b`. Overall 2.33 (all criteria identical — judge
degenerate). Cause: qwen leaks raw `<think>` traces into content; tutor turns
became meta-commentary. Harness now strips `<think>` blocks defensively.
Do not use this entry for comparisons.

### baseline-v1 — 2026-08-22 14:10 — PROVISIONAL BASELINE
Models: tutor `openai/gpt-oss-20b`, aux `openai/gpt-oss-20b`, judge
`openai/gpt-oss-20b`. 3 sessions × 8 turns.

| Criterion | Score |
|---|---|
| european_portuguese | 5.00 |
| level_appropriate_input | 3.67 |
| method_fidelity | **1.67** |
| no_answer_reveal | 3.00 |
| learner_output | **2.33** |
| corrective_feedback_quality | 3.67 |
| conversational_brevity | 4.33 |
| task_framing | 3.67 |
| **Overall** | **3.42** |

Counts: learner PT-production ≈ 1.7 turns/session; correction styles:
prompt 1, recast 0, reveal 1.

Known noise: session 0 contains two empty turns (learner hit the old
200-token cap before the fix); deterministic check caught "garçom"
(Brazilian) that the judge scored as clean pt-PT.

## Next iterations (planned)

Each change below comes from `docs/research/sla-methods.md` and is tested
against the rubric:

1. Two-track corrective feedback rule (prompts first, reveal after two
   failures) → targets `no_answer_reveal`, `corrective_feedback_quality`.
2. Require one learner-produced PT utterance per session from session 1
   → targets `learner_output`.
3. Task-framed free conversation (checkable outcome) → targets `task_framing`.

Re-run after Groq's daily token reset; keep all models identical to
baseline-v1 (`openai/gpt-oss-20b`) for comparability.
