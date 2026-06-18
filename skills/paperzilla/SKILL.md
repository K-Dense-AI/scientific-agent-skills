---
name: paperzilla
description: Chat with your agent about projects, recommendations, and canonical papers in Paperzilla. Use when users ask for recent project recommendations, canonical paper details, markdown-based summaries, recommendation feedback, feed export, or Atom feed URLs.
license: MIT
metadata: {"version": "1.0", "skill-author": "Paperzilla Inc"}
---

# Paperzilla

Use this skill when you want to chat with your agent about projects, recommendations, and canonical papers in Paperzilla.

## What you can ask

- "Give me the latest recommendations from project X."
- "Open recommendation Y and explain why it matters."
- "Fetch canonical paper Z as markdown and summarize it."
- "Tell me how this paper is relevant to my research."
- "Show me the feed for project X."
- "Leave feedback on a recommendation."
- "Export this paper, recommendation, or feed as JSON."

This is the core Paperzilla skill. It gives your agent direct access to Paperzilla data, but it does not impose a workflow or external delivery integration.

## Access method

Most current profiles in this repo use the `pz` CLI.

If the current profile ships extra agent-specific instructions, follow those as well.

## Install

### macOS
```bash
brew install paperzilla-ai/tap/pz
```

### Windows (Scoop)
```bash
scoop bucket add paperzilla-ai https://github.com/paperzilla-ai/scoop-bucket
scoop install pz
```

### Linux
Use the official Linux install guide:

- https://docs.paperzilla.ai/guides/cli-getting-started

### Build from source (Go 1.23+)
See the CLI repository for source builds:

- https://github.com/paperzilla-ai/pz

## Update

Check whether your CLI is up to date and get install-specific upgrade steps:

```bash
pz update
```

If detection is ambiguous, override it explicitly:

```bash
pz update --install-method homebrew
pz update --install-method scoop
pz update --install-method release
pz update --install-method source
```

Supported values are `auto`, `homebrew`, `scoop`, `release`, and `source`.

## Authentication

```bash
pz login
```

## CLI reference

If the current profile uses `pz`, these are the core commands.

### List projects
```bash
pz project list
```

### Show one project
```bash
pz project <project-id>
```

### Browse project feed
```bash
pz feed <project-id>
```

Useful flags:
- `--must-read`
- `--since YYYY-MM-DD`
- `--limit N`
- `--json`
- `--atom`

Examples:
```bash
pz feed <project-id> --must-read --since 2026-03-01 --limit 5
pz feed <project-id> --json
pz feed <project-id> --atom
```

Feed output can include existing recommendation feedback markers:

- `[↑]` upvote
- `[↓]` downvote
- `[★]` star

### Read a canonical paper
```bash
pz paper <paper-id>
pz paper <paper-id> --json
pz paper <paper-id> --markdown
pz paper <paper-id> --project <project-id>
```

### Open a recommendation from one of your projects
```bash
pz rec <project-paper-id>
pz rec <project-paper-id> --json
pz rec <project-paper-id> --markdown
```

### Leave recommendation feedback
```bash
pz feedback <project-paper-id> upvote
pz feedback <project-paper-id> star
pz feedback <project-paper-id> downvote --reason not_relevant
pz feedback clear <project-paper-id>
```

## Output and automation

- Prefer `--json` for machine parsing.
- `pz paper --markdown` only returns markdown when it is already prepared.
- `pz rec --markdown` can queue markdown generation and prints a friendly retry message while it is still being prepared.
- `--atom` returns a personal feed URL for feed readers.

## Configuration

```bash
export PZ_API_URL="https://paperzilla.ai"
```

## References

- Docs: https://docs.paperzilla.ai/guides/cli
- Quickstart: https://docs.paperzilla.ai/guides/cli-getting-started
- Repo: https://github.com/paperzilla-ai/pz
