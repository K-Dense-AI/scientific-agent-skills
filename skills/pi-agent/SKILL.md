---
name: pi-agent
description: Build with and use Pi, the minimal terminal coding harness. Use for installing Pi, configuring providers/models/settings, creating Pi skills/extensions/packages/themes/prompt templates, embedding Pi through the SDK, integrating over RPC or JSON event streams, parsing sessions, developing custom Pi providers and TUI components, or using ecosystem packages such as pi-subagents (delegation/orchestration), pi-mcp-adapter (MCP servers), pi-interview (interactive forms), and pi-web-access (web search, fetching, video understanding).
license: MIT
compatibility: Requires Node.js/npm for Pi CLI and SDK usage. Pi package name is @earendil-works/pi-coding-agent.
metadata: {"version": "1.1", "skill-author": "K-Dense Inc."}
---

# Pi Agent

Use this skill when the user wants to operate Pi or build on top of Pi. Pi is a minimal terminal coding harness extended through TypeScript extensions, skills, prompt templates, themes, packages, custom models/providers, SDK integrations, RPC mode, JSON event streams, and TUI components.

## First Decision

Pick the reference before answering or coding:

| User intent | Read |
|---|---|
| Install, authenticate, first run | `references/quickstart.md` |
| Day-to-day CLI usage, commands, modes, flags | `references/usage.md` |
| Provider auth, API keys, cloud provider setup | `references/providers.md` |
| Custom model entries, local models, proxies | `references/models.md` |
| Extension development, custom tools, events, commands | `references/extensions.md` |
| Custom provider implementation, OAuth, custom streaming | `references/custom-provider.md` |
| Embed Pi in Node/TypeScript | `references/sdk.md` |
| Integrate from another process/language | `references/rpc.md` |
| Consume JSONL event output | `references/json.md` |
| Build terminal UI components | `references/tui.md` |
| Package extensions/skills/prompts/themes | `references/packages.md` |
| Delegate to subagents, chains, parallel runs, orchestration | `references/pi-subagents.md` |
| Connect MCP servers, MCP tool discovery/config | `references/pi-mcp-adapter.md` |
| Interactive interview forms, structured user input | `references/pi-interview.md` |
| Web search, URL/PDF/repo fetching, video understanding | `references/pi-web-access.md` |
| Author Pi skills | `references/skills.md` |
| Prompt templates or themes | `references/prompt-templates.md`, `references/themes.md` |
| Sessions, branching, compaction, parsing JSONL | `references/sessions.md`, `references/compaction.md`, `references/session-format.md` |
| Security, sandboxing, trust | `references/security.md`, `references/containerization.md` |
| Keyboard or terminal issues | `references/keybindings.md`, `references/terminal-setup.md`, `references/tmux.md`, `references/windows.md`, `references/termux.md`, `references/shell-aliases.md` |
| Working on Pi itself | `references/development.md` |

## Build-On-Pi Defaults

Prefer the SDK for Node/TypeScript apps that need type safety, direct state access, in-process custom tools/extensions, or custom resource loading. Use `createAgentSession()` for a single stable session; use `createAgentSessionRuntime()` when the app must replace sessions through new/resume/fork/clone/import flows.

Prefer RPC mode when the client is not Node.js, needs process isolation, or wants a language-agnostic JSONL protocol. Start with `pi --mode rpc --no-session` for stateless subprocess integration, then add session flags when persistence matters.

Prefer JSON mode for one-shot command-line pipelines that only need streamed events, not bidirectional control: `pi --mode json "prompt"`.

Use extensions for Pi-native behavior: custom tools, command handlers, event hooks, provider registration, custom compaction, path protection, project trust policy, UI prompts, widgets, and TUI components.

Use packages when sharing or installing reusable extensions, skills, prompt templates, or themes across machines or projects.

## Safety Defaults

Pi is local and not sandboxed by default. Treat extensions, packages, skills, shell commands, and project-local `.pi` resources as code with the permissions of the Pi process. For untrusted repos or unattended automation, isolate with Docker, OpenShell, Gondolin, a VM, or a remote sandbox.

Do not store secrets in project files. Prefer env vars, `~/.pi/agent/auth.json`, OAuth via `/login`, or command-backed secret lookups in `models.json`/provider config.

## Common Commands

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
pi
pi -p "Summarize this codebase"
pi --mode json "List files"
pi --mode rpc --no-session
pi --provider anthropic --model claude-sonnet-4-5
pi --tools read,grep,find,ls -p "Review this repository"
```

## Source Coverage

These references summarize the Pi documentation at `https://pi.dev/docs/latest` and each docs page found under it as of this skill version, plus the package pages for `pi-subagents`, `pi-mcp-adapter`, `pi-interview`, and `pi-web-access` at `https://pi.dev/packages/`. When exact API behavior matters, prefer the cited reference page and inspect installed TypeScript definitions under `node_modules/@earendil-works/pi-coding-agent/dist/` and `node_modules/@earendil-works/pi-ai/dist/`.
