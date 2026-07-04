# Issue Tracker

This project uses a **local-markdown issue tracker** for wayfinding — tickets are `.md` files in `docs/agents/tickets/`.

## Wayfinding operations

### Labels

Each ticket has a YAML frontmatter with a `labels` field:

| Label | Meaning |
|-------|---------|
| `wayfinder:map` | The map issue (one per project effort) |
| `wayfinder:research` | Reading/investigation ticket |
| `wayfinder:prototype` | Build a cheap artifact to react to |
| `wayfinder:grilling` | Conversation-driven decision |
| `wayfinder:task` | Manual work or setup |
| `wayfinder:claimed` | Currently being worked on |
| `wayfinder:closed` | Resolved and closed |
| `wayfinder:unclaimed` | Available to claim |

### Blocking

Blocking is expressed in the `blocked_by` frontmatter field — an array of ticket filenames (without extension):

```yaml
blocked_by: [001-clone-and-verify]
```

A ticket is **unblocked** when every ticket in `blocked_by` has `wayfinder:closed`.

### Frontier

The **frontier** is the set of tickets that are:
- Open (no `wayfinder:closed` label)
- Unblocked (all `blocked_by` entries are closed)
- Unclaimed (no `wayfinder:claimed` label)

Find the frontier by listing `docs/agents/tickets/*.md` and checking frontmatter.

### Ticket lifecycle

1. Create ticket with `wayfinder:unclaimed` label
2. Claim: change label to `wayfinder:claimed` **before** starting work
3. Resolve: add a `## Resolution` section, add `wayfinder:closed` label
4. Append a one-line pointer to the map's `## Decisions so far`
5. Graduate any fog that became specifiable

### Writing tickets

Each ticket is a markdown file in `docs/agents/tickets/`:

```markdown
---
type: research | prototype | grilling | task
labels: [wayfinder:<type>, wayfinder:unclaimed]
blocked_by: []
---

## Question

<the decision or investigation this ticket resolves>

## Acceptance

<verifiable conditions for closing>

## Assets

- (linked when resolved)
```
