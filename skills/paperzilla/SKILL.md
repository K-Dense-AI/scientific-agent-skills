---
name: paperzilla
description: Reads projects, searches project feeds, and retrieves recommendations and canonical papers in Paperzilla through the pz CLI. Supports recent recommendations, paper details, markdown-based summaries, recommendation feedback, JSON export, and Atom feed URLs.
license: MIT
compatibility: Requires the pz CLI, network access, and a Paperzilla account with CLI access. Source builds require Go 1.23 or later.
metadata:
  version: "1.2"
  skill-author: Paperzilla Inc
  upstream-version: "pz 0.7.1"
  last-reviewed: "2026-10-01"
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

Use the official `pz` CLI. This skill targets **0.7.1**, checked against the
official release source and binary. Command examples use placeholder IDs; replace
them with records returned by your account. CLI behavior was tested against a
local mock server, not an authenticated Paperzilla account.

Start with `pz --version`, then list projects, select a project, browse or search
its feed, and inspect selected recommendations. Keep project recommendations
separate from the underlying canonical paper when summarizing or exporting.

## Install

### macOS
```bash
brew install paperzilla-ai/tap/pz
```

If Homebrew 6 or later rejects this formula as untrusted, the official guide uses
`brew trust --formula paperzilla-ai/tap/pz`, then retries installation. Trust only
that formula. Installation and upgrade commands were documentation-checked, not
executed during this review.

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

Login sends a one-time code to the account email and saves the session locally.
Complete it interactively before running JSON exports: missing or expired
credentials can trigger login prompts on stdout. The CLI checks account access
and refreshes tokens automatically; report access/upgrade errors rather than
treating them as an empty feed.

**Version-specific discrepancy:** the online guides describe anonymous canonical
paper access, but the 0.7.1 binary requires login and a CLI-access check even for
`pz paper`. Its subsequent canonical-paper HTTP request uses a public route. Do
not promise an anonymous CLI workflow for this release.

## CLI reference

If the current profile uses `pz`, these are the core commands.

### List projects
```bash
pz project list
pz project list --json
```

### Show one project
```bash
pz project <project-id>
pz project <project-id> --json
```

The list JSON is an array containing `id`, `name`, `mode`, and `visibility`.
The single-project JSON also includes keywords, watched sources, and categories.

### Browse project feed
```bash
pz feed <project-id>
```

Useful flags:
- `--must-read`
- `--since YYYY-MM-DD`
- `--limit N`
- `--offset N` (zero-based results to skip)
- `--json`
- `--atom`

Examples:
```bash
pz feed <project-id> --must-read --since 2026-03-01 --limit 5
pz feed <project-id> --limit 20 --offset 20 --json
pz feed <project-id> --json
pz feed <project-id> --atom
```

`--since` filters when recommendations were ready, not paper publication date.
Browse JSON contains `items`, `total`, `limit`, and `offset`. A command fetches
one page; it does not export the entire feed automatically. Retain the same
filters, advance from the returned offset by the number of items received, and
stop on an empty page or when the returned total is reached. Deduplicate by
recommendation ID if the live feed changes while paging.

Feed output can include existing recommendation feedback markers:

- `[↑]` upvote
- `[↓]` downvote
- `[★]` star

### Search the full project feed

```bash
pz feed search --project-id <project-id> --query "latent retrieval" --json
pz feed search --project-id <project-id> --query "retrieval" --feedback-filter starred --must-read --limit 20 --offset 20 --json
```

Search ranks results across the whole project feed. Use a trimmed query of
3–200 characters and a positive `--limit` up to 100. `--offset` must be
nonnegative. Feedback filters are `all`, `unrated`, `liked`, `disliked`, `starred`,
`not-relevant`, and `low-quality`; these hyphenated filters differ from the
underscored downvote reasons below. Search does not accept `--since`.

Search JSON contains `items`, `limit`, `offset`, `has_more`, and `query`, with no
exact total. Request the next offset only while `has_more` is true, keeping the
query and filters unchanged. Stop and report an inconsistent empty page rather
than looping indefinitely. The second example illustrates a subsequent page.

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

Feedback changes account data; use it when the user requests that change.
Downvote reasons are `not_relevant` or `low_quality`, and `--reason` applies only
to a downvote. Add `--json` to get the feedback object; clearing returns
`{"project_paper_ref": "...", "cleared": true}`. `clear` is a subcommand before
the recommendation ID.

## Keep paper and recommendation identities separate

A canonical `paper-id` identifies the paper; a `project-paper-id` identifies its
recommendation within a project. Take both from returned records and retain the
project association when exporting results. Use the recommendation ID for `rec`
and feedback operations, even if the same paper appears in several projects.
In feed JSON, `items[].id`/`items[].short_id` are recommendation identifiers;
`items[].paper.id`/`items[].paper.short_id` are canonical paper identifiers.
Do not infer recommendation IDs from a DOI or canonical paper ID. See the
[official CLI documentation](https://github.com/paperzilla-ai/pz).

When markdown is still being prepared, report that state and summarize only the
metadata or abstract actually returned. A retry message is not full-text evidence.

## Output and automation

- Prefer `--json` for machine parsing after completing login. `paper` and `rec`
  reject combining `--json` with `--markdown`.
- `pz paper --markdown` only returns markdown when it is already prepared.
- `pz rec --markdown` and project-scoped `pz paper --project ... --markdown`
  can queue markdown generation. A pending message can exit successfully; check
  the content before treating stdout as full text. Avoid repeated immediate
  retries and report the pending state.
- `--atom` returns a personal feed URL for feed readers and can create a feed
  token. Anyone holding that URL can read the feed; keep its token out of logs,
  public reports, and repositories. It does not return Atom XML or page JSON,
  and browse filters are not applied to the generated URL.
- A relevance score expresses project matching, not scientific validity or an
  effect estimate. Label whether a summary used metadata, an abstract, or actual
  markdown. Missing PDF URLs do not imply that a source landing page is absent.

## Configuration

```bash
export PZ_API_URL="https://paperzilla.ai"
```

The default already points to Paperzilla; change it only for a trusted service
or a local test server. Authenticated requests send session credentials there.
`PZ_TOKENS_PATH` optionally selects a session file; by default the CLI uses
`~/.paperzilla/tokens.json`. Never export that file as research data.

See [the verified CLI contracts](references/cli-contracts.md) for request routes,
response shapes, pagination, and the documentation/source discrepancy.

## References

- Docs: https://docs.paperzilla.ai/guides/cli
- Quickstart: https://docs.paperzilla.ai/guides/cli-getting-started
- Repo: https://github.com/paperzilla-ai/pz
