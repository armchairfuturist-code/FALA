# FALA — Wayfinder Map (Daily-Driver Trust Pass)

## Destination

FALA as a tutor you'd actually run daily for 10 minutes — **trust, not features**. The shipped MVP works; this effort closes the gap between "demo passes" and "I'd let it hold 200 hours of my vocabulary history." Zero new features. The route is: real test coverage for the untested shipped code, the guardrails that exist-but-don't-guard, and the type/lint surfaces that currently lie about safety.

Ground-truth audit (2026-07-14) already cleared the QA inventory's worst fears — `save_vocabulary` empty-guard, `.env` loading, API-key error message, `/start` double-call guard, `_extract_level` A0–C2, `add_vocabulary` case-insensitive dedup, audio-failure user feedback, and the misleading `/voice` banner are all **already fixed** in current code. What remains is on this map.

## Notes

- **Domain**: European Portuguese (pt-PT) CLI tutor for English speakers, A1→B1.
- **Stack**: Python 3.10+, OpenAI SDK, Rich, Piper TTS (local), Whisper (local STT), FastAPI (web port).
- **Structure**: `fala.py` (CLI) → `conversation.py` (LLM) → `progress.py` (SRS + persistence) → `audio.py` (STT/TTS) → `web.py` (FastAPI port).
- **Skills to consult**: `grilling`, `domain-modeling`, `code-review`, `tdd`.
- **Tracker**: Local-markdown (`docs/agents/tickets/`). Claim by setting `assigned_to` in frontmatter; block via `blocked_by`; close by setting `assigned_to: closed` + adding a `## Resolution` section. Only `wayfinder:<type>` labels exist.
- **Git**: Alex Myers <alex@thearmchairfuturist.com>
- **Execution mode**: This effort, like its predecessor, overrides "plan, don't do" — tickets here ship working code (tests, fixes), not just decisions. The one exception is ticket 015 (grilling) which is a pure decision.
- **Audit baseline**: ruff ✅ passing · mypy ❌ 13 errors (all in `progress.py` `parse_vocabulary`) · 59 tests passing across config/conversation/progress/fala · `web.py` + `vocabulary_report` untested · `max_new_words_per_session` defined in config, referenced nowhere · `start_warmup` has no idempotency guard.

## Decisions so far

- [mypy pass on `progress.py`](docs/agents/tickets/017-mypy-progress-parsing.md) — 13 type errors fixed via `VocabEntry` alias. 0 mypy errors, 59 tests green.
- [enforce or remove max-new-words](docs/agents/tickets/015-enforce-or-remove-max-new-words.md) — **Enforce in code.** `conversation.py` truncates `new_words` to 5 before adding to vocab. Guardrail is real, not a prompt hint.
- [warmup idempotency guard](docs/agents/tickets/016-warmup-idempotency-guard.md) — `start_warmup` checks `_warmup_done` and returns early. 2 new tests, 61/61 green.
- [vocab-report-test-coverage](docs/agents/tickets/013-vocab-report-test-coverage.md) — 4 new tests mocking `_load_frequency_words`. 65 tests green.
- [web-py-test-coverage](docs/agents/tickets/014-web-py-test-coverage.md) — 12 FastAPI TestClient tests across all endpoints. 77 tests green.
- [record-numbering-gaps](docs/agents/tickets/019-record-numbering-gaps.md) — `save_learning_record` uses `max(nums)+1` instead of `len+1`. No collision on delete.
- [session-filename-collision](docs/agents/tickets/018-session-filename-collision.md) — **Leave as-is.** Second-resolution `%H%M%S` is sufficient; collision only loses session log, not vocab.

## Not yet specified

<!-- in-scope fog you can't ticket yet; graduates as the frontier advances -->

- **Mid-session failure modes**: LLM rate-limit or transient API error *during* a conversation (not at startup) — does `user_message`/`_call_llm` degrade gracefully, drop the turn, or crash? Need to see the live error path before ticketing. The startup path is handled (`__init__` raises helpful `ValueError`); the mid-session path is not audited.
- **Long-session memory**: `session_log` grows unbounded in memory; only last 20 lines go to the summary LLM. Fine for a 10-min daily session, but is there a session length where something breaks? No data — would need a real long session to find out.
- **Vocab file corruption recovery**: `load_vocabulary` reads YAML-ish lines; if `vocabulary.md` is hand-edited malformed, it crashes. The mypy fix (ticket 017) masked this at the type level but `_parse_vocab_entry` does bare `float(parts[1])`/`int(parts[2])` with no try/except — a single malformed line throws `ValueError` and the session is lost.

## Out of scope

- **Multi-user / cloud sync** — personal CLI tool (carried from prior map).
- **Multi-language support** — EP-only by design (carried).
- **New learning features** — spaced-review prompts, CEFR-tagged drills, gamification, progress dashboards. The destination is *trust in what exists*, not *more*.
- **Web port redesign** — `web.py` works; its only known issue (double-`/start` data loss) is already fixed via `_session_started/_session_ended` guards. Test coverage is in scope (ticket 014); a re-architecture is not.
- **Re-litigating closed decisions** — the prior map's 12 tickets are done. This map starts from their outputs.
