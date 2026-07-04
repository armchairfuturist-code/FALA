# Triage Labels

This project uses the `setup-matt-pocock-skills` label convention for GitHub Issues.

## Canonical labels

| Label | Purpose | Agent behavior |
|-------|---------|----------------|
| `needs-triage` | Default for new issues | Agent skips until triaged |
| `needs-info` | Waiting on more info from reporter | Agent skips |
| `ready-for-agent` | Triaged and actionable by agent | Agent picks up |
| `ready-for-human` | Needs human judgement/review | Agent skips |
| `wontfix` | Deliberately not addressing | Agent skips |

## Wayfinder labels (local-markdown tracker)

See `docs/agents/issue-tracker.md` for the `wayfinder:*` label set used in the local-markdown ticket files.
