# Native MCP and codemode

Sources: https://pi.dev/docs/latest/mcp, https://pi.dev/docs/latest/cli, and Pi 0.99.2 `packages/mcp` / built-in extension source.

Pi **0.99.2** includes MCP, codemode, and tool search as built-in extensions. These are separate from the optional `pi-mcp-adapter` package; its configuration and commands are in `pi-mcp-adapter.md`.

## Configure native servers

```bash
pi mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem .
pi mcp list
```

Commands mutate global `~/.pi/agent/mcp.json` by default; `--local` / `-l` uses trusted project `.pi/mcp.json`. A project entry replaces the same-named global entry. The example installs/executes a third-party server and is illustrative; inspect/pin it before deployment.

```json
{
  "mcpServers": {
    "docs": {
      "url": "https://mcp.example.com/mcp",
      "headers": { "Authorization": "Bearer ${DOCS_TOKEN}" },
      "description": "Search and read documentation",
      "exposure": "codemode",
      "timeout": 60
    }
  }
}
```

Use `command` plus argv `args`, optional `env` and `cwd` for stdio. Use `url`, optional `headers`, `oauth`, or provider-token `auth` for HTTP. `type` may be `stdio`, `http`, or `streamable-http`; **legacy SSE is rejected**. `timeout` is seconds, default 60; progress resets it. `enabled: false` disables a native server. This differs from adapter `disabled: true` and `requestTimeoutMs`.

`env`/header values support `${VAR}` interpolation and whole-value `!command`. `command` itself is an executable, never a shell command string. Avoid putting credentials in project files.

`/mcp` manages connections and exposure. CLI `pi mcp add|remove|list|login|logout` uses the built-in implementation without loading extensions. `pi mcp list` connects enabled servers and exits 1 for invalid entries or failures. Run `/reload` after external config edits.

## Authentication

HTTP OAuth runs through `/mcp login <server>` or `pi mcp login <server>` and stores refreshable credentials in `~/.pi/agent/mcp-auth.json`. Remote users can paste the final redirect URL. Registered clients use `oauth.clientId`, optional `clientSecret`, `callbackPort`/`callbackUrl`, `scope`, and `clientName`; the callback must be an HTTP loopback URL matching the server registration. An explicit Authorization header takes precedence over automatic OAuth.

Pi 0.99.2 also accepts `auth: { provider: "<provider>" }` to read a provider's current `/login` token on each request. It is allowed only in global config or extension registration, requires HTTPS except loopback, and should only target a service authorized to receive that provider credential. OAuth flows were not executed in this audit.

## Exposure and execution

Default `codemode` exposure hides definitions until scripts discover them. `deferred` uses `tool_search`; `direct` declares tools immediately; `hidden` makes them unreachable. `codemode-deferred` aliases `codemode`. `toolExposure` overrides individual original names or `*` patterns: exact match wins, otherwise first matching pattern.

Names are `mcp__<server>__<tool>` with non-alphanumeric/non-underscore characters normalized to `_`. Same-server tool collisions gain hash suffixes; server names differing only in `-` versus `_` are rejected. Discover actual names instead of guessing.

Enabled servers connect in the background at session start. First prompts wait only for direct-tool servers (up to 10s); discovery/tool use waits for the required servers. The model sees a compact `mcp_servers` system-prompt section; codemode's tool description does not expand as these servers connect.

Illustrative codemode body:

```javascript
const hits = await searchTools("documentation", { limit: 5 });
text(hits);
text(await describeNamespace("mcp__docs"));
```

Use `tools.<discovered_name>(args)` after inspecting its declaration. Scripts run in QuickJS and have `ALL_TOOLS`, `searchTools`, `describeTool`, `describeNamespace`, `text`, `image`, `store`/`load`, `exit`, and a top-level `return`. Optional first line: `// @options: {"max_output_tokens": 2000, "timeout_ms": 60000}`. No deadline is set by default. `store` persists JSON only after a successful script and follows the session branch.

Enable codemode without MCP through `defaultTools: ["+codemode"]`. CLI `--tools` replaces the complete list and does not accept `+`/`-` deltas. `codemode.mode: "only"` hides other declarations while keeping callable tools. QuickJS limits the script environment; underlying tools still have the Pi process's permissions.

MCP script calls resolve to a full `CallToolResult`, including `content`, `structuredContent`, and `isError`. An error result resolves with `isError` rather than necessarily throwing. Direct model output truncates text over 20KB and includes a spill path; scripts receive the complete result. Nested calls pass Pi validation/permission hooks and report `parentToolCallId`.

## Resources and SDK

`list_mcp_resources({ server?, cursor? })`, `list_mcp_resource_templates(...)`, and `read_mcp_resource({ server, uri })` cover resources. With `server`, listing returns one page and `nextCursor`; without it, Pi collects every server. MCP App UI resources are omitted because native Pi does not render them. Tool calls are not retried automatically; resource reads/listing retry once on transient HTTP failures.

Extensions register native servers with `pi.registerMcpServer(name, config)` and withdraw with `pi.unregisterMcpServer(name)`. File config wins name conflicts. SDK hosts must explicitly add `createMcpExtension`, `createCodemodeExtension`, and `createToolSearchExtension` and bind extensions. Emit `session_shutdown` before bare-session disposal (or await runtime disposal) to close transports; see `sdk.md`.

An extension claiming `/mcp` replaces native session MCP. Current adapter 4.0 detects native Pi and uses `/mcp-adapter` instead, so both can coexist with separate files. Never duplicate one server in both owners' config unless two connections are intended.
