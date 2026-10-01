# Compaction and Branch Summarization

Source: https://pi.dev/docs/latest/compaction

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Pi has two summarization mechanisms that share the same structured summary format and track file operations cumulatively.

| Mechanism | Trigger | Purpose |
|---|---|---|
| Compaction | context exceeds threshold, or `/compact` | Summarize old messages to free context |
| Branch summarization | `/tree` navigation | Preserve context when switching branches |

Both disable prompt-cache writes where supported because these one-off prompts are unlikely to be reused.

## Auto-Compaction

Triggers when `contextTokens > contextWindow - reserveTokens`. Defaults: `reserveTokens` 16384, `keepRecentTokens` 20000, configured under `compaction` in global or project settings. Exact-model `compaction.modelOverrides` can override either budget independently. `/compact [instructions]` works even with auto-compaction disabled.

Steps: walk backwards from the newest message accumulating token estimates until `keepRecentTokens` is reached (the cut point) → collect messages from the previous kept boundary (or session start) to the cut point → summarize with the structured format, passing any previous summary as iterative context → append a `CompactionEntry` → rebuild the context for the next request as summary plus messages from `firstKeptEntryId`.

On repeated compactions the summarized span starts at the previous compaction's kept boundary (`firstKeptEntryId`), not at the compaction entry, falling back to the entry after the previous compaction when that kept entry is not on the path. This re-includes messages that survived the earlier pass. `tokensBefore` is recalculated from the context-edited projection before writing the new entry.

Valid cut points: user messages, assistant messages, bash execution messages, and custom messages (`custom_message`, `branch_summary`). Pi never cuts at tool results.

## Split Turns

A user-message span starts with a user message and includes assistant turns and tool calls until the next user message. A runtime `turn_start`/`turn_end` instead encloses one assistant response and its tools. When a single turn exceeds `keepRecentTokens`, the cut lands mid-turn at an assistant message (`isSplitTurn`). Pi then generates two summaries — a history summary for previous context and a turn-prefix summary for the early part of the split turn — and merges them.

## Branch Summarization

On `/tree` navigation to a different branch: find the deepest common ancestor, walk from the old leaf back to it, include messages up to the token budget newest-first, summarize, and append a `BranchSummaryEntry` at the navigation point — the summary lands on the destination branch's new leaf, not on the branch being left.

Both mechanisms extract file operations from the tool calls being summarized **and** from previous compaction/branch-summary `details`, so read/modified file tracking accumulates across passes.

## Entry Shapes

`CompactionEntry`: `type`, `id`, `parentId`, `timestamp`, `summary`, `firstKeptEntryId`, `tokensBefore`, optional `usage` (LLM usage that generated the summary; counted in session totals), optional `fromHook` (legacy name for "provided by extension"), optional `details`.

`BranchSummaryEntry`: same plus `fromId` instead of `firstKeptEntryId`.

Default `details` is `{ readFiles: string[], modifiedFiles: string[] }`; extensions may store any JSON-serializable structure. Current entries use `firstKeptEntryId` plus an optional complete `systemMessage` checkpoint; `retainedTail` is not the Pi 0.99.2 contract. Context edits affect the projected input, while raw history and costs remain unchanged. See `references/session-format.md`.

## Summary Format

Sections: `## Goal`, `## Constraints & Preferences`, `## Progress` (Done / In Progress / Blocked), `## Key Decisions`, `## Next Steps`, `## Critical Context`, then `<read-files>` and `<modified-files>` blocks.

## Message Serialization

`serializeConversation()` renders messages as `[User]:`, `[Assistant thinking]:`, `[Assistant]:`, `[Assistant tool calls]:`, `[Tool result]:` lines so the model does not treat the input as a conversation to continue. Tool results are truncated to 2000 characters during serialization, with a marker showing how many characters were dropped — `read` and `bash` results are usually the largest contributors to context.

## Extension Hooks

`session_before_compact` receives `{ preparation, branchEntries, customInstructions, reason, willRetry, signal }`. `preparation` exposes `messagesToSummarize`, `turnPrefixMessages`, `previousSummary`, `fileOps`, `tokensBefore`, `firstKeptEntryId`, and `settings`; `reason` is `"manual"`, `"threshold"`, or `"overflow"`; `willRetry` indicates overflow recovery. Return `{ cancel: true }` or `{ compaction: { summary, firstKeptEntryId, tokensBefore, usage?, details? } }`.

To summarize with your own model, convert messages first:

```ts
import { convertToLlm, serializeConversation } from "@earendil-works/pi-coding-agent";

const text = serializeConversation(convertToLlm(preparation.messagesToSummarize));
```

`session_before_tree` receives `{ preparation, signal }` with `targetId`, `oldLeafId`, `commonAncestorId`, `entriesToSummarize`, and `userWantsSummary`. It always fires, whether or not the user chose to summarize. Return `{ cancel: true }` to cancel navigation, or `{ summary: { summary, usage?, details? } }` (used only when `userWantsSummary`).

For direct programmatic summarization, `generateSummary()` returns the text and `generateSummaryWithUsage()` returns `{ text, usage }`.

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
