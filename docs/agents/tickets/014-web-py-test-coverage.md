---
type: task
labels: [wayfinder:task]
blocked_by: []
assigned_to: closed
---

## Question

`web.py` is 200 lines of FastAPI wrapping `ConversationEngine`, shipped as ticket 012's prototype — and has **no test file**. The endpoints (`/start`, `/message`, `/stats`, `/quit`) plus the `_session_started/_session_ended` state machine that *fixed* the double-`/start` data-loss bug (B5) are verified only by hand. The fix for the worst known web bug has no regression test. Add a `tests/test_web.py` using FastAPI's `TestClient`.

## Acceptance

- [x] `tests/test_web.py` exists, uses `fastapi.testclient.TestClient`.
- [x] Test: `POST /start` returns warmup message + status report.
- [x] Test: `POST /start` twice in a row → second returns "Session already started" (B5 regression guard).
- [x] Test: `POST /message` before `/start` → returns "No active session" error (B9 regression guard).
- [x] Test: `POST /message` with "quit" ends session; subsequent `/message` is rejected.
- [x] Test: `GET /stats` returns a stats dict/string.
- [x] All mocked — no real LLM calls (patch `ConversationEngine`).
- [x] `pytest tests/ -v` green; no ruff/mypy regressions.

## Resolution

12 tests across 5 endpoint classes (index, start, message, stats, quit) using FastAPI TestClient + MagicMock. All B5/B9 regression guards tested. 77 tests green, ruff clean.
