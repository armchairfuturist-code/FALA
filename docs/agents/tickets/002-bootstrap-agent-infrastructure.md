---
type: task
labels: [wayfinder:task, wayfinder:claimed]
blocked_by: [001-clone-and-verify]
---

## Question

What agent infrastructure files and conventions does this project need so that future agent sessions can work effectively?

## Acceptance

1. `AGENTS.md` exists at project root describing stack, conventions, build/test commands
2. `docs/agents/issue-tracker.md` documents the local-markdown issue tracker (wayfinder conventions)
3. `CONTEXT.md` exists with high-level project context for future sessions
4. `docs/adr/` directory exists with ADR template
5. `docs/agents/triage-labels.md` documents the canonical label set (needs-triage, needs-info, ready-for-agent, etc.)
6. All files are committed on a `chore/bootstrap` branch ready for PR

## Assets

- (linked when resolved)
