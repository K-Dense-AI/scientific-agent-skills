# pi-mcp-adapter Package

Source: https://pi.dev/packages/pi-mcp-adapter

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

MCP adapter extension for Pi. Instead of loading hundreds of tool definitions upfront, it exposes one `mcp` proxy tool (~200 tokens) that discovers and calls tools on demand. Servers connect lazily and disconnect when idle; tool metadata is cached to disk so search/describe work offline.

```bash
pi install npm:pi-mcp-adapter
```

Version 4.0.0 was reviewed with Pi 0.99.2. Restart Pi after installation. Native Pi owns `/mcp` and `mcp.json`; the adapter uses `/mcp-adapter` and `mcp-adapter.json`. `/mcp` is an adapter alias only without native MCP. On first run the adapter reads standard MCP files automatically. If you only have host-specific configs (Cursor, Claude Code, Codex, …), run `/mcp-adapter setup` to adopt them, or `pi-mcp-adapter init` to scan and add compatibility imports to the Pi agent dir config.

## Configuration Files

Precedence, lowest to highest:

1. `~/.config/mcp/mcp.json` — user-global shared
2. `~/.agents/mcp.json` — user-global tool-agnostic
3. `~/.agents/mcp/mcp.json` — user-global tool-agnostic
4. `<Pi agent dir>/mcp-adapter.json` — Adapter global override (`~/.pi/agent/mcp-adapter.json`, or `$PI_CODING_AGENT_DIR/mcp-adapter.json`)
5. `.mcp.json` — project-local shared (preferred for projects)
6. `.pi/mcp-adapter.json` — Adapter project override

```json
{
  "mcpServers": {
    "chrome-devtools": { "command": "npx", "args": ["-y", "chrome-devtools-mcp@1.6.0"] }
  }
}
```

Host-specific configs are detected but **not** loaded automatically, and the normal `/mcp-adapter` panel does not scan them while `settings.hostConfigDiscovery` is `"off"` (the default). Opt in with `"on"` (or `pi-mcp-adapter init --discover-host-configs`); `"prompt"` detects without activating. Host configs sit below every shared and Pi-owned source.

Import specific host formats explicitly with `"imports": ["cursor", "claude-code", "claude-desktop", "opencode", "vscode", "windsurf", "codex"]`.

### Agent Plugins

