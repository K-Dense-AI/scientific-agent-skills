# Extensions

Source: https://pi.dev/docs/latest/extensions

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Extensions are TypeScript modules that extend Pi. They register tools, commands, shortcuts, CLI flags, providers, renderers, UI, event handlers, and persistent session entries. They run with the full permissions of the Pi process — only install extensions you trust.

## Locations

- `~/.pi/agent/extensions/*.ts` and `~/.pi/agent/extensions/*/index.ts` (global)
- `.pi/extensions/*.ts` and `.pi/extensions/*/index.ts` (project-local, loaded only after project trust)
- Paths from `settings.json` `extensions` / `packages`

Use `pi -e ./my-extension.ts` for quick tests only; auto-discovered extensions can be hot-reloaded with `/reload`. Extensions load via [jiti](https://github.com/unjs/jiti), so TypeScript needs no compilation.

## Quick Extension

```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async (_event, ctx) => {
    ctx.ui.notify("Extension loaded", "info");
  });

  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName === "bash" && event.input.command?.includes("rm -rf")) {
      const ok = await ctx.ui.confirm("Dangerous", "Allow rm -rf?");
      if (!ok) return { block: true, reason: "Blocked by user" };
    }
  });

  pi.registerTool({
    name: "greet",
    label: "Greet",
    description: "Greet someone by name",
    parameters: Type.Object({ name: Type.String() }),
    async execute(_toolCallId, params) {
      return { content: [{ type: "text", text: `Hello, ${params.name}!` }], details: {} };
    },
  });

  pi.registerCommand("hello", {
    description: "Say hello",
    handler: async (args, ctx) => ctx.ui.notify(`Hello ${args || "world"}`, "info"),
  });
}
```

## Imports

`@earendil-works/pi-coding-agent` (extension types and APIs), `typebox` (tool parameter schemas), `@earendil-works/pi-ai` (`StringEnum` for Google-compatible enums), `@earendil-works/pi-tui` (TUI components), plus Node built-ins. Add a `package.json` next to the extension and run `npm install` for npm dependencies. Distributed packages must put runtime deps in `dependencies` — package installs use `npm install --omit=dev`.

## Factory Semantics

The default export receives `ExtensionAPI` and may be async; Pi awaits it before `session_start`, `resources_discover`, and flushing queued `pi.registerProvider()` calls. Use async factories for one-time startup work such as dynamic model discovery. Do **not** start background resources (processes, sockets, watchers, timers) in the factory — factories can run in invocations that never start a session. Start them in `session_start` or on demand, and close them in an idempotent `session_shutdown` handler.

## Event Lifecycle

Startup: `project_trust` (user/global and CLI `-e` extensions only) → `session_start { reason: "startup" }` → `resources_discover { reason: "startup" }`.

Prompt: extension commands checked first (they bypass `input`) → `input` → skill/template expansion → `before_agent_start` → `agent_start` → message events → per turn: `turn_start`, `context`, `before_provider_headers`, `before_provider_request`, `after_provider_response`, then `tool_execution_start`, `tool_call`, `tool_execution_update`, `tool_result`, `tool_execution_end` → `turn_end` → `agent_end` → `agent_settled`.

Session replacement (`/new`, `/resume`): `session_before_switch` (cancellable) → `session_shutdown` → `session_start { reason: "new" | "resume", previousSessionFile }` → `resources_discover`. `/fork` and `/clone` use `session_before_fork` (with `position: "before" | "at"`) then `reason: "fork"`. `/name` emits `session_info_changed`. Compaction: `session_before_compact` → `session_compact`. `/tree`: `session_before_tree` → `session_tree`. Model changes: `thinking_level_select` then `model_select`. Exit: `session_shutdown`.

## High-Value Hooks

- `project_trust` — must return `{ trusted: "yes" | "no" | "undecided", remember?: boolean }`. First yes/no decision wins and suppresses the built-in prompt. `ctx` is a limited trust context (cwd, mode, hasUI, select/confirm/input/notify).
- `resources_discover` — return `{ skillPaths, promptPaths, themePaths }`.
- `before_agent_start` — return `{ message }` to inject a persistent custom message. Prefer structured prompt-section/tool updates so Pi persists transcript deltas; `{ systemPrompt }` or `forceSystemPrompt` forces the leading provider prompt for this run. `event.systemPromptOptions` exposes the structured inputs Pi used: `customPrompt`, `selectedTools`, `toolSnippets`, `promptGuidelines`, `appendSystemPrompt`, `cwd`, `contextFiles`, `skills`.
- `context` — transforms the conversation without prompt/tool system messages; Pi restores that state afterward. Use `context_with_system` only to own the complete request-local transcript and preserve a system message at index zero.
- `provider_stream_event` — observes each parsed provider event before normalization; awaited, notification-only, not persisted.
- `turn_end` / `agent_before_settle` — may propose `custom`, `custom_message`, `context_edit`, or `compaction` entries and request one continuation with `continue: true`; guard against unconditional loops.
- `before_provider_headers` — mutate `event.headers` in place; a string adds/overrides, `null` deletes. Fires once per request; retries reuse the headers.
- `before_provider_request` — inspect or replace `event.payload`; handlers run in load order and `undefined` keeps it unchanged. Payload-level system-instruction rewrites are not reflected by `ctx.getSystemPrompt()`.
- `after_provider_response` — `event.status` and normalized `event.headers` before the stream body is consumed.
- `tool_call` — `event.input` is mutable and mutations affect execution (no re-validation); return `{ block: true, reason?, terminate? }` to block. `terminate` applies only to a blocked call, and the agent stops early only when every finalized result in the batch is terminating. Narrow with `isToolCallEventType("bash", event)`, or `isToolCallEventType<"my_tool", MyToolInput>(...)` for custom tools.
- `tool_result` — middleware-style chain; return partial patches (`content`, `details`, `isError`, `usage`). Use `isBashToolResult(event)` for typed bash details and `ctx.signal` for nested async work.
- `message_end` — return `{ message }` to replace the finalized message; the replacement must keep the same `role`.
- `user_bash` — intercept `!`/`!!`: return `{ operations }` (optionally wrapping `createLocalBashOperations()`) or `{ result }`.
- `input` — sees raw text before skill/template expansion. Return `{ action: "continue" | "transform" | "handled" }`; `event.source` is `"interactive" | "rpc" | "extension"` and `event.streamingBehavior` is `"steer" | "followUp" | undefined`.

In parallel tool mode, sibling tool calls are preflighted sequentially then executed concurrently, so `tool_call` is not guaranteed to see sibling tool results; `tool_result`/`tool_execution_end` may interleave in completion order while final `toolResult` message events stay in assistant source order.

## ExtensionContext

`ctx.ui` (see Custom UI), `ctx.mode` (`"tui" | "rpc" | "json" | "print"`), `ctx.hasUI` (true in TUI and RPC), `ctx.cwd`, `ctx.signal` (agent abort signal; usually `undefined` outside active turns), `ctx.isProjectTrusted()`, `ctx.sessionManager` (read-only: `getEntries`, `getBranch`, `buildContextEntries`, `getLeafId`, …), `ctx.modelRegistry` (`getProvider(id)`, `getProviderAuth(id)`, `find(...)`), `ctx.model`, `ctx.thinkingLevel`, `ctx.scopedModels`, `ctx.isIdle()`, `ctx.abort()`, `ctx.hasPendingMessages()`, `ctx.shutdown()`, `ctx.getContextUsage()`, `ctx.compact({ customInstructions, onComplete, onError })`, `ctx.getSystemPrompt()`.

`ctx.scopedModels` is the read-only list of models scoped to the session — the same set `/scoped-models` shows, resolved at session start from `--models` and the `enabledModels` setting (minimatch against `provider/modelId` or a bare `modelId`). It is empty when no scoping is configured, meaning every available model is usable. Entries are `{ model, thinkingLevel? }`, with `thinkingLevel` set only when a pattern pinned it (e.g. `anthropic/*:high`). Use it for a model picker that mirrors the built-in one instead of enumerating `ctx.modelRegistry.getAvailable()`.

Use the exported `CONFIG_DIR_NAME` instead of hardcoding `.pi` — rebranded distributions use a different name.

## ExtensionCommandContext

Command handlers additionally get session-control methods that would deadlock from event handlers: `getSystemPromptOptions()`, `waitForIdle()`, `newSession({ parentSession, setup, withSession })`, `fork(entryId, { position: "before" | "at", withSession })`, `navigateTree(targetId, { summarize, customInstructions, replaceInstructions, label })`, `switchSession(path, { withSession })`, `reload()`.

`withSession` receives a fresh `ReplacedSessionContext` with async `sendMessage()`/`sendUserMessage()`. It runs only after the old session emitted `session_shutdown` and the new instance already received `session_start`, but still executes in the original closure — so captured old `pi`/`ctx`/`sessionManager` objects are stale and throw. Capture only plain data (strings, ids) across the boundary. Treat `await ctx.reload()` as terminal for that handler (`await ctx.reload(); return;`); tools cannot call it, so expose a command and have the tool queue it with `pi.sendUserMessage("/my-reload", { deliverAs: "followUp" })`.

## ExtensionAPI

Tools: `registerTool(definition)` (works during load and at runtime — new tools are callable without `/reload`), `getActiveTools()`, `getAllTools()` (returns `name`, `description`, `parameters`, `promptGuidelines`, `sourceInfo`), `setActiveTools(names)`.

Messages and session: `sendMessage(message, { deliverAs: "steer" | "followUp" | "nextTurn", triggerTurn })`, `sendUserMessage(content, { deliverAs, expandPromptTemplates })` (`deliverAs` required while streaming; `expandPromptTemplates` defaults to `false` and opts into extension-command dispatch plus skill/prompt-template expansion), `appendEntry(customType, data)`, `setSessionName`, `getSessionName`, `setLabel(entryId, label)`.

Commands and input: `registerCommand(name, { description, handler, getArgumentCompletions })` (duplicate names get `:1`/`:2` suffixes in load order), `getCommands()` (extension → prompt → skill order, each with `sourceInfo.scope`/`origin`), `registerShortcut(key, options)`, `registerFlag(name, options)` + `getFlag(name)`.

Rendering: `registerMessageRenderer(customType, renderer)` (custom messages, in LLM context), `registerEntryRenderer(customType, renderer)` (custom entries, TUI only), `registerMarkdownTransformer(transformer)`.

`registerMarkdownTransformer` transforms the Markdown of normal user text, assistant text, and thinking blocks before Pi's built-in renderer runs. Transformers run in extension load order, each receiving the previous transformer's output plus a context of `messageType` (`"user" | "assistant" | "assistant-thinking"`), `isStreaming` (true only for partial assistant updates), and `availableWidth` (exact terminal columns):

```typescript
pi.registerMarkdownTransformer((markdown, { messageType, isStreaming }) => {
  if (isStreaming || messageType === "assistant-thinking") return markdown;
  return markdown.replaceAll("-->", "→");
});
```

A throwing transformer keeps the Markdown produced so far and continues with the next one. The hook is display-only — the session and model context keep the original message. It fires for new user messages, assistant streaming updates, restored session messages, and terminal width changes, so keep transformers synchronous and cheap.

Model and provider: `setModel(model)` (returns `false` without an API key), `getThinkingLevel()`, `setThinkingLevel(level)`, `registerProvider(nameOrProvider, config?)`, `unregisterProvider(name)`. Calls after the load phase take effect immediately. Dynamic providers can implement `refreshModels`, and a complete pi-ai `Provider` from `createProvider(...)` can be registered as the composition base with `models.json` overrides layered above.

`refreshModels` receives the canonical credential/stored-catalog/network/signal context: `context.stored` is the persisted provider snapshot, and persistence goes through generation-checked `context.publish({ persist: entry })` (`persist: null` deletes the snapshot). Live servers such as llama.cpp can return models without persisting. `context.signal` is always a concrete signal and provider callbacks must pass it to blocking I/O; public `ModelRuntime.refresh()` / `ModelRegistry.refresh()` accept an optional signal and are unbounded when it is omitted, so extensions choose their own deadlines. Cancellation stops the caller waiting even if a provider ignores the signal. OAuth `refreshToken(credentials, signal)` now takes the signal as a second argument.

Other: `exec(command, args, { signal, timeout })` → `{ stdout, stderr, code, killed }`, `on(event, handler)` (returns unsubscribe), `events` (inter-extension bus), `registerMcpServer`/`unregisterMcpServer`/`getMcpServers` for native MCP. Tools can call `ctx.executeTool(name, args, { signal, onUpdate })`; nested calls pass normal validation/hooks and emit `parentToolCallId`. Pi records bounded nested-call metadata and aggregates nested usage; callers must not double-count it.

## Custom Tools

```ts
pi.registerTool({
  name: "my_tool",
  label: "My Tool",
  description: "What this tool does (shown to the LLM)",
  promptSnippet: "One-line entry in the system prompt's Available tools section",
  promptGuidelines: ["Use my_tool when the user asks to summarize generated text."],
  parameters: Type.Object({ action: StringEnum(["list", "add"] as const), text: Type.Optional(Type.String()) }),
  prepareArguments(args) { return args; },
  async execute(toolCallId, params, signal, onUpdate, ctx) {
    onUpdate?.({ content: [{ type: "text", text: "Working..." }], details: { progress: 50 } });
    return { content: [{ type: "text", text: "Done" }], details: {}, terminate: true };
  },
  renderShell: "self",
  renderCall(args, theme, context) { /* Component */ },
  renderResult(result, options, theme, context) { /* Component */ },
});
```

- Use `StringEnum` from `@earendil-works/pi-ai` for string enums; `Type.Union`/`Type.Literal` breaks Google's API.
- `promptGuidelines` bullets are appended flat with no tool-name prefix — always name the tool ("Use my_tool when…"), never "this tool".
- `prepareArguments` runs before schema validation; use it to fold legacy argument shapes from resumed sessions instead of loosening `parameters`.
- Throw to fail a tool, or return `isError: true` when a structured failure result should remain available to script callers. With `outputSchema`, return matching `structuredContent`; ordinary model callers still receive `content`.
- `terminate: true` hints that the follow-up LLM call should be skipped, and only applies when every finalized result in the batch terminates.
- Return `usage` for nested LLM calls; Pi persists it and includes it in footer, `/session`, and RPC totals.
- Strip a leading `@` from path arguments (some models add it), and wrap read-modify-write windows in `withFileMutationQueue(absolutePath, fn)` so the tool shares the per-file queue with built-in `edit`/`write` — tools run in parallel by default. Resolve to an absolute path first; the helper canonicalizes existing files through `realpath()`.
- Truncate output. The built-in limit is 50 KB / 2000 lines, whichever hits first. Use `truncateHead` (beginning matters), `truncateTail` (end matters), `truncateLine`, `formatSize`, `DEFAULT_MAX_BYTES`, `DEFAULT_MAX_LINES`, and tell the LLM where the full output was saved.

Overriding built-ins (`read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`) works by registering the same name; interactive mode warns. Renderer inheritance is per slot, so omitting `renderCall`/`renderResult` keeps the built-in UI. `promptSnippet`/`promptGuidelines` are **not** inherited. The result shape, including `details`, must match exactly.

Remote execution: built-in tool factories accept pluggable `operations` (`ReadOperations`, `WriteOperations`, `EditOperations`, `BashOperations`, `LsOperations`, `GrepOperations`, `FindOperations`). `createBashTool(cwd, { spawnHook, exposeSessionEnvironment })` can rewrite command/cwd/env; session variables are injected before `spawnHook` (`references/environment-variables.md`).

### Dynamic Tool Loading

Register tools first; `pi.setActiveTools(names)` can activate known tools and ignores unknown names. Pi persists initial prompt/tool declarations and later changes as system messages; a provider unable to represent the transition receives a checkpoint and may lose its cache prefix. Do not assume additive changes are always cache-free.

`exposure` controls reachability: `direct` (default, declared/callable while active), `model-only` (declared while active, never callable from another tool), `codemode` (callable while registered), `deferred` (callable but discovered instead of listed), or `hidden` (unreachable). There is no public tool unregister API in Pi 0.99.2; re-register hidden to withdraw a tool. `namespace` groups tools and `annotations` carry unverified MCP-style hints. `prepareLoadout(loadout)` can change declarations/descriptions while preserving callable tools. Prefer `model-only` for user interaction and orchestrator tools. See `mcp.md` for native MCP exposure (the default server `codemode` exposure deliberately uses deferred discovery).

## State Management

Store state in tool result `details` so branching works, and rebuild it in `session_start` by walking `ctx.sessionManager.getBranch()`. `pi.appendEntry(customType, data)` persists extension state that does not enter LLM context.

## Custom UI

Dialogs: `ctx.ui.select(title, options)`, `confirm(title, message)`, `input(prompt, placeholder)`, `editor(title, prefill)`, `notify(message, "info" | "warning" | "error")`. Dialogs accept `{ timeout }` (live countdown; `select`/`input` return `undefined`, `confirm` returns `false`) or `{ signal }` when you need to distinguish timeout from user cancel.

Chrome: `setStatus(key, text)`, `setWidget(key, lines | factory, { placement: "aboveEditor" | "belowEditor" })`, `setFooter(factory)`, `setHeader(...)`, `setTitle(text)`, `setEditorText` / `getEditorText` / `pasteToEditor`, `setWorkingMessage`, `setWorkingVisible`, `setWorkingIndicator({ frames, intervalMs })`, `setToolsExpanded` / `getToolsExpanded`, `setEditorComponent(factory)` / `getEditorComponent()`, `addAutocompleteProvider(current => provider)`, `getAllThemes` / `getTheme` / `setTheme` / `theme`, and `custom(factory, { overlay, overlayOptions, onHandle })`.

Custom-component details, overlays, built-in components, and copy-paste patterns are in `references/tui.md`. Syntax highlighting helpers: `highlightCode(code, lang, theme)`, `getLanguageFromPath(path)`. Keybinding hints: `keyHint(id, description)`, `keyText(id)`, `rawKeyHint(key, description)` with namespaced ids (`app.*` for the coding agent, `tui.*` for shared TUI).

## Error Handling and Mode Behavior

Extension errors are logged and the agent continues; `tool_call` errors block the tool (fail-safe); tool `execute` failures may throw or return `isError: true`. `user_bash` exceptions and invalid defined results fail closed; only `undefined` continues to later handlers/local execution.

| Mode | `ctx.mode` | `ctx.hasUI` | Notes |
|---|---|---|---|
| Interactive | `"tui"` | `true` | Full TUI |
| RPC | `"rpc"` | `true` | Dialogs/notifications over the JSON protocol; `custom()` returns `undefined` |
| JSON | `"json"` | `false` | UI methods are no-ops |
| Print (`-p`) | `"print"` | `false` | Extensions run but cannot prompt |

Guard TUI-only features with `ctx.mode === "tui"`; guard dialogs and notifications with `ctx.hasUI`.
