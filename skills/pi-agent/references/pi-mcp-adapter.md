# pi-mcp-adapter Package

Source: https://pi.dev/packages/pi-mcp-adapter

MCP adapter extension for Pi. Instead of loading hundreds of MCP tool definitions upfront (10,000+ tokens per server), it exposes one `mcp` proxy tool (~200 tokens) that discovers and calls tools on demand. Servers connect lazily and disconnect when idle.

```bash
pi install npm:pi-mcp-adapter
```

Restart Pi after installation.

## Configuration Files

Precedence (highest to lowest):

1. `~/.config/mcp/mcp.json` — user-global shared config
2. `<Pi agent dir>/mcp.json` — Pi global override
3. `.mcp.json` — project-local shared config
4. `.pi/mcp.json` — Pi project override

```json
{
  "mcpServers": {
    "chrome-devtools": { "command": "npx", "args": ["-y", "chrome-devtools-mcp@latest"] }
  }
}
```

Import existing configs with `"imports": ["cursor", "claude-code", "claude-desktop"]` (also `vscode`, `windsurf`, `codex`).

## Server Options

| Field | Description |
|---|---|
| `command`, `args`, `env`, `cwd` | stdio transport; `env`/`cwd` support `${VAR}`, `$env:VAR`, `~` |
| `url`, `headers` | HTTP endpoint (StreamableHTTP with SSE fallback); headers support interpolation |
| `auth` | `"bearer"` or `"oauth"` |
| `oauth` | `{ grantType, clientId, clientSecret, scope, redirectUri }` |
| `lifecycle` | `"lazy"` (default: connect on first call, idle disconnect), `"eager"` (connect at startup), `"keep-alive"` (startup + health checks + auto-reconnect) |
| `idleTimeout` | Minutes before idle disconnect (default 10) |
| `exposeResources` | Expose MCP resources as tools (default true) |
| `directTools` | `true`, `string[]`, or `false` — register tools directly instead of via proxy |
| `excludeTools` | Tool names to hide |
| `debug` | Show server stderr (default false) |

Global `settings` block: `toolPrefix`, `idleTimeout`, `directTools`, `disableProxyTool`, `autoAuth`, `sampling`, `samplingAutoApprove`, `elicitation`, `elicitationAutoOpenUrls`.

Direct tools cost 150–300 tokens each; use for 5–20 targeted tools, the proxy for everything else:

```json
{ "mcpServers": { "github": { "directTools": ["search_repositories", "get_file_contents"] } } }
```

## Proxy Tool API

```javascript
mcp({ })                                            // list servers
mcp({ server: "name" })                             // server details
mcp({ search: "screenshot navigate" })              // search tools
mcp({ describe: "tool_name" })                      // tool description
mcp({ tool: "chrome_devtools_take_screenshot", args: '{"format": "png"}' })  // call; args is a JSON string
mcp({ connect: "server-name" })
mcp({ action: "ui-messages" })                      // retrieve MCP UI messages
```

## CLI Commands

```
/mcp                    # interactive panel and first-run setup
/mcp setup              # guided imports and config
/mcp tools              # list all available tools
/mcp reconnect [server]
/mcp logout <server>    # clear OAuth credentials
/mcp-auth [server]      # OAuth setup picker
```

## Behavior Notes

Tool metadata is cached to disk so search/describe work offline. npx-based servers resolve to direct binaries to skip npm overhead. MCP UI–capable tools open in a native macOS window via Glimpse (if installed) or a browser fallback; UI message types `prompt`, `intent`, `notify`, `message` are retrievable via `mcp({ action: "ui-messages" })`.

Limitations: no cross-session server sharing; MCP sampling is text-only (context, tools, audio, images rejected).

Subagents (`pi-subagents`) only receive direct MCP tools when listed in their `tools:` frontmatter with an `mcp:` prefix — see `references/pi-subagents.md`.
