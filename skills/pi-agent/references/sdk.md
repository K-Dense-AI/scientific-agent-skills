# SDK

Source: https://pi.dev/docs/latest/sdk

Install the main package; the SDK is included:

```bash
npm install @earendil-works/pi-coding-agent
```

Use the SDK to embed Pi in apps, build custom UIs, automate workflows, spawn sub-agents, test behavior, or customize tools/resources in process.

## Quick Start

```ts
import { AuthStorage, createAgentSession, ModelRegistry, SessionManager } from "@earendil-works/pi-coding-agent";

const authStorage = AuthStorage.create();
const modelRegistry = ModelRegistry.create(authStorage);

const { session } = await createAgentSession({
  sessionManager: SessionManager.inMemory(),
  authStorage,
  modelRegistry,
});

session.subscribe((event) => {
  if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
    process.stdout.write(event.assistantMessageEvent.delta);
  }
});

await session.prompt("What files are in the current directory?");
```

## `AgentSession`

Core methods: `prompt`, `steer`, `followUp`, `subscribe`, `setModel`, `setThinkingLevel`, `cycleModel`, `cycleThinkingLevel`, `navigateTree`, `compact`, `abortCompaction`, `abort`, and `dispose`.

State: `sessionFile`, `sessionId`, `agent`, `model`, `thinkingLevel`, `messages`, `isStreaming`.

Session replacement (`new`, `resume`, `fork`, import) belongs to `AgentSessionRuntime`, not `AgentSession`.

## Runtime API

Use `createAgentSessionRuntime()` when replacing the active session and rebuilding cwd-bound services. After `runtime.newSession()`, `runtime.switchSession()`, or `runtime.fork()`, `runtime.session` changes; re-subscribe to events and re-bind extensions if you manage them manually.

## Prompting and Queueing

`PromptOptions` supports `expandPromptTemplates`, `images`, `streamingBehavior` (`steer` or `followUp`), `source`, and `preflightResult`.

During streaming, `prompt()` without `streamingBehavior` throws. Use `session.steer()` for steering delivered after current assistant turn tool calls, or `session.followUp()` for after all work finishes. Extension commands execute immediately and cannot be queued by `steer`/`followUp`.

## Events

Subscribe to `AgentSessionEvent` for `message_update` text/thinking deltas, tool execution events, message lifecycle, agent lifecycle, turn lifecycle, queue updates, compaction, and retry events.

## Models and Auth

Use `AuthStorage.create()` and `ModelRegistry.create(authStorage)`. API key priority: runtime overrides, `auth.json`, environment variables, then custom provider fallback from `models.json`.

Use `getModel(provider, id)` for built-in model lookup and `modelRegistry.find(provider, id)` for built-in plus custom. `modelRegistry.getAvailable()` checks auth availability.

## Tools

Built-in names: `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`. Defaults: `read`, `bash`, `edit`, `write`. `tools` allowlists tools; `excludeTools` disables specific tools. `noTools: "all"` disables all tools; `noTools: "builtin"` disables built-ins but keeps custom/extension tools.

The `edit` tool returns `details.diff` for TUI display and `details.patch` as standard unified patch for SDK consumers.

Define custom tools with `defineTool()` and pass `customTools`; include custom names in `tools` if using an allowlist.

## Resource Loading

`DefaultResourceLoader` discovers extensions, skills, prompts, themes, and context files. It supports additional extension paths, inline extension factories, overrides for skills/prompts/context, and a shared event bus.

`cwd` controls project discovery and tool path resolution. `agentDir` controls global resources such as `~/.pi/agent`.

## Sessions and Settings

Use `SessionManager.inMemory()`, `create()`, `continueRecent()`, `open()`, `list()`, and `listAll()`. Tree APIs include `getEntries`, `getTree`, `getPath`, `getLeafEntry`, `getEntry`, `getChildren`, `appendLabelChange`, `branch`, `branchWithSummary`, and `createBranchedSession`.

`SettingsManager.create()` loads global plus project settings; `SettingsManager.inMemory()` is useful for tests. Setters persist asynchronously; call `flush()` for durability and `drainErrors()` to report write errors.

## Run Modes

The SDK exports run helpers: `InteractiveMode`, `runPrintMode`, and `runRpcMode`. Use these when building custom launchers while reusing Pi's mode implementations.

## SDK vs RPC

Prefer SDK when you want type safety, same Node.js process, direct state access, or programmatic tools/extensions. Prefer RPC when integrating from another language, needing process isolation, or building a language-agnostic client.

## Important Exports

`createAgentSession`, `createAgentSessionRuntime`, `AgentSessionRuntime`, `AuthStorage`, `ModelRegistry`, `DefaultResourceLoader`, `defineTool`, `getAgentDir`, `SessionManager`, `SettingsManager`, tool factories, and types for options, results, extensions, tools, skills, and prompt templates.
