# RPC Mode

Sources: https://pi.dev/docs/latest/rpc, https://pi.dev/docs/latest/rpc-commands, https://pi.dev/docs/latest/rpc-extension-ui

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

RPC mode runs Pi headlessly over stdin/stdout JSONL. Use it for language-agnostic clients, IDE integrations, custom UIs, or subprocess isolation. For Node/TypeScript in-process apps prefer the SDK unless you want subprocess isolation.

```bash
pi --mode rpc [options]
```

Common options: `--provider`, `--model` (supports `provider/id` and `:<thinking>`), `--name`/`-n`, `--no-session`, `--session-dir`.

## Framing

Commands are JSON objects on stdin, one per line; responses (`type: "response"`) and events stream to stdout as JSON lines. Use LF (`\n`) as the only record delimiter, strip an optional trailing `\r`, and never use readers that split on Unicode separators — Node `readline` is not protocol-compliant because it also splits on U+2028/U+2029, which are valid inside JSON strings.

Commands accept an optional `id`; the response echoes it. Events generally omit `id`; `bash_execution_update` carries the `id` of its originating `bash` command.

Responses have the shape `{"type":"response","command":"...","success":true|false,"data":{...},"error":"..."}`. Parse failures return `command: "parse"`.

## Prompting Commands

`prompt` — `{"id":"req-1","type":"prompt","message":"Hello"}`. Optional `images: [{"type":"image","data":"base64...","mimeType":"image/png"}]`. While streaming, `streamingBehavior` is required (`"steer"` or `"followUp"`) or the command errors. Extension commands execute immediately even during streaming; skill commands and prompt templates expand before sending or queueing. `success: true` returns `data.disposition: "started" | "queued" | "handled"`; later failures arrive as events, not a second response. A handled prompt starts no run. Wait for `agent_settled` only for work that started.

`steer` — queue a steering message delivered after the current assistant turn's tool calls. `follow_up` — queue a message delivered when the agent is fully done. Both accept `images`, invoke input handlers, expand skills/templates, reject extension commands, and return `{ disposition: "queued" | "handled" }`.

`abort` — abort the current agent operation. `clear_queue` clears queued messages and returns the removed `{ steering, followUp }` arrays.

`new_session` — optional `parentSession`; response `data: { cancelled }` (an extension may cancel via `session_before_switch`).

## State, Model, Thinking

- `get_state` → `model` (full Model object or `null`), `thinkingLevel`, `isStreaming`, `isCompacting`, `steeringMode`, `followUpMode`, `sessionFile`, `sessionId`, `sessionName`, `autoCompactionEnabled`, `messageCount`, `pendingMessageCount`.
- `get_messages` → all `AgentMessage` objects.
- `set_model` (`provider`, `modelId`) → full Model object.
- `cycle_model` → `{ model, thinkingLevel, isScoped }`, or `null` data with one model.
- `get_available_models` → array of Model objects.
- `set_thinking_level` (`off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`; `xhigh`/`max` only when the model supports them).
- `cycle_thinking_level` → `{ level }`, `null` if the model has no thinking.
- `get_available_thinking_levels` → `{ levels }`; `["off"]` for non-reasoning models.

## Queue, Compaction, Retry

- `set_steering_mode` / `set_follow_up_mode`: `"all"` or `"one-at-a-time"` (default).
- `compact` with optional `customInstructions` → `{ summary, firstKeptEntryId, tokensBefore, estimatedTokensAfter, usage, details }`. `estimatedTokensAfter` is a heuristic over the rebuilt context, not a provider-exact count; `usage` may be omitted by custom compaction handlers.
- `set_auto_compaction` (`enabled`), `set_auto_retry` (`enabled`), `abort_retry`.

## Bash

`bash` (`command`, optional `id`) executes immediately, streams `bash_execution_update` events, and returns `{ output, exitCode, cancelled, truncated }` plus `fullOutputPath` when truncated. Internally a `BashExecutionMessage` is stored in agent state; it reaches the LLM on the **next** `prompt`, rendered as ``Ran `cmd``` plus a fenced output block. Multiple bash commands before a prompt are all included. `abort_bash` aborts a running command.

## Session Commands

