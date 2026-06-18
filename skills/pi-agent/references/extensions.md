# Extensions

Source: https://pi.dev/docs/latest/extensions

Extensions are TypeScript modules that extend Pi. They can register tools, commands, shortcuts, flags, custom providers, UI, event handlers, and persistent session entries.

## Locations

- `~/.pi/agent/extensions/*.ts`
- `~/.pi/agent/extensions/*/index.ts`
- `.pi/extensions/*.ts`
- `.pi/extensions/*/index.ts`
- Paths from settings or packages

Project-local extensions load only after project trust. Use `pi -e ./my-extension.ts` for quick tests. Auto-discovered extensions can be hot-reloaded with `/reload`.

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

- `@earendil-works/pi-coding-agent`: extension types and APIs.
- `typebox`: schemas for tool parameters.
- `@earendil-works/pi-ai`: AI utilities.
- `@earendil-works/pi-tui`: TUI components.

Runtime dependencies for distributed packages belong in `dependencies`; package installs use production installs by default.

## Event Flow

Startup: `project_trust`, `session_start`, `resources_discover`.

Prompt: extension commands, `input`, skill/template expansion, `before_agent_start`, `agent_start`, message events, turn events, provider request/response hooks, tool events, `agent_end`.

Session changes: `session_before_switch`, `session_shutdown`, `session_start`, `resources_discover`. Fork/clone use `session_before_fork`.

Compaction/tree: `session_before_compact`, `session_compact`, `session_before_tree`, `session_tree`.

Model changes: `model_select`, `thinking_level_select`.

Shutdown: `session_shutdown`.

## High-Value Hooks

- `project_trust`: user/global or CLI extensions can decide project trust.
- `resources_discover`: contribute skill, prompt, and theme paths.
- `before_agent_start`: inject custom messages or modify the system prompt.
- `context`: non-destructively modify messages before each LLM call.
- `before_provider_request`: inspect/replace provider payload for debugging or compatibility.
- `after_provider_response`: inspect status/headers before streaming body is consumed.
- `tool_call`: block or mutate tool inputs before execution.
- `tool_result`: modify tool results.
- `message_end`: replace finalized message while preserving role.

## Runtime Notes

Extension factories may be async; Pi awaits them before startup continues. Use async factories for startup-only work such as dynamic model discovery. In RPC or JSON/print mode, guard TUI-specific UI with `ctx.mode === "tui"` and check `ctx.hasUI` before prompting.
