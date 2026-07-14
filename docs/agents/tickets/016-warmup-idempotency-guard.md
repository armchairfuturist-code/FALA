---
type: task
labels: [wayfinder:task]
blocked_by: []
assigned_to: closed
---

## Question

`ConversationEngine.start_warmup()` has **no idempotency guard** — calling it twice appends a second warmup prompt to `self.messages`, double-charging the LLM context and confusing the tutor. The CLI never calls it twice, but `web.py`'s `/start` is guarded separately by `_session_started`; the engine itself is not defensive. A direct caller (a future test, a different frontend) can trigger this. Add a `_warmup_done` guard at the top of `start_warmup` (the flag already exists and is set at the end — just check it).

## Resolution

Idempotency guard added: `start_warmup` checks `self._warmup_done` at the top and returns early with `"[Warm-up already completed this session]"`. Two new tests verify the second call doesn't add messages or call the LLM. 61 tests green, mypy 0, ruff clean.

## Acceptance

- [x] `start_warmup` returns early with a no-op marker if `_warmup_done` is already True.
- [x] Test: second call does not append to `engine.messages`.
- [x] Test: second call does not invoke `_call_llm` (call counter assertion).
- [x] Existing `TestStartWarmup` tests still pass.
- [x] `pytest tests/ -v` green; no ruff/mypy regressions.
