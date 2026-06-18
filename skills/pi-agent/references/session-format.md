# Session File Format

Source: https://pi.dev/docs/latest/session-format

Sessions are JSONL files. Each line is a JSON object with `type`. Entries form a tree through `id` and `parentId`.

## Location

```text
~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl
```

Existing sessions auto-migrate to current version. Version 3 renamed `hookMessage` role to `custom`.

## Message Content

Messages use content blocks: `text`, `image`, `thinking`, and `toolCall`. Base roles include `user`, `assistant`, and `toolResult`. Extended roles include `bashExecution`, `custom`, `branchSummary`, and `compactionSummary`.

Assistant messages include `api`, `provider`, `model`, `usage`, `stopReason`, optional `errorMessage`, timestamp, and content blocks.

## Entry Types

- `session`: header, first line, metadata only.
- `message`: wraps an `AgentMessage`.
- `model_change`: model switches.
- `thinking_level_change`: thinking level changes.
- `compaction`: summary of earlier messages with `firstKeptEntryId` and `tokensBefore`.
- `branch_summary`: summary of an abandoned branch.
- `custom`: extension state, not sent to LLM.
- `custom_message`: extension-injected message, sent to LLM.
- `label`: user-defined bookmark on an entry.
- `session_info`: display name metadata.

## Context Building

`buildSessionContext()` walks from current leaf to root. If a `CompactionEntry` is on the path, Pi emits the summary first, then messages from `firstKeptEntryId`, then later messages.

## SessionManager API

Static factories: `create`, `open`, `continueRecent`, `inMemory`, `forkFrom`.

Listing: `list`, `listAll`.

Session management: `newSession`, `setSessionFile`, `createBranchedSession`.

Append: `appendMessage`, `appendThinkingLevelChange`, `appendModelChange`, `appendCompaction`, `appendCustomEntry`, `appendSessionInfo`, `appendCustomMessageEntry`, `appendLabelChange`.

Tree: `getLeafId`, `getLeafEntry`, `getEntry`, `getBranch`, `getTree`, `getChildren`, `getLabel`, `branch`, `resetLeaf`, `branchWithSummary`.

Info/context: `buildSessionContext`, `getEntries`, `getHeader`, `getSessionName`, `getCwd`, `getSessionDir`, `getSessionId`, `getSessionFile`, `isPersisted`.
