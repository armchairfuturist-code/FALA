---
type: task
labels: [wayfinder:task]
blocked_by: []
assigned_to: closed
---

## Question

`conversation.py:235` names session files `f"{strftime('%Y-%m-%d-%H%M%S')}.md"` — **second-resolution**. The QA inventory's B11 ("minute collision") is already moot (seconds, not minutes), but two sessions starting in the *same second* still collide — a real edge if a user quits and immediately restarts, or a script drives the CLI. Is this worth hardening? The fix is cheap: append a counter or a short uuid on collision. But the *decision* is whether second-resolution is good enough for a personal tool (it almost certainly is) or whether we want true uniqueness.

## Acceptance

- [x] Decision: leave as-is (second-resolution is sufficient for a personal CLI).
- [x] No code change.

## Resolution

The QA inventory claimed "minute collision" (B11) but the code actually uses seconds (`%H%M%S`). Two sessions starting in the same second is negligible for a personal CLI — and even if it happens, only the session log is overwritten (cosmetic), not the vocabulary data (saved separately via `save_vocabulary`). Accepted.
