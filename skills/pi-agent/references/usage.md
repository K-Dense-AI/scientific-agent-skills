# Using Pi

Source: https://pi.dev/docs/latest/usage

## Interface

Interactive mode has a startup header, message area, editor, and footer. The footer shows cwd, session name, token/cache usage, cost, context usage, and current model. The editor border indicates thinking level.

## Editor Features

- Type `@` to fuzzy-search project files.
- Press Tab for path completion.
- Use Shift+Enter, or Ctrl+Enter on Windows Terminal, for multi-line input.
- Paste or drag images in supported terminals.
- Prefix with `!` to run a shell command and include output in context.
- Prefix with `!!` to run a hidden shell command outside model context.
- Ctrl+G opens `$VISUAL` or `$EDITOR`.

## Slash Commands

Important commands: `/login`, `/logout`, `/model`, `/scoped-models`, `/settings`, `/resume`, `/new`, `/name`, `/session`, `/tree`, `/fork`, `/clone`, `/compact [prompt]`, `/copy`, `/export [file]`, `/share`, `/reload`, `/hotkeys`, `/changelog`, `/quit`.

Skills are available as `/skill:name`; prompt templates expand as `/template-name`; extensions can register custom commands.

## Message Queue

- Enter while the agent is running queues a steering message.
- Alt+Enter queues a follow-up message for after all current work finishes.
- Escape aborts and restores queued messages to the editor.
- Alt+Up retrieves queued messages.
- `steeringMode` and `followUpMode` control one-at-a-time vs all-at-once delivery.

## CLI Modes

```bash
pi [options] [@files...] [messages...]
pi -p "prompt"
pi --mode json "prompt"
pi --mode rpc
pi --export [out]
```

Print mode reads piped stdin and merges it into the initial prompt.

## Common Options

Model: `--provider`, `--model`, `--api-key`, `--thinking`, `--models`, `--list-models`.

Session: `-c/--continue`, `-r/--resume`, `--session`, `--fork`, `--session-dir`, `--no-session`, `--name/-n`.

Tools: `--tools/-t`, `--exclude-tools/-xt`, `--no-builtin-tools/-nbt`, `--no-tools/-nt`. Built-ins are `read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`.

Resources: `-e/--extension`, `--skill`, `--prompt-template`, `--theme`, and corresponding `--no-*` flags. `--no-context-files` disables `AGENTS.md`/`CLAUDE.md` discovery.

Other: `--system-prompt`, `--append-system-prompt`, `--verbose`, `--approve`, `--no-approve`, `--help`, `--version`.

## Environment Variables

- `PI_CODING_AGENT_DIR`: config directory, default `~/.pi/agent`.
- `PI_CODING_AGENT_SESSION_DIR`: session storage override.
- `PI_PACKAGE_DIR`: package directory override.
- `PI_OFFLINE`: disable startup network operations.
- `PI_SKIP_VERSION_CHECK`: skip version check.
- `PI_TELEMETRY`: override install/update telemetry and provider attribution headers.
- `PI_CACHE_RETENTION`: set `long` where supported.
- `VISUAL`, `EDITOR`: external editor.

## Design Principles

Pi intentionally does not include built-in MCP, sub-agents, permission popups, plan mode, to-dos, or background bash. Build or install those workflows as extensions/packages, or use containers/tmux/external tools.
