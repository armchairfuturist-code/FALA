# Eval Harness

Simulated-learner evaluation for the tutor prompts. An LLM plays an A0
beginner, the real `ConversationEngine` plays the tutor, and an LLM judge
grades each transcript against `rubric.md`.

## Metric

Mean rubric score across 7 criteria (1–5, higher is better), plus a
deterministic Brazilian-Portuguese marker check. See `experiments.md` for
the running experiment log.

## Run

```bash
.venv/bin/python eval/run_eval.py --tag baseline --sessions 3 --turns 8
```

- `--sessions N` — number of simulated sessions (default 3)
- `--turns N` — learner turns per session (default 8)
- `--no-judge` — generate transcripts only, skip judging

Output: `results/<tag>/session_<i>.json` and `results/<tag>/summary.json`.
Each run appends an entry to `experiments.md`.

## Model selection

Groq rate limits are per model. The harness splits roles so one exhausted
pool does not block a run:

| Env var | Role | Default |
|---|---|---|
| `FALA_MODEL` (from `.env`) | Tutor under test | `openai/gpt-oss-120b` |
| `FALA_EVAL_TUTOR_MODEL` | Override tutor model for a run | unset |
| `FALA_EVAL_AUX_MODEL` | Simulated learner | same as tutor |
| `FALA_EVAL_JUDGE_MODEL` | Rubric judge + counts | same as aux |

Example (tutor on its own pool, learner on qwen, judge on gpt-oss-20b):

```bash
FALA_EVAL_AUX_MODEL=qwen/qwen3.6-27b \
FALA_EVAL_JUDGE_MODEL=openai/gpt-oss-20b \
.venv/bin/python eval/run_eval.py --tag mychange
```

Keep every run inside one autoresearch loop on identical models. Different
models score differently; mixed models break comparability.
`summary.json` records the models used by each run.

## Autoresearch loop

1. Run `--tag baseline`. Record overall score in `experiments.md`.
2. Change one thing in `prompts/system.md` or `prompts/warmup.md`, tied to a
   finding in `docs/research/`.
3. Re-run with a new tag. Keep the change if the score rises; revert if it
   falls. Log the decision in `experiments.md`.
4. Repeat within the iteration budget.

## Cost notes

Each turn costs 2 LLM calls (learner + tutor) plus one vocab-extraction call,
plus one judge call per session. Groq's free tier handles small runs; keep
`sessions × turns` modest and raise counts only for confirm runs.
