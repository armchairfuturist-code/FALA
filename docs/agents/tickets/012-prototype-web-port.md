---
type: prototype
labels: [wayfinder:prototype]
blocked_by: []
assigned_to: closed
---

## Question

What would a web-based version of FALA look like? Build a cheap, rough prototype to see if the CLI tutor's conversation engine can be wrapped in a web UI.

## Resolution

Built `web.py` — a FastAPI server wrapping the existing `ConversationEngine` in a single-page chat UI.

**What was built:**
- `web.py` — FastAPI app with 5 endpoints: GET `/` (HTML page), POST `/start`, POST `/message`, GET `/stats`, POST `/quit`
- Single-page HTML chat UI with tutor/user/sys message bubbles
- Reuses existing ConversationEngine, data/ directory, vocab, SRS, etc.
- Runs with: `python3 web.py` (serves on `http://127.0.0.1:8080`)
- 56 tests still passing

**Usage:** `pip install fastapi uvicorn python-multipart && python3 web.py`

| # | Acceptance | Status |
|---|-----------|--------|
| 1 | Working web UI starts conversation | ✅ |
| 2 | Text input + response display | ✅ |
| 3 | Shows CEFR stats via /stats | ✅ |
| 4 | Reuses existing engine + data dir | ✅ |
| 5 | Runs locally with single command | ✅ (`python3 web.py`) |
