# Using Pi

Source: https://pi.dev/docs/latest/usage

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

## Interface

Interactive mode has four areas: startup header (shortcuts, loaded context files, prompt templates, skills, extensions), messages, editor, and footer. The footer shows cwd, session name, token/cache usage, cost, context usage, and current model; totals include assistant responses, usage reported by tools, and summary generation. The editor border indicates thinking level. Built-in UI (`/settings`) or extension UI can temporarily replace the editor.

## Editor Features

| Feature | How |
|---|---|
| File reference | Type `@` to fuzzy-search project files |
| Path completion | Tab |
| Multi-line input | Shift+Enter, or Ctrl+Enter on Windows Terminal |
| Copy response | Ctrl+X copies the last assistant message; in `/tree` it copies the selected message |
| Images | Paste with Ctrl+V (Alt+V on Windows and WSL), or drag into the terminal |
| Shell command | `!command` runs and sends output to the model |
| Hidden shell command | `!!command` runs without sending output to the model |
| External editor | Ctrl+G opens `externalEditor`, `$VISUAL`, `$EDITOR`, Notepad on Windows, or `nano` elsewhere |

## Slash Commands

| Command | Description |
|---|---|
| `/login`, `/logout` | Manage OAuth or API-key credentials |
| `/llama` | Download, load, unload llama.cpp router models (`references/llama-cpp.md`) |
| `/model`, `/thinking` | Switch models or thinking level; Ctrl+S saves a default |
| `/mcp` | Manage built-in MCP connections and exposure |
| `/bug [description]` | Review/export or upload a redacted bug report |
| `/scoped-models` | Enable/disable models for Ctrl+P cycling |
| `/settings` | Thinking level, theme, message delivery, transport |
| `/resume`, `/new`, `/name <name>`, `/session` | Session management |
| `/tree` | Jump to any point in the session and continue from there |
| `/trust` | Save project trust decision for future sessions |
| `/fork`, `/clone` | New session from a previous user message / duplicate active branch |
| `/compact [prompt]` | Manually compact context, optionally with custom instructions |
| `/copy` | Copy last assistant message to clipboard |
| `/export [file]` | Export session to HTML or JSONL |
| `/import <file>` | Import and resume a session from a JSONL file |
| `/share` | Upload as private GitHub gist with shareable HTML link |
| `/reload` | Reload keybindings, extensions, skills, prompts, themes, context files |
| `/hotkeys`, `/changelog`, `/quit` | Shortcuts, version history, quit |

Skills are available as `/skill:name`; prompt templates expand as `/templatename`; extensions can register custom commands.

## Message Queue

- Enter queues a steering message, delivered after the current assistant turn finishes its tool calls.
- Alt+Enter (Ctrl+Q on Windows and WSL) queues a follow-up message, delivered after the agent finishes all work.
- Escape aborts and restores queued messages to the editor; Alt+Up (Alt+Q on Windows and WSL) retrieves them.
- `steeringMode` and `followUpMode` control one-at-a-time vs all-at-once delivery.

Windows/WSL defaults use Ctrl+Q for follow-up, avoiding Windows Terminal's Alt+Enter fullscreen shortcut. Remap only if you deliberately want Alt+Enter.

## Context and System Prompt Files

Pi loads `AGENTS.md` or `CLAUDE.md` from `~/.pi/agent/AGENTS.md`, parent directories walking up from cwd, and the current directory. A directory containing `AGENTS.override.md` contributes that file instead of its `AGENTS.md`/`CLAUDE.md`; other directories still layer normally. Disable with `--no-context-files` / `-nc`.

Replace the default system prompt with `.pi/SYSTEM.md` (project) or `~/.pi/agent/SYSTEM.md` (global). Append instead of replacing with `APPEND_SYSTEM.md` in either location.

## Project Trust

Interactive startup asks before trusting a project folder that has project-local settings, resources, or project `.agents/skills` and no saved decision for that folder or a parent in `~/.pi/agent/trust.json`. Before the decision, Pi loads only context files, user/global extensions, and CLI `-e` extensions so they can handle `project_trust`. Non-interactive modes (`-p`, `--mode json`, `--mode rpc`) never prompt and follow `defaultProjectTrust` (`ask` default, `never`, `always`); `--approve`/`-a` and `--no-approve`/`-na` override for one run. `/trust` saves a decision (including for the immediate parent folder) to `trust.json` without reloading the session. `pi config` and package commands use the same flow, except `pi update` never prompts.

