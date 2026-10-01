# Environment Variables

Source: https://pi.dev/docs/latest/environment-variables

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Pi uses environment variables three ways: variables that configure the Pi process, markers Pi sets so child processes know they run inside Pi, and session metadata injected into commands run by the LLM-callable bash and native Windows PowerShell tools. Provider API-key variables live in `references/providers.md`.

## Process Markers

The CLI and RPC entry points set two markers:

- `AI_AGENT=pi` — generic marker letting tooling identify Pi as the launching agent.
- `PI_CODING_AGENT=true` — Pi-specific marker for detecting that a process runs inside Pi.

Child processes inherit both. Neither is session-specific, and neither is set automatically when Pi is embedded through the SDK.

## Bash Tool Session Environment

Commands run by the LLM-callable bash and native Windows PowerShell tools receive:

| Variable | Description |
|---|---|
| `PI_SESSION_ID` | Current session ID |
| `PI_SESSION_FILE` | Absolute path to the session JSONL file; unset for ephemeral sessions |
| `PI_PROVIDER` | Currently selected model provider |
| `PI_MODEL` | Currently selected model ID |
| `PI_REASONING_LEVEL` | Effective reasoning level: `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max` |

Values resolve when each command starts, so switching models affects the next bash command without restarting. `PI_PROVIDER`/`PI_MODEL` identify the selected Pi model, not an upstream model a router picks internally. When asked which model is running, inspect these variables instead of inferring from the system prompt:

```bash
printf '%s/%s\n' "$PI_PROVIDER" "$PI_MODEL"
```

These are injected into the LLM-callable bash and native Windows PowerShell tools only — not into user-entered `!` or `!!` commands.

Custom shell tools built with `createBashTool()` or `createPowerShellTool()` expose the same variables by default, injected **before** `spawnHook` so hooks see them in `ctx.env`. Disable with `exposeSessionEnvironment: false`; Pi then also clears inherited values so nested Pi processes do not leak stale parent-session metadata.

## Pi Process Configuration

| Variable | Description |
|---|---|
| `PI_CODING_AGENT_DIR` | Override the config directory; default `~/.pi/agent` |
| `PI_CODING_AGENT_SESSION_DIR` | Override session storage; overridden by `--session-dir` |
| `PI_PACKAGE_DIR` | Override the package directory (useful for Nix/Guix store paths) |
| `PI_OFFLINE` | Disable startup network operations: update checks, package updates, install/update telemetry |
| `PI_SKIP_VERSION_CHECK` | Disable the `pi.dev` latest-version request |
| `PI_TELEMETRY` | Override install/update telemetry and provider attribution headers: `1`/`true`/`yes` or `0`/`false`/`no` |
| `PI_CACHE_RETENTION` | Set to `long` for extended provider prompt caching where supported |
| `PI_SHARE_VIEWER_URL` | Override the base URL used by `/share` |
| `PI_RADIUS_GATEWAY` | Override Radius relay and bug-report gateway origin |
| `PI_HYPERLINKS`, `PI_TRUE_COLOR` | Capability override: `1`, `0`, or `auto` |
| `PI_IMAGE_PROTOCOL` | `kitty`, `iterm2`, `none`, or `auto` |
| `PI_HARDWARE_CURSOR` | Set to `1` to show the hardware cursor (IME positioning) |
| `PI_TUI_ESC_TIMEOUT` | Milliseconds to wait after a lone ESC before treating it as Escape; defaults to `100` over SSH and `10` otherwise. Increase when Alt-key input is misread as Escape |
| `VISUAL`, `EDITOR` | External editor fallback when the `externalEditor` setting is unset |
| `HTTP_PROXY`, `HTTPS_PROXY` | Proxy outbound HTTP requests |

Names are derived from the rebrandable app name (`package.json` `piConfig.name`), so a fork uses a different prefix — see `references/development.md`.

Other variables documented elsewhere: `PI_EXPERIMENTAL` (experimental first-time setup, `references/settings.md`), `PI_TUI_WRITE_LOG` (raw ANSI capture, `references/tui.md`), `AWS_BEDROCK_FORCE_CACHE` and other cloud variables (`references/providers.md`), `LLAMA_BASE_URL`/`LLAMA_API_KEY` (`references/llama-cpp.md`).
