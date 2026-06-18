# Compaction and Branch Summarization

Source: https://pi.dev/docs/latest/compaction

Pi uses compaction to summarize older content when context grows too long, and branch summarization to preserve context when changing branches.

## Mechanisms

| Mechanism | Trigger | Purpose |
|---|---|---|
| Compaction | context exceeds threshold or `/compact` | Summarize old messages to free context |
| Branch summarization | `/tree` navigation | Preserve context when switching branches |

## Auto-Compaction

Triggers when:

```text
contextTokens > contextWindow - reserveTokens
```

Defaults: `reserveTokens` 16384, `keepRecentTokens` 20000. Configure under `compaction` in settings.

Compaction finds a cut point, summarizes old messages, appends a `CompactionEntry`, then reloads session context as summary plus kept messages.

Valid cut points: user messages, assistant messages, bash execution messages, and custom messages. Pi never cuts at tool results.

## Split Turns

If one turn exceeds `keepRecentTokens`, Pi may cut mid-turn at an assistant message, generate a history summary plus turn-prefix summary, and merge them.

## Entry Shapes

`CompactionEntry` contains `type`, `id`, `parentId`, `timestamp`, `summary`, `firstKeptEntryId`, `tokensBefore`, optional `fromHook`, and optional `details`.

`BranchSummaryEntry` contains `type`, `id`, `parentId`, `timestamp`, `summary`, `fromId`, optional `fromHook`, and optional `details`.

Default details track `readFiles` and `modifiedFiles`; extensions may store JSON-serializable custom details.

## Extension Hooks

`session_before_compact` can cancel or provide custom compaction. Convert messages with `convertToLlm()` and `serializeConversation()` when using a custom summarizer.

`session_before_tree` can cancel navigation or provide a custom branch summary when the user chose to summarize.

## Settings

```json
{
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000
  }
}
```
