# Pi Documentation Overview

Source: https://pi.dev/docs/latest

Pi is a minimal terminal coding harness. The core stays small and most workflow-specific behavior lives in TypeScript extensions, skills, prompt templates, themes, and Pi packages.

## Top-Level Areas

- Start here: quickstart, usage, providers, security, containerization, settings, keybindings, sessions, compaction.
- Customization: extensions, skills, prompt templates, themes, Pi packages, custom models, custom providers.
- Programmatic usage: SDK, RPC mode, JSON event stream mode, TUI components.
- Reference: session file format and SessionManager API.
- Platform setup: Windows, Termux, tmux, terminal setup, shell aliases.
- Development: local source setup, rebranding, debug logs, tests, package structure.

## Quick Install

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
pi
```

On Linux/macOS, the installer is also available:

```bash
curl -fsSL https://pi.dev/install.sh | sh
```

Authenticate with `/login` for subscription providers or set API keys such as `ANTHROPIC_API_KEY` before startup.
