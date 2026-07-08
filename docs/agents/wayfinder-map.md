# FALA — Wayfinder Map

## Destination

A conversational European Portuguese (pt-PT) CLI tutor you can run daily — reliable, pleasant to use, and effective for going from A1 to B1. All 6 infrastructure/SRS tickets are closed; remaining work sharpens the tutor itself.

## Notes

- **Domain**: Language-learning CLI tool (European Portuguese tutor for English speakers)
- **Stack**: Python 3.10+, OpenAI SDK, Rich (CLI), Whisper (local STT), OpenAI TTS
- **Structure**: `fala.py` (entrypoint) → `conversation.py` (LLM orchestration) → `progress.py` (SRS + persistence) → `audio.py` (STT/TTS pipeline)
- **Skills to consult**: `domain-modeling`, `grilling`, `implement`, `prototype`, `code-review`
- **Standing**: 11 closed, 1 open (ticket #012). Tickets graduate from Not yet specified.
- **Execution mode**: This effort overrides wayfinder's "plan, don't do" default — tickets here produce working code, not just decisions. The destination is a working tool, so each ticket either sharpens a decision or ships working features toward it.
- **Tracker**: Local-markdown (`docs/agents/tickets/`). Tickets are claimed by setting the `assigned_to` field in frontmatter. Labels: `wayfinder:<type>` only.
- **Git**: Alex Myers <alex@thearmchairfuturist.com>

## Decisions so far

<!-- one line per closed ticket: name (linked) + gist of the answer -->

- [Clone and verify](tickets/001-clone-and-verify.md) — Repo cloned locally, `.venv` + deps installed, CLI verified to start; `.venv/` added to `.gitignore`; Arch requires virtualenv for pip
- [Bootstrap agent infrastructure](tickets/002-bootstrap-agent-infrastructure.md) — AGENTS.md, CONTEXT.md, issue-tracker.md, triage-labels.md, ADR template created and committed on `chore/bootstrap` branch
- [Setup development environment](tickets/003-setup-development-environment.md) — pyproject.toml, ruff/pytest/mypy config, .env.example, scripts/bootstrap.sh + lint.sh, all lint passes clean
- [Architecture documentation](tickets/004-architecture-documentation.md) — docs/architecture.md with module graph, data flow, SRS algorithm, prompt templates, audio pipeline, 8 design decisions, 8 latent issues documented; README claims checked
- [Testing and CI](tickets/005-testing-and-ci.md) — 52 tests (config, progress, conversation, fala smoke test), .github/workflows/ci.yml, fixed load_vocabulary parsing bug
- [Fix SRS feedback loop](tickets/006-fix-srs-feedback-loop.md) — `update_vocab_after_review()` and `save_learning_record()` wired into `conversation.py`; extraction prompt returns `{"new_words": [...], "assessments": [...]}`; 4 integration tests added; 56 tests total
- [Research TTS/STT quality for pt-PT](tickets/007-research-tts-stt-ptpt.md) — 6 TTS and 7 STT options evaluated; Piper TTS (tugão) is best local neural voice; Google STT has explicit pt-PT locale; recommendation is multi-tier quality progression
- [Add Piper TTS](tickets/008-add-piper-tts.md) — Piper TTS engine added to `audio.py`; `FALA_TTS=piper` env var switches to local tugão pt-PT voice; auto-downloads from HuggingFace; banner shows active provider
- [Review conversation prompts](tickets/009-review-conversation-prompts.md) — Researched Praktika, Talkpal, and academic sources; rewrote `system.md` and `warmup.md` with gentle in-flow correction, no-direct-answer guardrails, conditional pronunciation feedback, and natural name introduction
- [Research evaluation/progress measurement](tickets/010-research-evaluation.md) — Surveyed Duolingo, Anki, LingQ, CEFR vocab; recommended CEFR breakdown + SRS health report + `/stats` command (ticket #011 implements)
- [CEFR vocabulary breakdown](tickets/011-cefr-vocab-breakdown.md) — Implemented `vocabulary_report()` via FrequencyWords pt_50k.txt; `/stats` command mid-session; CEFR breakdown + SRS stats shown at session end

## Not yet specified

*(none)*

## Out of scope

- **Multi-user / cloud sync** — this is a personal CLI tool.
- **Multi-language support** — EP-only by design. Adding other languages would be a separate effort.
