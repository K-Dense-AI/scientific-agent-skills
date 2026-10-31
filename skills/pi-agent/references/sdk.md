# SDK

Source: https://pi.dev/docs/latest/sdk

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

The SDK ships in the main package:

```bash
npm install @earendil-works/pi-coding-agent
```

Use it to embed Pi, build custom UIs, automate workflows, spawn sub-agents, test behavior, or customize tools/resources in process.

## Quick Start

```ts
import { createAgentSession, ModelRuntime, SessionManager } from "@earendil-works/pi-coding-agent";

const modelRuntime = await ModelRuntime.create();
const { session } = await createAgentSession({
  sessionManager: SessionManager.inMemory(),
  modelRuntime,
});

session.subscribe((event) => {
  if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
    process.stdout.write(event.assistantMessageEvent.delta);
  }
});

try {
  await session.prompt("What files are in the current directory?");
} finally {
  await session.extensionRunner.emit({ type: "session_shutdown", reason: "quit" });
  session.dispose();
}
```

`createAgentSession()` returns `{ session, extensionsResult, modelFallbackMessage? }` and uses `DefaultResourceLoader` when no `resourceLoader` is passed.

## `AgentSession`

Methods: `prompt(text, options?)`, `steer(text)`, `followUp(text)`, `subscribe(listener)` (returns unsubscribe), `setModel`, `setThinkingLevel`, `cycleModel`, `cycleThinkingLevel`, `navigateTree(targetId, { summarize, customInstructions, replaceInstructions, label })`, `compact(customInstructions?)`, `abortCompaction()`, `abort()`, `dispose()`.

State: `sessionFile`, `sessionId`, `agent`, `model`, `thinkingLevel`, `messages`, `isStreaming`.

`session.agent.state` exposes `messages`, `model`, `thinkingLevel`, `systemPrompt`, `tools`, `streamingMessage`, `errorMessage`; `SessionManager` is authoritative for finalized context: assigning `agent.state.messages` does not replace persisted history. Restore external history with `SessionManager.inMemory(cwd, options, entries)` before creating the session. Use `session.waitForIdle()` to wait for the full session run.

Session replacement (new/resume/fork/clone/import) lives on `AgentSessionRuntime`, not `AgentSession`.

## Runtime API

```ts
const createRuntime: CreateAgentSessionRuntimeFactory = async ({ cwd, sessionManager, sessionStartEvent }) => {
  const services = await createAgentSessionServices({ cwd });
  return {
    ...(await createAgentSessionFromServices({ services, sessionManager, sessionStartEvent })),
    services,
    diagnostics: services.diagnostics,
  };
};

const runtime = await createAgentSessionRuntime(createRuntime, {
  cwd: process.cwd(),
  agentDir: getAgentDir(),
  sessionManager: SessionManager.create(process.cwd()),
});
```

`await runtime.dispose()` emits extension shutdown and releases the active session. `AgentSessionRuntime` owns `newSession()`, `switchSession(path)`, `fork(entryId)`, clone via `fork(entryId, { position: "at" })`, and `importFromJsonl()`. `runtime.session` changes after each, so re-subscribe to events and call `runtime.session.bindExtensions(...)` again if you manage extensions manually. Creation returns `runtime.diagnostics`; failures throw.

## Prompting and Queueing

```ts
interface PromptOptions {
  expandPromptTemplates?: boolean;
  images?: ImageContent[];
  streamingBehavior?: "steer" | "followUp";
  source?: InputSource;
  preflightResult?: (disposition: "started" | "queued" | "handled") => void;
}
```

`preflightResult` is an internal RPC hook called only after acceptance with a disposition string. It is not called when preflight rejects; it no longer receives a boolean. Failures after acceptance surface through events and messages. `prompt()` resolves only after the full accepted run finishes, including retries.