- `get_session_stats` → session file/id, message counts, `tokens` (`input`, `output`, `cacheRead`, `cacheWrite`, `total`), `cost`, and `contextUsage` (`tokens`, `contextWindow`, `percent`). Totals include tool-reported usage and summary generation. `contextUsage` is omitted without a model/context window; `tokens`/`percent` are `null` right after compaction until a fresh assistant response provides usage.
- `export_html` with optional `outputPath` → `{ path }`.
- `switch_session` (`sessionPath`) → `{ cancelled }`.
- `fork` (`entryId`) → `{ text, cancelled }`; `clone` → `{ cancelled }`. Both can be cancelled by `session_before_fork`.
- `get_fork_messages` → `[{ entryId, text }]`.
- `get_entries` with optional `since` cursor → `{ entries, leafId }`. Includes pre-compaction history and abandoned branches, unlike `get_messages`. Entry ids are durable cursors across client restarts; an unknown `since` returns `success: false`. `leafId` is `null` for an empty session.
- `get_tree` → `{ tree, leafId }` where each node is `{ entry, children, label?, labelTimestamp? }`. Orphaned entries appear as extra roots.
- `get_last_assistant_text` → `{ text }` or `{ text: null }`.
- `set_session_name` (`name`); read it back from `get_state.sessionName`. Set the initial name with `--name`.

## Commands Discovery

`get_commands` returns extension commands, prompt templates, and skills (`skill:` prefixed) with `name`, `description`, `source` (`extension` | `prompt` | `skill`), optional `location` (`user` | `project` | `path`), and `path`. Built-in TUI commands such as `/settings` are interactive-only and excluded.

## Events

`agent_start`; `agent_end` (`messages`, `willRetry`); `agent_settled` (nothing will continue automatically — no retry, compaction retry, or queued continuation); `turn_start` / `turn_end`; `message_start` / `message_update` / `message_end`; `bash_execution_update`; `tool_execution_start` / `_update` / `_end`; `queue_update`; `compaction_start` / `compaction_end`; `auto_retry_start` / `auto_retry_end`; `summarization_retry_scheduled` / `summarization_retry_attempt_start` / `summarization_retry_finished`; `extension_error`.

`message_update.assistantMessageEvent` types: `text_start`, `text_delta`, `text_end`, `thinking_start`, `thinking_delta`, `thinking_end`, `toolcall_start`, `toolcall_delta`, `toolcall_end`.

`message_update` is delta-only — it carries a top-level `usage` object plus the delta event, and omits both the former cumulative `message` field and `assistantMessageEvent.partial`:

```json
{"type":"message_update","usage":{"input":100,"output":1,"cacheRead":0,"cacheWrite":0,"totalTokens":101,"cost":{}},
 "assistantMessageEvent":{"type":"text_delta","contentIndex":0,"delta":"Hello "}}
```

`usage` is the latest cumulative provider-reported usage and may stay zero until completion. Clients needing a live partial message must assemble it from `message_start` and subsequent events using `contentIndex`; treat `message_end.message` as authoritative. For tool calls, buffer `toolcall_delta.delta` — `toolcall_end.toolCall` holds the completed call.

`compaction_start`/`compaction_end` carry `reason` (`"manual"`, `"threshold"`, `"overflow"`). On overflow success, `willRetry` is `true` and the prompt is retried. Aborted compaction omits `result` and sets `aborted: true`; failure omits `result`, sets `aborted: false`, and includes `errorMessage`. `tool_execution_update.partialResult` is tool-defined; do not assume every extension emits cumulative output.

## Extension UI Protocol

Extension dialogs (`select`, `confirm`, `input`, `editor`) emit `extension_ui_request` on stdout and block until the client sends `extension_ui_response` on stdin with the matching `id`. Fire-and-forget methods (`notify`, `setStatus`, `setWidget`, `setTitle`, `set_editor_text`) emit a request with no response expected. A `timeout` field means the agent auto-resolves when it expires, so clients need not track timeouts.

Responses: `{"type":"extension_ui_response","id":"...","value":"..."}` for select/input/editor, `{"confirmed":true|false}` for confirm, `{"cancelled":true}` to dismiss any dialog.

Degraded in RPC mode: `custom()` returns `undefined`; `setWorkingMessage`, `setWorkingIndicator`, `setFooter`, `setHeader`, `setEditorComponent`, `setToolsExpanded` are no-ops; `getEditorText()` returns `""`; `getToolsExpanded()` returns `false`; `pasteToEditor()` delegates to `setEditorText()`; `getAllThemes()` returns `[]`; `getTheme()` returns `undefined`; `setTheme()` returns `{ success: false, error }`. `ctx.mode` is `"rpc"` and `ctx.hasUI` is `true` — use `ctx.mode === "tui"` to guard real-terminal features.

## Message Types

`UserMessage` (`role`, `content` string or blocks, `timestamp`, `attachments`), `AssistantMessage` (`content` with `text`/`thinking`/`toolCall` blocks, `api`, `provider`, `model`, `usage`, `stopReason` ∈ `stop`/`length`/`toolUse`/`error`/`aborted`/`deferred`, `timestamp`), `ToolResultMessage` (`toolCallId`, `toolName`, `content`, optional `usage` for nested LLM work, `isError`), `BashExecutionMessage` (from the `bash` command, not LLM tool calls), and `Attachment`. Full definitions in `references/session-format.md`.
