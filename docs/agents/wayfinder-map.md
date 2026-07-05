# FALA — Wayfinder Map

## Destination

A conversational European Portuguese (pt-PT) CLI tutor you can run daily — reliable, pleasant to use, and effective for going from A1 to B1. All 6 infrastructure/SRS tickets are closed; remaining work sharpens the tutor itself.

## Notes

- **Domain**: Language-learning CLI tool (European Portuguese tutor for English speakers)
- **Stack**: Python 3.10+, OpenAI SDK, Rich (CLI), Whisper (local STT), OpenAI TTS
- **Structure**: `fala.py` (entrypoint) → `conversation.py` (LLM orchestration) → `progress.py` (SRS + persistence) → `audio.py` (STT/TTS pipeline)
- **Skills to consult**: `domain-modeling`, `grilling`, `implement`, `prototype`, `code-review`
- **Standing**: Bootstrap phase complete (6 closed tickets). Next tickets come from graduating "Not yet specified" items.
- **Tracker**: Local-markdown (`docs/agents/tickets/`). Tickets are claimed by setting the `assigned_to` field in frontmatter. No labels beyond `wayfinder:<type>`.
- **Git**: Alex Myers <alex@thearmchairfuturist.com>

## Decisions so far

<!-- one line per closed ticket: name (linked) + gist of the answer -->

- [Clone and verify](tickets/001-clone-and-verify.md) — Repo cloned locally, `.venv` + deps installed, CLI verified to start; `.venv/` added to `.gitignore`; Arch requires virtualenv for pip
- [Bootstrap agent infrastructure](tickets/002-bootstrap-agent-infrastructure.md) — AGENTS.md, CONTEXT.md, issue-tracker.md, triage-labels.md, ADR template created and committed on `chore/bootstrap` branch
- [Setup development environment](tickets/003-setup-development-environment.md) — pyproject.toml, ruff/pytest/mypy config, .env.example, scripts/bootstrap.sh + lint.sh, all lint passes clean
- [Architecture documentation](tickets/004-architecture-documentation.md) — docs/architecture.md with module graph, data flow, SRS algorithm, prompt templates, audio pipeline, 8 design decisions, 8 latent issues documented; README claims checked
- [Testing and CI](tickets/005-testing-and-ci.md) — 52 tests (config, progress, conversation, fala smoke test), .github/workflows/ci.yml, fixed load_vocabulary parsing bug
- [Fix SRS feedback loop](tickets/006-fix-srs-feedback-loop.md) — `update_vocab_after_review()` and `save_learning_record()` wired into `conversation.py`; extraction prompt returns `{"new_words": [...], "assessments": [...]}`; 4 integration tests added; 56 tests total

## Not yet specified

- **TTS/STT quality** — current OpenAI TTS voices are English-optimised; pt-PT voices are scarce. Worth investigating alternatives (ElevenLabs, local models) when the audio module gets attention.
- **Conversation UX** — the warmup→free-conversation flow works, but session quality depends entirely on the LLM prompt. Long-term improvements likely need prompt versioning and A/B evaluation.
- **Evaluation** — how to measure learning progress objectively? LLM summary is subjective. A structured assessment mode is a candidate feature.
- **Web/mobile port** — a known direction but too vague to ticket; might be worth a prototype to assess feasibility.

## Out of scope

- **Multi-user / cloud sync** — this is a personal CLI tool.
- **Multi-language support** — EP-only by design. Adding other languages would be a separate effort.
