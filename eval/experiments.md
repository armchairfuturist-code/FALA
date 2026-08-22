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

## smoke-syn — 2026-08-22 18:05
- Sessions: 1 × 1 learner turns
- Models: tutor `deepseek-v3.2` / aux `hf:Qwen/Qwen3.8-27B`
- **Overall: 4.75**
- european_portuguese: 5.0
- level_appropriate_input: 4.0
- method_fidelity: 5.0
- no_answer_reveal: 5.0
- learner_output: 5.0
- corrective_feedback_quality: 5.0
- conversational_brevity: 4.0
- task_framing: 5.0

## iter2-brevity — 2026-08-22 18:35
- Sessions: 3 × 8 learner turns
- Models: tutor `deepseek-v3.2` / aux `hf:Qwen/Qwen3.8-27B`
- **Overall: 3.62**
- european_portuguese: 5.0
- level_appropriate_input: 4.0
- method_fidelity: 3.0
- no_answer_reveal: 3.0
- learner_output: 4.0
- corrective_feedback_quality: 4.0
- conversational_brevity: 3.0
- task_framing: 3.0

## Consistent-judge re-score (2026-08-22, judge `deepseek-v3.2` on all arms)

The Synthetic `hf:Qwen/Qwen3.8-27B` judge produced malformed JSON on most
calls (truncated reasoning) — its numbers above are unreliable. All saved
transcripts were re-scored with the same Venice judge via `eval/rejudge.py`.
This is the comparison set of record (n=3 per arm, same tutor/learner/judge):

| Criterion | baseline | iter1 two-track | iter2 +brevity guard |
|---|---|---|---|
| method_fidelity | 3.67 | **4.67** | 3.67 |
| no_answer_reveal | 3.00 | **3.33** | 2.33 |
| corrective_feedback_quality | 5.00 | 4.67 | 5.00 |
| conversational_brevity | 5.00 | 5.00 | 4.33 |
| task_framing | 3.00 | **3.67** | 3.00 |
| **Overall** | 4.33 | **4.54** | 4.17 |

Counts: learner PT production 1.0 → 2.0 → 0.67 turns/session; reveals 9 → 10 → 3.

### Decisions
- **iter1 (two-track + production step + task framing): KEEP.** Beats baseline
  on the criteria it targets; the feared brevity cost did not appear.
- **iter2 (brevity guard): REVERT.** Overall dropped to 4.17 and brevity
  itself scored lower (4.33). No benefit, real cost. Guard line removed from
  `prompts/system.md`.

### Known noise
n=3 per arm; judge variance between runs is visible (baseline scored 4.25
then 4.33 on identical transcripts). Treat deltas < 0.3 as directional only.
Confirm runs with more sessions before big calls.

## Iteration 3 (implemented, NOT yet evaluated)
- `progress.py`: `get_review_words_with_direction()` — recall (EN→PT) at
  confidence ≥ 0.5, recognition (PT→EN) below. Wired into
  `get_vocab_for_prompt`, so the warm-up prompt now tags each review word.
- `prompts/warmup.md`: recall/recognition instructions for the tutor.
- NOT measured by the current harness: simulated A0 first sessions have no
  vocabulary, so the review path never triggers. Measuring iter3 needs
  multi-session simulation (harness extension) — next harness task.
