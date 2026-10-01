# Sessions

Source: https://pi.dev/docs/latest/sessions

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Pi auto-saves conversations to `~/.pi/agent/sessions/`, organized by working directory. Each session is a JSONL tree.

## Session Commands

```bash
pi -c                  # continue most recent
pi -r                  # browse and select
pi --no-session        # ephemeral, do not save
pi --name "my task"    # display name at startup
pi --session <path|id> # specific file or partial session ID
pi --fork <path|id>    # fork into a new session file
```

Interactive: `/resume`, `/new`, `/name <name>`, `/session` (file, ID, message count, tokens, cost), `/tree`, `/fork`, `/clone`, `/compact [prompt]`, `/export [file]`, `/share`.

## Resuming and Deleting

`/resume` (and `pi -r`) opens a picker for the current project. Search by typing; Ctrl+P toggles path display, Ctrl+S cycles sort mode, Ctrl+N filters to named sessions, Ctrl+R renames, Ctrl+D deletes with confirmation. Pi uses the `trash` CLI when available instead of permanently removing files.

## Branching with `/tree`

Sessions are trees: every entry has `id` and `parentId`, and the current position is the active leaf. `/tree` jumps to any previous point and continues from there without creating a new file.

| Key | Action |
|---|---|
| ↑/↓ | Navigate visible entries |
| ←/→ | Page up/down |
| Ctrl+←/→ or Alt+←/→ | Fold/unfold or jump between branch segments |
| Shift+L | Set or clear a label on the selected entry |
| Shift+T | Toggle label timestamps |
| Enter | Select entry |
| Escape / Ctrl+C | Cancel |
| Ctrl+O | Cycle filter mode |

Filter modes: default, no-tools, user-only, labeled-only, all. Set the default with `treeFilterMode`.

### Selection Behavior

Selecting a **user or custom** message moves the leaf to that message's parent, puts the message text in the editor, and lets you edit and resubmit — creating a new branch. Selecting an **assistant, tool, compaction, or other non-user** entry moves the leaf there with an empty editor so you continue from that point. Selecting the root user message resets the leaf to an empty conversation with the original prompt in the editor.

## Tree vs Fork vs Clone

| | `/tree` | `/fork` | `/clone` |
|---|---|---|---|
| Output | Same session file | New session file | New session file |
| View | Full tree | User-message selector | Current active branch |
| Typical use | Explore alternatives in place | Start a new session from an earlier prompt | Duplicate current work before continuing |
| Summary | Optional branch summary | None | None |

## Branch Summaries

When `/tree` switches away from one branch, Pi can summarize the abandoned branch and attach the summary at the new position, preserving context without replaying the branch. When prompted, choose no summary, the default prompt, or custom focus instructions. Internals and extension hooks: `references/compaction.md`. File format and `SessionManager` API: `references/session-format.md`.
