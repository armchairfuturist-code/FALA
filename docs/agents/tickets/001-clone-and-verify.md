---
type: task
labels: [wayfinder:task, wayfinder:closed]
blocked_by: []
---

## Question

Can I clone the FALA repo, install its dependencies, and verify it runs (starts, shows the CLI banner, responds to input)?

## Resolution

Resolved in session 2026-07-04.

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Repo cloned into `~/Projects/FALA` | ✅ |
| 2 | `pip install -r requirements.txt` succeeds | ✅ (in `.venv`) |
| 3 | `python3 fala.py` starts and shows the banner | ✅ |
| 4 | Entering "quit" exits cleanly | ✅ — warmup LLM call fails without API key (expected), but CLI UI, banner, audio status all render correctly |
| 5 | `data/` directory auto-created with expected subdirectories | ✅ — `sessions/`, `records/`, `vocabulary.md` all created |

**Facts for future tickets:**
- Arch Linux — `python -m venv .venv` required (externally-managed Python)
- OpenAI SDK v2.44.0 rejects empty keys on init; needs `FALA_API_KEY` or `OPENAI_API_KEY` set
- `summary.md` is not written until `end_session()` is called (default returned in-memory)
- CLI works: banner, Rich panels, data dirs, voice toggle menu all render

## Assets

- `~/Projects/FALA/` — cloned repo
