# JSON Event Stream Mode

Source: https://pi.dev/docs/latest/json

Use JSON mode for one-shot prompts that output all session events as JSON lines to stdout.

```bash
pi --mode json "Your prompt"
```

## Event Types

`AgentSessionEvent` includes base agent events plus queue, compaction, and retry events:

- `agent_start`, `agent_end`
- `turn_start`, `turn_end`
- `message_start`, `message_update`, `message_end`
- `tool_execution_start`, `tool_execution_update`, `tool_execution_end`
- `queue_update`
- `compaction_start`, `compaction_end`
- `auto_retry_start`, `auto_retry_end`

`queue_update` emits full pending steering and follow-up queues. Compaction events cover manual and automatic compaction.

## Output Format

First line is the session header:

```json
{"type":"session","version":3,"id":"uuid","timestamp":"...","cwd":"/path"}
```

Subsequent lines are events:

```json
{"type":"agent_start"}
{"type":"turn_start"}
{"type":"message_update","message":{},"assistantMessageEvent":{"type":"text_delta","delta":"Hello"}}
{"type":"agent_end","messages":[]}
```

## Example

```bash
pi --mode json "List files" 2>/dev/null | jq -c 'select(.type == "message_end")'
```

For bidirectional control, use RPC instead of JSON mode.