List [Agent Plugins](https://agent-plugins.org/) package directories in `settings.agentPluginPaths` to load their MCP servers:

```json
{ "settings": { "agentPluginPaths": ["./plugins/acme-tools"] }, "mcpServers": {} }
```

Each directory needs a valid Agent Plugins 1.0 `plugin.json`; a root `mcp.json` there contributes `mcpServers` entries prefixed `<plugin>__<server>`. The loader uses the transport declared by each server `type` and skips invalid entries without blocking others. For stdio plugin servers, `${PLUGIN_ROOT}` and `${PLUGIN_DATA}` expand only in `args`, `env`, and `cwd`; both are set for the child process and plugin data is stored under the Pi agent directory. The adapter reads shared `.mcp.json`/`~/.config/mcp/mcp.json` plus adapter-owned overrides. It never reads native Pi global/project `mcp.json`.

`/mcp-adapter disable <server>` / `/mcp-adapter enable <server>` persist only the `disabled` field into `.pi/mcp-adapter.json` (never rewriting the source file or copying credentials); run `/reload` to apply. The manual equivalent is `{ "disabled": true }` in any MCP config.

### SDK Configuration

```ts
import { createMcpAdapter } from "pi-mcp-adapter";
const extension = createMcpAdapter({ config: { mcpServers: { docs: { url: "https://mcp.example.com/mcp", lifecycle: "eager" } } } });
```

A supplied `config` is a complete isolated snapshot — never merged with files, imports, or `--mcp-config`, and cloned per adapter/session. Status, reconnect, explicit `/mcp-auth <server>`, proxy calls, and direct tools still work; setup and no-argument auth/status panels report the limitation. With `configPath` and no `config`, normal file merging applies and that path outranks argv and `--mcp-config`. The package ships TypeScript source, so standalone Node processes need a TS-capable loader (e.g. `node --import tsx`).

OAuth credentials are stored in the OS credential store keyed by configured server name, with URL binding so credentials cannot be reused for a different server URL. `settings.oauthDir` / `MCP_OAUTH_DIR` are legacy plaintext `tokens.json` import locations only.

Cooperating Pi extensions can reuse URL-bound tokens through the public `pi-mcp-adapter/oauth` subpath (`getMcpOAuthTokensForUrl(server, url)`, `updateMcpOAuthTokensForUrl(server, url, tokens)`, plus a status helper). The async read path applies the adapter's refresh logic first. It exposes token read/update only — never client registration secrets, PKCE verifiers, or OAuth state — and keeps secure-store storage, URL binding, refresh persistence, chunk handling, legacy import, and fail-closed credential-store errors.

## Server Options

| Field | Description |
|---|---|
| `command`, `args` | stdio transport; mutually exclusive with `url` and `socket` |
| `socket` | `rmcp-mux` Unix socket path; supports `${VAR}`, `$env:VAR`, `~` |
| `env`, `cwd` | Interpolation supported; an `env` value starting with `!` runs a command at connect (`!!` escapes) |
| `url`, `headers` | StreamableHTTP with SSE fallback; interpolation supported, missing URL vars fail before any request |
| `auth` | `"bearer"` or `"oauth"` |
| `oauth.*` | `grantType` (`authorization_code` default, or `client_credentials`), `clientId` (MCP 2026 prefers pre-registered clients or Client ID Metadata Documents; Dynamic Client Registration is the fallback when omitted), `clientSecret`, `scope`, `redirectUri` (exact localhost callback for pre-registered clients), `clientName`, `clientUri` (defaults to the host manifest's `piConfig.clientUri`, omitted under a rebranded host), `logoUri` (absolute `http(s)` URL, RFC 7591 `logo_uri`), `authorizationParams` (extra authorization-URL parameters; flow-owned ones such as `client_id`, `redirect_uri`, `scope`, `state`, `code_challenge`, `response_type`, `resource` cannot be overridden), `skipIssuerMetadataValidation` |
| `bearerToken` / `bearerTokenEnv` | Token or env var name; interpolation and `!command` supported |
| `lifecycle` | `"lazy"` (default), `"eager"`, `"keep-alive"`, `"lazy-keep-alive"` |
| `idleTimeout` | Minutes before idle disconnect (overrides global) |
| `requestTimeoutMs` | Per-server request timeout; omitted or `<= 0` uses the MCP SDK default |
| `protocolVersion` | `"legacy"` (default), `"auto"`, or `"2026-07-28"` — modern negotiation is opt-in |
| `exposeResources` | Expose MCP resources as tools (default `true`) |
| `directTools` | `true`, `string[]`, `"search"`, or `false` |
| `toolPrefix` | Per-server override of the global `toolPrefix` |
| `includeTools` / `excludeTools` | Names or glob patterns; `excludeTools` applies after `includeTools` |
| `searchKeywords` | `{ "tool-or-glob": ["keyword", …] }` extra keywords boosting `mcp({ search })` ranking; never shown to the model |
| `approveTools` | `true`, `"destructive"`, or glob array requiring approval before calls (overrides the global setting) |
| `debug` | Show server stderr (default `false`) |
| `trace` | Metadata-only JSONL protocol tracing for this server |
| `disabled` | Keep visible in config/status but block connections, auth, tools, resources (only literal `true`) |

Secret values in `headers`, `bearerToken`, `oauth.clientSecret`, and stdio `env` may use a leading `!command` resolved at connect/auth time: stdin and stderr suppressed, stdout capped at 1 MiB and trimmed, 10-second limit, non-empty output required. Commands never run during discovery, merging, previewing, hashing, or rendering config.

`oauth.skipIssuerMetadataValidation: true` disables the RFC 8414 issuer echo check for one server. It weakens OAuth mix-up protection — use it only for a known-misconfigured internal server while its metadata is being fixed, never for public or untrusted servers.

**Protocol version negotiation** — the default `"legacy"` uses the classic MCP initialize sequence with no `server/discover` or 2026 headers, preserving compatibility with deployed 2025-era servers. `"auto"` probes for MCP 2026-07-28 and conservatively falls back to the classic handshake on legacy evidence; set it for Cloudflare Workers `createMcpHandler` and other MCP SDK v2 stateless servers. For stdio servers, `"auto"` probes with a short-lived sibling process before starting the session process, so each fresh connection adds one spawn and may wait out the request timeout; explicit Unix sockets probe in place. HTTP auto negotiation uses the real Streamable HTTP connection and falls back to legacy SSE only on definitive rejection (404/405/406/415) — never on auth failures, cancellation, timeouts, or server errors. `"2026-07-28"` pins that revision with no legacy or SSE fallback. Strict OAuth issuer validation applies in every mode. Adapter-level roots support, standard MCP logging presentation, and protocol cache-hint config are not yet implemented.

**Lifecycle modes** — `lazy`: connect on first tool call, disconnect after idle, cached metadata keeps search working. `eager`: connect at startup, no auto-reconnect, no idle timeout unless set. `keep-alive`: connect at startup with health checks and auto-reconnect. `lazy-keep-alive`: connect on first use, then stay resident with auto-reconnect. Any enabled `eager`/`keep-alive` server also triggers initialization at extension load, supporting hosts that never emit `session_start`.

**rmcp-mux** — point `socket` at an [`rmcp-mux`](https://github.com/VetCoders/rmcp-mux) service socket to share one stdio server across Pi sessions. The adapter owns only its client socket; the mux owns the upstream process, routing, restart policy, and socket permissions. A socket is an explicit trusted local endpoint.

## Global Settings

```json
{ "settings": { "toolPrefix": "server", "idleTimeout": 10, "requestTimeoutMs": 30000, "trace": { "enabled": true } } }
```

`toolPrefix` (`"server"` default, `"short"` strips a `-mcp` suffix, `"none"`, `"mcp"` prefixes `mcp__`; per-server `toolPrefix` overrides it), `idleTimeout` (minutes, default 10, `0` disables), `requestTimeoutMs`, `showStatusIcon` (default `true`), `mcpFooterStatus` (`"full"` default, `"compact"`, `"off"`), `toolResultRendering` (`"compact"` default self-rendered rows, or `"boxed"` for the legacy Pi tool row), `collapsedResultLines` (`1`–`3`; defaults `1` compact / `3` boxed), `notifyOnStartupConnect` (default `true`; `false` suppresses routine connect notices but keeps errors and auth warnings), `hostConfigDiscovery`, `agentPluginPaths`, `approveTools` (`"destructive"` asks for unknown/destructive tools), `oauthDir`, `directTools` (global default, default `false`), `freezeDirectTools` (default `false`), `scriptMode` (default `false`; registers the MCP-only `mcpScript` plain-JavaScript tool), `disableProxyTool`, `autoAuth` (default `false`), `sampling` (default `true` when UI approval is available; honors `modelPreferences.hints`), `samplingAutoApprove` (required for sampling in non-UI sessions), `elicitation` (default `true` with UI), `outputGuard`, `trace` (`{ enabled, file, maxBytes: 262144, maxEvents: 10000 }`; the per-session JSONL defaults to `.pi/mcp-traces/` and never records payloads, prompts, arguments/results, auth data, or URLs).

Per-server `idleTimeout`, `requestTimeoutMs`, and `approveTools` override the global values.

### Tool Approval

`approveTools` keeps a tool visible but gates the call — useful for destructive or high-cost actions where hiding the tool would hurt planning:

```json
{ "settings": { "approveTools": ["github_delete_*", "notion_update_*"] },
  "mcpServers": { "github": { "approveTools": ["delete_*", "merge_pull_request"] }, "docs": { "approveTools": false } } }
```

A matching call from the proxy tool, a direct MCP tool, `mcpScript`, a resource call, or an MCP UI iframe prompts **Allow once** / **Allow for session** / **Deny**; session approvals live in memory only, and headless sessions fail closed with an `approval_required` result. `excludeTools` still removes tools entirely — `approveTools` only gates visible ones.

Permission extensions can broker decisions by listening on `MCP_TOOL_APPROVAL_REQUEST_EVENT` (`pi-mcp-adapter:tool-approval-request`) and claiming the request synchronously with `request.claim(async () => "allow_once" | "allow_for_session" | "deny" | "abstain")`. The request carries `serverName`, `originalToolName`, `prefixedToolName`, `args`, `origin`, and an optional `signal`; the first synchronous claim wins, `allow_for_session` updates the same in-memory cache as the dialog, and `abstain`/no claim keeps the fallback behavior. Brokered approval runs for every uncached MCP call regardless of `approveTools` config.

### Search Keywords

Search matches literally, so per-server `searchKeywords` adds vocabulary for tools whose names and descriptions use different words:

```json
{ "mcpServers": { "github": { "searchKeywords": { "search_code": ["grep"], "*": ["gh"] } } } }
```

Keys match a tool's original name, prefixed name, or a glob (`*` covers every tool on the server), and all matching entries combine. Keywords are weighted like description text with an extra boost on exact phrase matches. They affect ranked and regex search only (including `tools.search` in `mcpScript`) and never appear in tool schemas, `describe` output, direct-tool registration, or the metadata cache — so keyword search works offline from cached metadata.

## Output Guard

On by default: inline text is capped at **50 KiB / 2000 lines** (matching Pi's `bash` guard), with the full text spilled to a temp file whose path is included so the agent can `read`/`grep` it. Image blocks pass through unchanged. Binary resource blobs up to **10 MiB** are decoded to private temp files and replaced with file references, bounded to 100 MiB and 10,000 files per session and removed at session teardown. In proxy mode `details.mcpResult` stays raw when its JSON is ≤ 16 KiB; larger results become a compact summary with the raw JSON spilled to a temp file (direct tools never carry `mcpResult`). Tune with `{ maxBytes, maxLines, detailsMaxBytes }`; disable with `"outputGuard": false` or `MCP_OUTPUT_GUARD=0`. Text/raw-JSON spill files are mode `0600` under the system temp dir and are not cleaned up automatically; binary resource-file cleanup follows the separate session-bound lifecycle above.

## Direct Tools

```json
{ "mcpServers": { "github": { "directTools": ["search_repositories", "get_file_contents"] } } }
```

`true` registers all of a server's tools individually, an array registers only those (original MCP names), omitted/`false` is proxy-only. Per-server overrides the global default. `includeTools`/`excludeTools` filter direct tools, proxy search/list/describe, and the `/mcp-adapter` panel. Each direct declaration increases prompt size; expose a targeted set or use search/proxy discovery for large servers.

Direct tools can register from the metadata cache (`~/.pi/agent/mcp-cache.json`, or `$PI_CODING_AGENT_DIR/mcp-cache.json`). If required metadata is missing, startup may connect to populate it and hot-load declarations; `deferWithMissingMetadata: true` opts into deferral. Servers advertising list-change notifications refresh the current session. Force a refresh with `/mcp-adapter reconnect <server>`.

Set `settings.freezeDirectTools: true` when prompt-cache stability matters more than hot-loading: the initial sync still runs, but later automatic reconnects, lazy-connects, and list-change notifications leave the registered tool surface unchanged. Explicit reconnects also preserve a frozen direct-tool surface; proxy/search/cache metadata still refreshes.

## Proxy Tool API

```javascript
mcp({ })                                        // status / list servers
mcp({ server: "name" })                         // server details (+ instructions preview)
mcp({ search: "screenshot navigate", limit: 12, offset: 0 })  // ranked tool search
mcp({ describe: "tool_name" })
mcp({ instructions: "name" })                   // full server instructions
mcp({ tool: "chrome_devtools_take_screenshot", args: { format: "png" } })
mcp({ connect: "server-name" })                 // connect or refresh
mcp({ action: "ui-messages" })
mcp({ action: "auth-start", server: "name" })
mcp({ action: "auth-complete", server: "name", args: { redirectUrl: "http://localhost:19876/callback?code=...&state=..." } })
```

`args` accepts a JSON object or a JSON string. Search covers **MCP tools only** in the current adapter. Space-separated words are ranked by weighted matches across name, server, description, and any configured `searchKeywords`, then paginated (`limit` defaults to 12; follow `details.nextOffset`). `regex: true` still works but paginates without ranking. Names fuzzy-match on hyphens and underscores, and an unresolvable `describe`/`tool` name returns top suggestions so the agent can fix a typo in the same turn. With `includeSchemas`, search and describe render common JSON Schema parameters as compact TypeScript shapes like `{ query: string; limit?: number; }`. For HTTP servers, a failed connect runs a one-request shape probe that turns opaque transport errors into hints such as `endpoint returned HTML (200) — this URL does not appear to speak MCP`. Server `instructions` surface at three levels: a truncated head in the proxy tool description, a longer preview in `mcp({ server })`, and the full text via `mcp({ instructions })` — captured at connect time and cached.

Remote/headless OAuth: `/mcp-auth <server>` first shows a clickable authorization URL. Open it in your local browser, approve, then select **Yes** in Pi to open the callback input — the browser's localhost callback page will usually fail to load (localhost is your workstation), so copy the full URL from its address bar and paste it into Pi. When the browser can reach Pi's callback directly, the authorization screen closes on its own instead. The same flow is available through the proxy tool (`auth-start` then `auth-complete` with `redirectUrl` or `args: { code }`) for non-interactive clients. By default persistent OAuth requires the OS credential store, such as an unlocked Secret Service on headless Linux. An explicit `oauthCredentialStore: "encrypted-file"` alternative needs `PI_MCP_ADAPTER_OAUTH_FILE_KEY`; neither mode silently falls back to plaintext. On Linux, when credential access fails because Pi inherited a revoked session keyring, the adapter attempts recovery through `keyctl session - node <packaged helper>` (requires `keyctl` and `node` on `PATH`) so re-authentication can write fresh credentials without killing a long-lived tmux server.

## Commands

`/mcp-adapter` (interactive panel: status, tools, direct/proxy toggles, reconnect, `ctrl+a` or Enter for OAuth, Save on `ctrl+s` — remappable via the `mcp.panel.save` keybinding), `/mcp-adapter setup` (imports, a minimal `.mcp.json`, curated known servers — DeepWiki, Context7, Notion, GitHub, Chrome DevTools — RepoPrompt quick-add, config-path inspection), `/mcp-adapter tools`, `/mcp-adapter prompts`, `/mcp-adapter reconnect [server]`, `/mcp-adapter disable <server>`, `/mcp-adapter enable <server>`, `/mcp-adapter logout <server>`, `/mcp-auth [server]`.

## Prompts, Elicitation, UI

MCP prompt templates register as slash commands `/mcp__<server>__<prompt>`, refreshed on connect. Arguments support positional and `key=value` forms with quoting; required arguments are validated before `prompts/get`. Results flatten into one user message preserving `[user]`/`[assistant]` markers.

Elicitation forms use Pi's `select()`/`input()` dialogs with validation and a review step; explicit refusal maps to MCP `decline`, dismissal to `cancel`. URL mode is TUI-only, always shows requesting server/host/URL, and requires consent; `-32042` URL-required tool errors are handled — retry the original call after completing the browser step.

MCP UI resources open in a native macOS window via Glimpse (`pi install npm:glimpseui`) or fall back to the browser. `MCP_UI_VIEWER=browser|glimpse|none` forces or suppresses the viewer (`none` still runs the tool and returns inline results). UIs talk back — message types `prompt`, `intent`, `notify`, `message`, plus custom types forwarded as intents — retrieved with `mcp({ action: "ui-messages" })` (each with `type`, `sessionId`, `serverName`, `toolName`, `timestamp`). Calling the same tool again pushes a new result into the open window instead of replacing it. Tool consent gates whether UIs may call MCP tools (never / once-per-server / always), and `_meta.ui.visibility` controls audience — app-only tools stay out of the model tool list, model-only tools cannot be called from the UI iframe. Browser controls: Cmd/Ctrl+Enter completes, Escape cancels.

## Status Snapshots

```ts
import { MCP_STATUS_EVENT, type McpStatusSnapshot } from "pi-mcp-adapter";
pi.events.on(MCP_STATUS_EVENT, (snapshot) => { /* read-only */ });
```

Includes `totalTools`, `totalResources`, `connectedCount`, `disabledCount`, and per-server `name`, `status` (connected, cached, failed, needs-auth, not-connected, disabled), `toolCount`, `disabled`, plus `resourceCount` when known and `failedAgoSeconds` on active failure. Reading status never connects a lazy server, starts auth, or exposes clients, transports, credentials, or server definitions. An initial snapshot follows initialization; an empty snapshot is emitted on shutdown.

## Behavior Notes and Limitations

npx-based servers resolve to direct binaries, avoiding an extra npm parent process. Advertised `outputSchema` supports JSON Schema draft-07 and 2020-12 (unstamped schemas use the SDK's 2020-12 default), and returned `structuredContent` is validated for both proxy and direct calls. Results use compact self-rendered rows by default — collapsed success output shows the call title and the first result line plus a `Ctrl+O to expand` hint — while the model still receives the full result. Set `toolResultRendering: "boxed"` for the legacy row, or `collapsedResultLines` to `2`/`3` for more collapsed text.

Limitations: no cross-session server sharing (each Pi session runs its own server processes, unless using rmcp-mux); MCP sampling is text-only (context inclusion, tools, stop sequences, audio, and images are rejected); inline images follow Pi's image display settings; Pi still owns one separator row before self-rendered tool output, so compact mode reduces but cannot eliminate the gap.

Subagents (`pi-subagents`) receive direct MCP tools only when listed with an `mcp:` prefix in their `tools:` frontmatter — a global `directTools: true` is not enough. See `references/pi-subagents.md`.


## Current admission and scripting contracts

Project `.mcp.json` and `.pi/mcp-adapter.json` servers follow Pi trust and a separate approval tied to the effective server definition. Trusted headless sessions skip unapproved project servers unless user-global `settings.projectServers: "allow"` explicitly enables them. Project files cannot loosen that policy. `settings.ancestorConfigRoots` optionally scopes ancestor discovery to explicit trusted roots; it is off by default.

Stdio `inheritEnv: false` limits inherited process environment; `literalEnv` avoids interpolation for explicitly literal values. `directTools: "search"` registers tools inactive until search/call activates them. Optional `strictDirectToolArguments` validates direct inputs; `directToolResultDetails: "bounded"` retains guarded raw fields (default `lean`). Namespace proxy wrappers are controlled by `namespaceProxyTools` (default true).

`mcpScript` is **opt-in** through `settings.scriptMode: true`. Use `await tools.search({ query, server?, limit?, offset? })`, `await tools.describe({ path, server? })`, and `await tools.call(path, args, { server }?)`; calls return `{ ok: true, data }` or `{ ok: false, error: { code, message } }`, where `data` is the raw MCP result. Preserve the server from discovery to disambiguate shared names. Output shapes in describe are observed field/type hints, not schemas; with script mode enabled they may persist across sessions. The script deadline defaults to 30s. These are adapter APIs, not native Pi codemode APIs.

The SDK `createMcpAdapter({ config })` form is an isolated snapshot. Extension loading and configuration paths were executed without contacting external MCP servers; programmatic approval, OAuth, Apps, sampling and remote protocol compatibility remain source-verified only.
