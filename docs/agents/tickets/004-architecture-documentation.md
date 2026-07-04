---
type: research
labels: [wayfinder:research, wayfinder:unclaimed]
blocked_by: [002-bootstrap-agent-infrastructure, 003-setup-development-environment]
---

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

## Assets

- `docs/architecture.md`
