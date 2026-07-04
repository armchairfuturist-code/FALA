---
type: task
labels: [wayfinder:task, wayfinder:claimed, wayfinder:closed]
blocked_by: [001-clone-and-verify]

---

## Resolution

**Status**: ✅ All criteria met

1. ✅ `AGENTS.md` at project root — stack, commands, code layout, testing/linting, conventions
2. ✅ `docs/agents/issue-tracker.md` — local-markdown tracker: labels, blocking, frontier, lifecycle, ticket format
3. ✅ `CONTEXT.md` — project context: what/why/how, design decisions, architecture overview, current state
4. ✅ `docs/adr/` directory with `0000-template.md` (status, date, context, decision, consequences)
5. ✅ `docs/agents/triage-labels.md` — canonical labels (needs-triage, ready-for-agent, etc.)
6. ✅ All committed on `chore/bootstrap` branch (commit `14988e7`)

**Commit**: `14988e7` on `chore/bootstrap`

## Assets

- `AGENTS.md`
- `CONTEXT.md`
- `docs/agents/issue-tracker.md`
- `docs/agents/triage-labels.md`
- `docs/adr/0000-template.md`

## Question

What agent infrastructure files and conventions does this project need so that future agent sessions can work effectively?

## Acceptance

1. `AGENTS.md` exists at project root describing stack, conventions, build/test commands
2. `docs/agents/issue-tracker.md` documents the local-markdown issue tracker (wayfinder conventions)
3. `CONTEXT.md` exists with high-level project context for future sessions
4. `docs/adr/` directory exists with ADR template
5. `docs/agents/triage-labels.md` documents the canonical label set (needs-triage, needs-info, ready-for-agent, etc.)
6. All files are committed on a `chore/bootstrap` branch ready for PR
