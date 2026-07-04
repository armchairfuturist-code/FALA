---
type: research
labels: [wayfinder:research, wayfinder:claimed, wayfinder:closed]
blocked_by: [002-bootstrap-agent-infrastructure, 003-setup-development-environment]

---

## Resolution

**Status**: ✅ All criteria met

1. ✅ `docs/architecture.md` covering:
   - Mermaid module dependency graph
   - Data flow diagram for a full session lifecycle
   - SM-2 SRS algorithm with table of confidence/ease/interval changes
   - Prompt template structure for system.md, warmup.md, and dynamic prompts
   - Audio pipeline: TTS (OpenAI → mpv/ffplay/aplay) + STT (Whisper local → cloud)
   - 8 key design decisions with rationale table
2. ✅ Latent issues documented:
   - **Medium**: SRS feedback loop disconnected — `update_vocab_after_review()` never called
   - **Low**: vocab parser fragility, silent audio failure, format-string injection risk
   - **UX**: empty API key crashes before banner
3. ✅ README accuracy check — all claims accurate except "spaced repetition / SM-2" marked as partial (algorithm exists but graduation path broken)

**Key findings:**
- `/voice` toggle works, audio pipeline has graceful STT fallbacks (local Whisper → cloud API)
- SRS writes confidence at add-time but never updates it — words stay `needs_review=True` indefinitely
- `save_learning_record()` and `update_vocab_after_review()` are defined but never imported/called

**Files created:**
- `docs/architecture.md` (12.6 KB)

## Assets

- `docs/architecture.md`

## Question

What is the architecture of FALA? How do the modules connect, what data flows through the system, and what design decisions are embedded in the code?

## Acceptance

1. `docs/architecture.md` written covering:
   - Module dependency graph (with diagram in mermaid or ASCII)
   - Data flow for a typical session (start → warmup → conversation → end)
   - SRS scheduler algorithm documented
   - Prompt template structure and variables
   - Audio pipeline (STT fallback chain, TTS player chain)
   - Key design decisions and their rationale
2. Review current code for any latent bugs or edge cases, noted in the doc
3. All findings reviewed against README claims for accuracy
