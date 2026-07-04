# FALA — Wayfinder Map

## Tickets

The frontier is at `docs/agents/tickets/` — query all `.md` files where `wayfinder:claimed` is absent and `blocked_by` entries are all closed (or empty). Current ticket set:

| # | Name | Type | Blocked by |
|---|------|------|------------|
| 1 | Clone and verify | task | — (closed) |
| 2 | Bootstrap agent infrastructure | task | — (closed) |
| 3 | Setup development environment | task | — (closed) |
| 4 | Architecture documentation | research | — (closed) |
| 5 | Testing and CI | task | — (closed) |

## Notes

- **Domain**: Language-learning CLI tool (European Portuguese tutor for English speakers)
- **Stack**: Python 3.10+, OpenAI SDK, Rich (CLI), Whisper (local STT), OpenAI TTS
- **Structure**: `fala.py` (entrypoint) → `conversation.py` (LLM orchestration) → `progress.py` (SRS + persistence) → `audio.py` (STT/TTS pipeline)
- **Skills to consult**: `domain-modeling`, `grilling`, `implement`, `prototype`, `code-review`
- **Standing**: Multi-session effort. Bootstrap infrastructure first, then develop features. Resolve tickets in frontier order.
- **Tracker**: Local-markdown (`docs/agents/tickets/`). Each ticket is a `.md` file.
- **Git**: Alex Myers <alex@thearmchairfuturist.com>

## Decisions so far

<!-- one line per closed ticket: name (linked) + gist of the answer -->

- [Clone and verify](tickets/001-clone-and-verify.md) — Repo cloned locally, `.venv` + deps installed, CLI verified to start; `.venv/` added to `.gitignore`; Arch requires virtualenv for pip
- [Bootstrap agent infrastructure](tickets/002-bootstrap-agent-infrastructure.md) — AGENTS.md, CONTEXT.md, issue-tracker.md, triage-labels.md, ADR template created and committed on `chore/bootstrap` branch
- [Setup development environment](tickets/003-setup-development-environment.md) — pyproject.toml, ruff/pytest/mypy config, .env.example, scripts/bootstrap.sh + lint.sh, all lint passes clean
- [Architecture documentation](tickets/004-architecture-documentation.md) — docs/architecture.md with module graph, data flow, SRS algorithm, prompt templates, audio pipeline, 8 design decisions, 8 latent issues documented; README claims checked
- [Testing and CI](tickets/005-testing-and-ci.md) — 52 tests (config, progress, conversation, fala smoke test), .github/workflows/ci.yml, fixed load_vocabulary parsing bug

## Fog

- **Feature roadmap** — what to build after infrastructure is solid? New modes? Web/mobile port? Pronunciation analyzer? Can't sharpen until the codebase is understood.
- **TTS/STT quality** — current OpenAI TTS voices are English-optimised; pt-PT voices are scarce. Worth investigating alternatives (ElevenLabs, local models) when the audio module gets attention.
- **SRS broken** — `update_vocab_after_review()` and `save_learning_record()` exist but are never called. Words are added at confidence=0.3 but never graduate. Needs a dedicated fix ticket.
- **Conversation UX** — the warmup→free-conversation flow works, but session quality depends entirely on the LLM prompt. Long-term improvements likely need prompt versioning and A/B evaluation.
- **Multi-user / persistence** — currently single-user file-based. Multi-user or cloud sync is a known direction but too vague to ticket.
- **Evaluation** — how to measure learning progress objectively? LLM summary is subjective. A structured assessment mode is a candidate feature.