Extension commands execute immediately even during streaming. File-based prompt templates expand before sending or queueing. Calling `prompt()` while streaming without `streamingBehavior` throws — use `session.steer()` (delivered after the current assistant turn's tool calls) or `session.followUp()` (after all work finishes). Both pass through extension input handlers, expand templates, reject extension commands, and return `"queued"` or `"handled"`.

## Events

`message_update` (with `assistantMessageEvent` deltas such as `text_delta`, `thinking_delta`), `tool_execution_start` / `_update` / `_end`, `message_start` / `message_end`, `agent_start` / `agent_end` / `agent_settled`, `entry_appended`, `session_info_changed`, `thinking_level_changed`, `turn_start` / `turn_end`, `queue_update`, `compaction_start` / `compaction_end`, `auto_retry_start` / `auto_retry_end`, `summarization_retry_scheduled` / `summarization_retry_attempt_start` / `summarization_retry_finished`.

## Models and Auth

`ModelRuntime` replaces the older `AuthStorage` + `ModelRegistry` pair (a synchronous `ModelRegistry` facade remains exported for extension compatibility).

```ts
const modelRuntime = await ModelRuntime.create({ authPath, modelsPath, credentials });
modelRuntime.getModel(provider, id);        // built-ins + models.json, no auth check
await modelRuntime.getAvailable();          // only models with valid auth
await modelRuntime.checkAuth(providerId);
modelRuntime.getProviders();                // provider.auth methods and status
await modelRuntime.setRuntimeApiKey(provider, key); // not persisted
```

Credential priority: runtime overrides → `auth.json` → configured `models.json` API key → provider environment/ambient auth (native provider extensions can define their own resolution). `getModel(provider, id)` from `@earendil-works/pi-ai/compat` looks up built-ins only. Inject any pi-ai `CredentialStore` (for example `InMemoryCredentialStore`) via `credentials`.

### Catalog Refresh and Deadlines

`create()` restores cached catalogs but does not refresh them from `pi.dev` by default. Opt in with `ModelRuntime.create({ allowModelNetwork: true, modelRefreshTimeoutMs: 15_000 })`. Remote catalogs persist to `~/.pi/agent/models-store.json` (override with `modelsStorePath`, or inject `modelsStore`); refreshes are throttled to once per provider every four hours unless forced, and `PI_OFFLINE` disables model network access entirely.

Public model/auth operations and `ModelRuntime.create({ signal })` accept optional abort signals and are unbounded when omitted — SDK applications own deadline policy:

```ts
const result = await modelRuntime.refresh({ providers: ["anthropic"], signal: AbortSignal.timeout(15_000) });
if (result.aborted) console.warn("Catalog refresh timed out; using cached models");
for (const [providerId, error] of result.errors) console.warn(providerId, error);
```

Force an immediate refresh with `await modelRuntime.refresh({ allowNetwork: true, force: true, signal })`. Each `refresh()` starts a new provider generation, so it does not queue behind a stalled refresh and stale generations cannot publish afterward. A failed or timed-out refresh never undoes a successful credential operation.

`login()`, `logout()`, `setRuntimeApiKey()`, and `removeRuntimeApiKey()` are async and resolve once the affected provider's cached/built-in catalog, composition, and availability snapshot are locally consistent; they do not wait for remote freshness. If credentials committed but local synchronization failed, they reject with the exported `CredentialSynchronizationError` — inspect `providerId`, `operation`, `credential`, and `cause` rather than blindly retrying the credential mutation.

To match CLI parsing, use `resolveCliModel({ cliModel, modelRuntime })` (uses all registered models so `--api-key` first-run flows resolve before stored auth exists) and `resolveModelScopeWithDiagnostics(patterns, modelRuntime)` (matches `--models`/`enabledModels` semantics and returns warnings instead of printing).

Session options also accept `model`, `thinkingLevel` (`off`…`max`), and `scopedModels: [{ model, thinkingLevel }]` for Ctrl+P cycling. With no model: restore from session, then settings default, then first available.

## Tools

Built-ins: `read`, `bash`, `powershell` (native Windows), `edit`, `write`, `grep`, `find`, `ls`. Defaults: `read`, `bash`, `edit`, `write`. `tools` allowlists, `excludeTools` disables specific names after the allowlist, `noTools: "all"` disables everything, `noTools: "builtin"` keeps extension/custom tools. The `edit` tool returns `details.diff` for the TUI and `details.patch` as a standard unified patch for SDK consumers.

Define custom tools with `defineTool()` and pass them as `customTools`; include their names in `tools` if you use an allowlist. Tool factories are exported too: `createCodingTools`, `createReadOnlyTools`, `createReadTool`, `createBashTool`, `createPowerShellTool`, `createEditTool`, `createWriteTool`, `createGrepTool`, `createFindTool`, `createLsTool`.

Passing a custom `cwd` makes `createAgentSession()` build the selected built-in tools for that directory.

## Resource Loading

`DefaultResourceLoader` discovers extensions, skills, prompts, themes, and context files. Options: `cwd`, `agentDir`, `additionalExtensionPaths`, `extensionFactories` (bare functions or `InlineExtension { name, factory }` so the startup list shows `<inline:my-provider>` instead of `<inline:1>`), `settingsManager`, `systemPromptOverride`, `skillsOverride`, `promptsOverride`, `agentsFilesOverride`, `eventBus` (from `createEventBus()`). Call `await loader.reload()`, then read `getExtensions()`, `getSkills()`, `getPrompts()`, `getThemes()`, `getAgentsFiles().agentsFiles`.

`cwd` drives project discovery (`.pi/extensions`, `.pi/skills`, `.agents/skills` up to the git root, `.pi/prompts`, `AGENTS.md` walk-up, session naming); `agentDir` drives global resources (`extensions/`, `skills/`, `~/.agents/skills/`, `prompts/`, `AGENTS.md`, `settings.json`, `models.json`, `auth.json`, `sessions/`). With a custom `ResourceLoader`, `cwd`/`agentDir` still influence session naming and tool path resolution but no longer control discovery.

## Sessions and Settings

`SessionManager.inMemory(cwd?)`, `create(cwd)`, `continueRecent(cwd)`, `open(path)`, `list(cwd)`, `listAll(onProgress?)`. Tree API: `getEntries`, `getTree`, `getBranch`, `getLeafEntry`, `getEntry`, `getChildren`, `getLabel`, `appendLabelChange`, `branch`, `branchWithSummary`, `createBranchedSession`. Full API in `references/session-format.md`.

`SettingsManager.create(cwd?, agentDir?)` merges global plus project settings; `SettingsManager.inMemory(settings?)` avoids file I/O for tests. `applyOverrides({ compaction, retry, ... })` layers overrides. Getters/setters are synchronous for in-memory state and enqueue writes asynchronously — call `await flush()` for a durability boundary and `drainErrors()` to report write errors yourself (the manager never prints them).

## Run Modes

`InteractiveMode` (full TUI), `runPrintMode(runtime, { mode: "text", initialMessage, initialImages, messages })`, `runRpcMode(runtime)`. All take an `AgentSessionRuntime`. `InteractiveMode` options include `migratedProviders`, `modelFallbackMessage`, `initialMessage`, `initialImages`, `initialMessages`.

## SDK vs RPC

Prefer the SDK for type safety, same-process integration, direct state access, or programmatic tools/extensions. Prefer RPC for other languages, process isolation, or language-agnostic clients.

## Important Exports

`createAgentSession`, `createAgentSessionRuntime`, `AgentSessionRuntime`, `createAgentSessionServices`, `createAgentSessionFromServices`, `ModelRuntime`, `ModelRegistry`, `CredentialSynchronizationError`, `resolveCliModel`, `resolveModelScopeWithDiagnostics`, `DefaultResourceLoader`, `ResourceLoader` type, `createEventBus`, `CONFIG_DIR_NAME`, `defineTool`, `getAgentDir`, `getPackageDir`, `getReadmePath`, `getDocsPath`, `getExamplesPath`, `SessionManager`, `SettingsManager`, the tool factories above, `InteractiveMode`, `runPrintMode`, `runRpcMode`, and types for options, results, extensions (`ExtensionAPI`, `ExtensionFactory`, `InlineExtension`), tools, skills, and prompt templates.


## Native MCP and codemode in SDK hosts

SDK sessions do not load the CLI's built-in extensions automatically. Add `createCodemodeExtension()`, `createToolSearchExtension()`, and `createMcpExtension()` to a `DefaultResourceLoader` through `extensionFactories`, enable the tools through `defaultTools` or MCP exposure, then call `await session.bindExtensions({})` so `session_start` connects MCP servers. For a bare `AgentSession`, close extension-owned subprocesses before disposing: `await session.extensionRunner.emit({ type: "session_shutdown", reason: "quit" }); session.dispose();`. `session.dispose()` alone only disconnects session resources and did not close the MCP fixture in the local check. A host using `AgentSessionRuntime` should instead `await runtime.dispose()`. Follow the upstream [SDK example](https://github.com/earendil-works/pi/blob/v0.99.2/packages/coding-agent/examples/sdk/14-codemode-mcp.ts).

`ModelRuntime` now also exposes `getModelsOfType`, `getModelOfType`, `getAvailableOfType`, `getAllModels`, `getAllAvailable`, `generateImages`, and `classify`. Chat and image entries may share an upstream ID; select by operation type. These operations resolve credentials through the runtime. They may incur provider charges and were not called against live providers in this review.
