# Issue Tracker

This project uses a **local-markdown issue tracker** for wayfinding — tickets are `.md` files in `docs/agents/tickets/`.

## Wayfinding operations

### Labels

Each ticket has a YAML frontmatter with a `labels` field. The only wayfinder labels are the type labels (one per ticket):

| Label | Mode | Meaning |
|-------|------|---------|
| `wayfinder:map` | — | The map issue (one per project effort) |
| `wayfinder:research` | AFK | Reading/investigation — agent drives alone |
| `wayfinder:prototype` | HITL | Build a cheap artifact — human reacts |
| `wayfinder:grilling` | HITL | Conversation-driven decision — human answers |
| `wayfinder:task` | HITL or AFK | Manual work blocking a decision — agent drives when it can, hands checklist when it can't |

(AFK = agent resolves without the human; HITL = human-in-the-loop, requires live exchange.)

Claiming is done via `assigned_to` (see below), **not** labels.

### Blocking

Blocking is expressed in the `blocked_by` frontmatter field — an array of ticket filenames (without extension):

```yaml
blocked_by: [001-clone-and-verify]
```

A ticket is **unblocked** when every ticket in `blocked_by` has `assigned_to: closed`.

### Claiming

Tickets are claimed by setting the `assigned_to` frontmatter field to the dev's name **before** starting work:

```yaml
assigned_to: alex
```

An open ticket with no `assigned_to` (or `assigned_to: ""`) is unclaimed.

### Frontier

The **frontier** is the set of tickets that are:
- Open (`assigned_to` is not `closed`)
- Unblocked (all `blocked_by` entries are closed)
- Unclaimed (no `assigned_to` set)

Find the frontier by listing `docs/agents/tickets/*.md` and checking frontmatter.

### Ticket lifecycle

1. Create ticket with no `assigned_to`, `blocked_by` as appropriate
2. Claim: set `assigned_to: alex` **before** starting work
3. Resolve: add a `## Resolution` section, set `assigned_to: closed`
4. Append a one-line pointer to the map's `## Decisions so far`
5. Graduate any fog that became specifiable; rule out of scope if past the destination

### Writing tickets

Each ticket is a markdown file in `docs/agents/tickets/`:

```markdown
---
type: research | prototype | grilling | task
labels: [wayfinder:<type>]
blocked_by: []
assigned_to: ""
---

## Question

<the decision or investigation this ticket resolves>

## Acceptance

<verifiable conditions for closing>

## Assets

- (linked when resolved)
```
