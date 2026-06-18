# RPC Mode

Source: https://pi.dev/docs/latest/rpc

RPC mode runs Pi headlessly over stdin/stdout JSONL. Use it for language-agnostic clients, IDE integrations, custom UIs, or subprocess isolation.

```bash
pi --mode rpc [options]
```

Common options: `--provider`, `--model`, `--name/-n`, `--no-session`, `--session-dir`.

For Node/TypeScript in-process apps, prefer the SDK unless subprocess isolation is desired.

## Framing

Commands are JSON objects sent to stdin, one per line. Responses and events are JSON objects streamed to stdout, one per line. Use LF (`
`) as the only record delimiter; strip trailing `` for CRLF input. Do not use generic line readers that split on Unicode separators. Node `readline` is not protocol-compliant because it also splits on U+2028/U+2029.

Commands can include optional `id`; corresponding responses echo it. Events do not include `id`.

## Prompting Commands

`prompt`: send a user prompt. Response means accepted, queued, or handled; later failures come through events.

```json
{"id":"req-1","type":"prompt","message":"Hello"}
```

Add images with `images: [{"type":"image","data":"base64...","mimeType":"image/png"}]`.

If streaming, include `streamingBehavior: "steer"` or `"followUp"`. Extension commands execute immediately; skills and prompt templates expand before sending/queueing.

`steer`: queue a steering message delivered after current assistant turn tool calls.

`follow_up`: queue a message delivered after the agent is fully done.

`abort`: abort current agent operation.

`new_session`: start fresh, optionally with `parentSession`; can be cancelled by extension.

## State and Model Commands

- `get_state`: returns model, thinkingLevel, streaming/compacting state, queue modes, session info, message counts, auto-compaction.
- `get_messages`: returns all `AgentMessage` objects.
- `set_model`: switch model.
- `cycle_model`: cycle next available/scoped model.
- `get_available_models`: list configured models.
- `set_thinking_level`: set `off`, `minimal`, `low`, `medium`, `high`, or `xhigh`.
- `cycle_thinking_level`: cycle supported levels.

## Queue, Compaction, Retry

- `set_steering_mode`: `all` or `one-at-a-time`.
- `set_follow_up_mode`: `all` or `one-at-a-time`.
- `compact`: manually compact; accepts `customInstructions`.
- `set_auto_compaction`: enable/disable auto compaction.
- `set_auto_retry`: enable/disable transient-error retry.
- `abort_retry`: cancel retry delay and stop retrying.

## Bash

`bash` executes immediately and returns output. A `BashExecutionMessage` is stored in agent state but no event is emitted for it. The output reaches the LLM on the next `prompt`.

`abort_bash` aborts a running bash command.

## Session Commands

- `get_session_stats`: token totals, cost, context usage.
- `export_html`: export current session.
- `switch_session`: load another session; extension can cancel.
- `fork`: create a new fork from an earlier user message.
- `clone`: duplicate active branch into a new session.
- `get_fork_messages`: list forkable user messages.
- `get_last_assistant_text`: last assistant text or null.
- `set_session_name`: set display name.

## Commands Discovery

`get_commands` lists extension commands, prompt templates, and skills. Built-in TUI commands such as `/settings` are interactive-only and are not included.

## Events

RPC streams the same major events as the SDK/JSON mode: agent, turn, message, tool execution, queue, compaction, retry, and extension errors.
