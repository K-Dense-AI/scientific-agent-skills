# Session File Format

Sources: https://pi.dev/docs/latest/session-format and https://pi.dev/docs/latest/message-types

Reviewed against Pi 0.99.2 documentation, declarations, and local session projection on 2026-09-30.

## Storage and framing

Pi stores a JSON object per LF-delimited line under `~/.pi/agent/sessions/`, grouped by working directory. The first record is a `session` header with `version`, session `id`, ISO `timestamp`, `cwd`, and optional `parentSession`. The header has a session ID but no tree `parentId`. Subsequent entries have their own short `id`, `parentId` (null at a root), and ISO `timestamp`.

Format version remains **3**. v1 linear sessions and v2 trees migrate on load. Version 3 does not imply a frozen set of entry/message types: tolerate unknown types. Message timestamps are Unix milliseconds, unlike entry timestamps.

## Messages

The coding-agent `AgentMessage` union contains:

- `system`: `content`, optional `sections`, `toolsAdded`, `toolsRemoved`, `replace`, and `timestamp`.
- `user`: string or text/image `content`, `timestamp`.
- `assistant`: text/thinking/tool-call `content`, `api`, `provider`, `model`, `usage`, `stopReason`, `timestamp`, plus optional response model/ID, thinking metadata and diagnostics.
- `toolResult`: `toolCallId`, `toolName`, text/image `content`, `isError`, `timestamp`, optional JSON-compatible `details`, `usage`, and bounded `nestedCalls` metadata.
- `bashExecution`: direct shell `command`, `output`, `exitCode`, `cancelled`, `truncated`, optional `fullOutputPath` and `excludeFromContext`.
- `custom`: `customType`, `content`, `display`, optional `details`.
- `branchSummary`: `summary`, `fromId` (nullable).
- `compactionSummary`: `summary`, `tokensBefore`.

`TextContent` uses `{ type: "text", text }`; images use base64 `{ type: "image", data, mimeType }`; thinking uses `{ type: "thinking", thinking }` with opaque optional signatures/redaction. `ToolCall` uses `{ type: "toolCall", id, name, arguments }` and optional namespace/signature. Preserve opaque provider replay metadata.

Assistant stop reasons include `stop`, `length`, `toolUse`, `error`, `aborted`, and `deferred`; `pending` is for streaming partials and must not persist as a completed assistant response. Deferred responses carry a provider-specific `deferred` handle. Applications can augment the message union; parsers must tolerate unknown custom roles.

`Usage` contains `input`, `output`, `cacheRead`, `cacheWrite`, `totalTokens`, and `cost` (the four component costs and `total`). Optional `reasoning` is already included in `output`; optional `cacheWrite1h` is a subset of `cacheWrite`. Never add those subsets twice. Tool and summary usage contributes to session totals.

## Entry types

| Type | Content and effect |
|---|---|
| `message` | Wraps an `AgentMessage`; system messages also persist prompt/tool changes |
| `model_change` | `provider`, `modelId`; selected model may be virtual, while assistant messages identify the physical model |
| `thinking_level_change` | `thinkingLevel` |
| `usage` | `kind`, `provider`, `model`, `usage`, optional note; contributes to totals, excluded from model context |
| `compaction` | `summary`, required `firstKeptEntryId`, `tokensBefore`, optional complete `systemMessage`, `usage`, `details`, `fromHook` |
| `context_edit` | `targetId`, `replacement`; null omits the target from future model context |
| `branch_summary` | `summary`, `fromId`, optional `usage`, `details`, `fromHook` |
| `custom` | `customType`, `data`; persisted extension state excluded from model context |
| `custom_message` | `customType`, `content`, `display`, optional `details`; sent to the model |
| `label` | `targetId`, optional `label`; absent label clears it |
| `session_info` | Session `name` |

System messages replay named prompt `sections` (`null` removes), tool additions/removals, and optional complete replacement. The first request records a complete baseline; later requests append deltas. Do not strip system messages when exporting or restoring history.

## Projected context, compaction, and branching

`SessionManager` owns the entry tree and is authoritative for finalized context. Changing `agent.state.messages` does not replace this history.

`buildContextEntries()` walks the active branch and applies its latest compaction: compaction entry, kept non-system entries beginning at `firstKeptEntryId`, then later entries. A retain-none compaction uses its own ID as `firstKeptEntryId`. The optional `systemMessage` checkpoint replaces pre-compaction prompt/tool state. **Pi 0.99.2 does not use `retainedTail` as its compaction contract.**

`buildSessionProjection()` applies the latest branch-relative `context_edit` to each selected target. Edits may replace only content or omit user, assistant, tool-result, or custom-message entries. They do not mutate raw history, UI/export data, or usage accounting. `buildSessionContext()` converts the projection into messages and obtains selected model/thinking state from the full path. Never reconstruct the model's context by concatenating every line of the session file.

`getEntries()` includes abandoned branches; `getBranch()` follows one branch. `resetLeaf()` and `branchWithSummary(null, ...)` can create multiple roots. Preserve raw history when branching or omitting failed attempts.

## SessionManager API

Creation: `create(cwd, sessionDir?, options?)`, `open(path, sessionDir?)`, `continueRecent(cwd, sessionDir?)`, `inMemory(cwd?, options?, entries?)`, `forkFrom(sourcePath, targetCwd, sessionDir?)`. Listing: async `list(cwd, sessionDir?, onProgress?)`, `listAll(onProgress?)`.

Use `appendMessage`, `appendModelChange`, `appendThinkingLevelChange`, `appendUsage`, `appendContextEdit`, `appendCustomEntry`, `appendCustomMessageEntry`, `appendSessionInfo`, and `appendLabelChange` to preserve append-only history. `appendCompaction(summary, firstKeptEntryId, tokensBefore, details?, fromHook?, usage?)` and `branchWithSummary` create summary boundaries. For exact optional arguments use installed `dist/core/session-manager.d.ts`.

Local verification exercised context replacement/omission, raw-history preservation, compaction, branching, restoring entries with `inMemory`, and session accounting without a hosted model call.
