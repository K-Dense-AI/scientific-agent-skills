# JSON Event Stream Mode

Source: https://pi.dev/docs/latest/json

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Use JSON mode for one-shot prompts that output all session events as JSON lines to stdout.

```bash
pi --mode json "Your prompt"
```

## Event Types

Wire events use `JsonAgentSessionEvent`, which matches `AgentSessionEvent` except that streaming message updates omit cumulative snapshots:

```typescript
type WithoutPartial<T> = T extends { partial: unknown } ? Omit<T, "partial"> : T;

type JsonAssistantMessageEvent<T> = T extends { type: "toolcall_start"; partial: unknown }
  ? WithoutPartial<T> & { id: string; toolName: string }
  : WithoutPartial<T>;

type JsonAgentSessionEvent =
  | Exclude<AgentSessionEvent, { type: "message_update" }>
  | { type: "message_update"; usage: Usage; assistantMessageEvent: JsonAssistantMessageEvent<AssistantMessageEvent> };
```

`AgentSessionEvent` is `AgentEvent` plus session-level events:

- `agent_settled` — no further automatic continuation
- `queue_update` — `{ steering: readonly string[], followUp: readonly string[] }`, emitted whenever either queue changes
- `compaction_start` — `{ reason: "manual" | "threshold" | "overflow" }`
- `compaction_end` — `{ reason, result: CompactionResult | undefined, aborted, willRetry, errorMessage? }`
- `auto_retry_start` — `{ attempt, maxAttempts, delayMs, errorMessage }`
- `auto_retry_end` — `{ success, attempt, finalError? }`
- `summarization_retry_scheduled` — `{ attempt, maxAttempts, delayMs, errorMessage }`
- `summarization_retry_attempt_start` — `{ source: "branchSummary" }` or `{ source: "compaction", reason }`
- `summarization_retry_finished`

Base `AgentEvent` types:

- `agent_start`, `agent_end` (`messages`, `willRetry`)
- `turn_start`, `turn_end` (`message`, `toolResults`)
- `message_start` (`message`), `message_update` (`usage`, `assistantMessageEvent`), `message_end` (`message`)
- `tool_execution_start` (`toolCallId`, `toolName`, `args`), `tool_execution_update` (+ `partialResult`), `tool_execution_end` (`result`, `isError`)

## Output Format

First line is the session header:

```json
{"type":"session","version":3,"id":"uuid","timestamp":"...","cwd":"/path"}
```

RPC shares these event shapes but emits no session header. Split records on LF only. The following sequence is schematic: message and usage objects are abbreviated, and other events may interleave.

```json
{"type":"agent_start"}
{"type":"turn_start"}
{"type":"message_start","message":{"role":"assistant","content":[]}}
{"type":"message_update","usage":{},"assistantMessageEvent":{"type":"text_delta","contentIndex":0,"delta":"Hello"}}
{"type":"message_end","message":{}}
{"type":"turn_end","message":{},"toolResults":[]}
{"type":"agent_end","messages":[],"willRetry":false}
{"type":"agent_settled"}
```

`toolcall_start` additionally carries `id` and `toolName`; nested execution events may carry `parentToolCallId`. Session events also include `entry_appended`, session-info/thinking changes, and queue lifecycle notifications; tolerate new event types.

`message_update` records are delta-only: they omit both the cumulative `message` field and `assistantMessageEvent.partial` to keep stream size linear. The top-level `usage` field carries the latest cumulative provider-reported usage and may stay zero when a provider only reports usage at completion. Assemble live text, thinking, or tool-call arguments from `contentIndex` and `delta`; `message_end` holds the final authoritative message.

## Example

```bash
pi --mode json "List files" 2>/dev/null | jq -c 'select(.type == "message_end")'
```

For bidirectional control, use RPC instead of JSON mode.
