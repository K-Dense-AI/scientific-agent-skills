# Sessions

Source: https://pi.dev/docs/latest/sessions

Pi auto-saves conversations to `~/.pi/agent/sessions/`, organized by working directory. Each session is a JSONL tree.

## Session Commands

```bash
pi -c
pi -r
pi --no-session
pi --name "my task"
pi --session <path|id>
pi --fork <path|id>
```

Interactive commands: `/resume`, `/new`, `/name`, `/session`, `/tree`, `/fork`, `/clone`, `/compact [prompt]`, `/export [file]`, `/share`.

## Resuming

`/resume` and `pi -r` open a picker. Search by typing; use Ctrl+P to toggle path display, Ctrl+S sort, Ctrl+N named-only filter, Ctrl+R rename, Ctrl+D delete. Pi uses `trash` when available.

## Branching

Sessions are trees with `id` and `parentId`. `/tree` lets you jump to a previous point and continue without creating a new file. Selecting a user/custom message moves to its parent and puts that message in the editor so it can be edited and resubmitted. Selecting assistant/tool/compaction entries moves the leaf there with an empty editor.

## Tree vs Fork vs Clone

- `/tree`: same session file, full tree, optional branch summary.
- `/fork`: new session file from an earlier user message.
- `/clone`: new session file duplicating current active branch.

## Branch Summaries

When switching branches through `/tree`, Pi can summarize the abandoned branch and attach that context at the new position. See `compaction.md` for internals.
