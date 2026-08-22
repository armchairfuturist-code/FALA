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

Groq pools stayed exhausted, so the A/B pair below ran on Venice
`deepseek-v3.2` (tutor, learner, and judge identical). n=3 sessions — treat
deltas as directional.

### baseline-venice vs iter1-two-track-venice — DECISION: KEEP iteration 1

| Criterion | baseline | iter1 | Δ |
|---|---|---|---|
| method_fidelity | 3.67 | 4.33 | +0.66 |
| no_answer_reveal | 1.67 | 4.00 | **+2.33** |
| task_framing | 3.67 | 4.33 | +0.66 |
| conversational_brevity | 5.00 | 4.33 | −0.67 |
| **Overall** | **4.25** | **4.62** | **+0.37** |

Counts: learner PT production 0.33 → 2.00 turns/session; correction styles
prompt 5→7, reveal 9→6. The production step (Rule 3 Step 4) lengthens tutor
turns slightly, which explains the brevity dip — accepted trade.

## Next iterations (planned)

1. Brevity guard: cap the production-step phrasing to one short line
   (`conversational_brevity`, currently 4.33).
2. Recall-direction warm-up for known words (needs a confidence flag on
   vocab entries in `progress.py`).
3. Structured-input minimal pairs at A1+ (clitic placement first).

## baseline-venice — 2026-08-22 16:53
- Sessions: 3 × 8 learner turns
- Models: tutor `deepseek-v3.2` / aux `deepseek-v3.2`
- **Overall: 4.25**
- european_portuguese: 5.0
- level_appropriate_input: 5.0
- method_fidelity: 3.67
- no_answer_reveal: 1.67
- learner_output: 5.0
- corrective_feedback_quality: 5.0
- conversational_brevity: 5.0
- task_framing: 3.67

## iter1-two-track-venice — 2026-08-22 17:47
- Sessions: 3 × 8 learner turns
- Models: tutor `deepseek-v3.2` / aux `deepseek-v3.2`
- **Overall: 4.62**
- european_portuguese: 5.0
- level_appropriate_input: 5.0
- method_fidelity: 4.33
- no_answer_reveal: 4.0
- learner_output: 5.0
- corrective_feedback_quality: 5.0
- conversational_brevity: 4.33
- task_framing: 4.33
