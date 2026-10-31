# Pi Documentation Overview

Source: https://pi.dev/docs/latest

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Pi is a minimal terminal coding harness. The core stays small and most workflow-specific behavior lives in TypeScript extensions, skills, prompt templates, themes, and Pi packages. Positioning on `https://pi.dev/`: "There are many agent harnesses but this one is yours" — interactive, print/JSON, RPC, and SDK interfaces, multiple providers with mid-session model switching, tree-structured shareable sessions, steering and follow-up during a run, and extensible primitives instead of baked-in features.

## Top-Level Areas

- Start here: quickstart, usage, providers, llama.cpp, security, containerization, settings, keybindings, sessions, compaction.
- Customization: extensions, skills, prompt templates, themes, Pi packages, native MCP, codemode, custom and virtual models, custom providers.
- Programmatic usage: SDK, RPC mode, JSON event stream mode, TUI components.
- Reference: environment variables, session file format and SessionManager API.
- Platform setup: Windows, Termux, tmux, terminal setup, shell aliases.
- Development: local source setup, rebranding, debug logs, tests, package structure.

## Quick Install

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
pi
```

On Linux/macOS the installer is also available:

```bash
curl -fsSL https://pi.dev/install.sh | sh
```

pnpm and bun global installs work too (`pnpm add -g --ignore-scripts ...`, `bun add -g --ignore-scripts ...`).

Authenticate with `/login` for subscription providers or set API keys such as `ANTHROPIC_API_KEY` before startup.

## Ecosystem

Package gallery at `https://pi.dev/packages` lists community extensions tagged `pi-package`. Source: `https://github.com/earendil-works/pi` (formerly `pi-mono`; docs live under `packages/coding-agent/docs/`, and doc pages still link the old repo name, which redirects).

Pi requires Node.js >= 22.19.0. The published version this skill was written against is `0.99.2` (`https://pi.dev/api/latest-version` reports the current one).