## Exporting and Sharing

`/export [file]` writes HTML by default or JSONL when the output name selects it; `/share` uploads a private GitHub gist with a shareable HTML link. `badlogic/pi-share-hf` publishes sessions to Hugging Face datasets for research.

## CLI Modes

```bash
pi [options] [@files...] [messages...]
pi -p "prompt"                # print and exit
pi --mode json "prompt"       # JSONL event stream
pi --mode rpc                 # RPC over stdin/stdout
pi --export <in> [out]        # export a session to HTML
```

Print mode reads piped stdin and merges it into the initial prompt.

## Package Commands

```bash
pi install <source> [-l]     # -l writes to project settings
pi remove <source> [-l]      # pi uninstall is an alias
pi update [source|self|pi]   # update pi only, or one package source
pi update --all              # pi + packages; reconcile pinned git refs
pi update --extensions       # packages only
pi update --models           # refresh model catalogs only
pi update --self             # update pi only
pi update --extension <src>  # update one package
pi list                      # list installed packages
pi config                    # enable/disable package resources
```

## Options

Model: `--provider <name>`, `--model <pattern>` (supports `provider/id` and `:<thinking>`), `--api-key`, `--thinking <off|minimal|low|medium|high|xhigh|max>`, `--models <patterns>`, `--list-models [search]`.

Session: `-c/--continue`, `-r/--resume`, `--session <path|id>`, `--session-id <id>` (open/create exact project ID), `--fork <path|id>`, `--session-dir`, `--no-session`, `-n/--name`.

Tools: `-t/--tools`, `-xt/--exclude-tools`, `-nbt/--no-builtin-tools` (keeps extension/custom tools), `-nt/--no-tools`. Built-ins: `read`, `bash`, `powershell` (native Windows), `edit`, `write`, `grep`, `find`, `ls`. Built-in extensions provide optional `codemode` and `tool_search`.

Resources: `-e/--extension <source>` (path, npm, or git; repeatable), `--no-extensions` (also disables built-in extensions), `--skill`, `--no-skills`, `--prompt-template`, `--no-prompt-templates`, `--theme`, `--no-themes`, `-nc/--no-context-files`. Combine `--no-*` with explicit flags to load exactly what you need: `pi --no-extensions -e ./my-extension.ts`.

Other: `--system-prompt <text>` (context files and skills are still appended), `--append-system-prompt`, `--tui-mode <regular|fullscreen>`, `--use-theme <name[/name]>` (initial theme for this run only), `--verbose`, `-a/--approve`, `-na/--no-approve`, `-h/--help`, `-v/--version`.

## Fullscreen TUI Mode

`--tui-mode fullscreen` (experimental) scrolls the transcript inside the terminal viewport while queued messages, working status, extension widgets, editor, and footer stay pinned at the bottom. Mouse/trackpad input scrolls the region under the pointer, and keyboard viewport actions (`tui.altScreen.*` in `references/keybindings.md`) stay available. Inline images work in terminals supporting the Kitty graphics protocol (Kitty, Ghostty); iTerm2 renders text placeholders instead. `regular` mode uses the main screen and terminal-owned scrollback. Switch at runtime and set the default in `/settings`; `fullscreenExitOutput` controls whether exiting prints the final transcript or only the resume hint.

File arguments: prefix with `@` to include in the message (`pi @code.ts @test.ts "Review these"`).

Environment variables are documented separately in `references/environment-variables.md`.

## Examples

```bash
pi "List all .ts files in src/"
pi --name "release audit" -p "Audit this repository"
pi --model openai/gpt-4o "Help me refactor"
pi --model sonnet:high "Solve this complex problem"
pi --models "claude-*,gpt-4o"
pi --tools read,grep,find,ls -p "Review the code"
pi --exclude-tools ask_question
```

## Design Principles

Pi keeps the core small and pushes workflow-specific behavior into extensions, skills, prompt templates, and packages. Pi 0.99 includes MCP, codemode, and tool search as built-in extensions. Subagent orchestration and other workflow policies remain package/extension concerns. Read `references/mcp.md` before installing an MCP adapter: the native and adapter configurations differ.
