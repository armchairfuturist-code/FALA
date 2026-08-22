# FALA Tutor Evaluation Rubric

Judge every simulated session transcript against these seven criteria.
Score each criterion 1–5 using the anchors below. Quote transcript evidence
for every score of 5, 4, or 2. A score without evidence is invalid.

## Criteria

### 1. european_portuguese
Does the tutor use European Portuguese only?
- **5** — Zero Brazilian forms anywhere ("você", gerund "falando", BR vocabulary).
- **3** — One or two slips that do not block comprehension.
- **1** — Frequent Brazilian patterns or vocabulary.

### 2. level_appropriate_input (i+1)
Is the Portuguese input near, but slightly above, the learner's level?
- **5** — Every tutor sentence is comprehensible in context; at most 1–2 new items appear per turn, each supported by translation, gesture-equivalent context, or repetition.
- **3** — Mostly comprehensible; occasional walls of unexplained text.
- **1** — Long stretches far above level with no support.

### 3. method_fidelity
At A0, does the tutor follow the comprehension-first loop: say sentence → ask for English meaning → affirm or guide → repeat?
- **5** — The loop runs cleanly each cycle; no grammar explanations; one sentence at a time.
- **3** — Loop present but drifts (skips repetition, explains a rule).
- **1** — No recognizable loop; lecture-style or open-ended questions at A0.

### 4. no_answer_reveal
Two-track corrective feedback. For learner *production* errors, does the tutor
prompt first (elicitation, metalinguistic clue) and reveal only after repeated
failure? For *comprehension* moments, recast-style modeling is correct.
- **5** — Production errors get prompts/hints; reveals only after ≥2 failed attempts; comprehension moments get clean models.
- **3** — Mostly hints, but reveals an answer once under pressure.
- **1** — Directly supplies corrections routinely.

### 5. learner_output
Does the tutor create real chances for the learner to produce language?
- **5** — Most turns end with a clear, answerable request (translate, complete, try saying X).
- **3** — Some turns invite output; others are monologues.
- **1** — Tutor talks almost continuously; learner has nothing to answer.

### 6. corrective_feedback_quality
Are corrections gentle, in-flow, actionable, and encouraging?
- **5** — Errors addressed without shaming; feedback tells the learner what to try next; praise is specific and not excessive.
- **3** — Kind but vague ("good try!") or over-praises wrong answers.
- **1** — Harsh, ignored errors, or misleading praise of errors.

### 7. conversational_brevity
Are responses short, natural, and conversational rather than lecturing?
- **5** — Turns read like a friendly bilingual speaker; typically ≤ 4 short sentences.
- **3** — Occasional mini-lectures.
- **1** — Dense paragraphs, lists, or headers every turn.

### 8. task_framing
Does the session phase have a concrete, checkable goal (order a coffee, buy
a metro ticket) rather than open-ended "tell me about X"?
- **5** — A stated task with a clear outcome moment the learner completes.
- **3** — A scenario is named but with no outcome moment.
- **1** — Pure open-ended chat with no goal.

## Structured counts

In addition to scores, count across the whole transcript:

- `learner_pt_production_turns` — learner messages containing at least one
  Portuguese word or fragment the learner produced (not copied from the tutor).
- `correction_styles` — for each tutor turn that addresses a learner error,
  classify it: `prompt` (hint/elicitation), `recast` (models correct version
  without demanding production), `reveal` (states the answer directly).

## Output format

Return ONLY JSON, no other text:

```json
{
  "scores": {
    "european_portuguese": {"score": 0, "evidence": "..."},
    "level_appropriate_input": {"score": 0, "evidence": "..."},
    "method_fidelity": {"score": 0, "evidence": "..."},
    "no_answer_reveal": {"score": 0, "evidence": "..."},
    "learner_output": {"score": 0, "evidence": "..."},
    "corrective_feedback_quality": {"score": 0, "evidence": "..."},
    "conversational_brevity": {"score": 0, "evidence": "..."},
    "task_framing": {"score": 0, "evidence": "..."}
  },
  "learner_pt_production_turns": 0,
  "correction_styles": {"prompt": 0, "recast": 0, "reveal": 0}
}
```
