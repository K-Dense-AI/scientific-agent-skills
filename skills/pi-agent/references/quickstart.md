# Quickstart

Source: https://pi.dev/docs/latest/quickstart

## Install and Uninstall

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

`--ignore-scripts` disables dependency lifecycle scripts. Pi does not need install scripts for normal npm installs.

Uninstall with the matching package manager. Curl and npm installs are removed with:

```bash
npm uninstall -g @earendil-works/pi-coding-agent
```

Uninstalling Pi leaves settings, credentials, sessions, and installed packages in `~/.pi/agent/`.

## Authenticate

Use `/login` in interactive mode for subscription providers: Claude Pro/Max, ChatGPT Plus/Pro (Codex), and GitHub Copilot. API-key providers can be configured by environment variable or stored through `/login` in `~/.pi/agent/auth.json`.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pi
```

## First Session

Run Pi in the project directory:

```bash
cd /path/to/project
pi
```

By default, the model gets `read`, `write`, `edit`, and `bash`. Additional read-only built-ins `grep`, `find`, and `ls` are available through tool options.

## Project Instructions

Pi loads context files at startup:

- `~/.pi/agent/AGENTS.md`
- `AGENTS.md` or `CLAUDE.md` from parent directories and current directory

Run `/reload` or restart after changing context files.

## Common First Tasks

```bash
pi @README.md "Summarize this"
pi @src/app.ts @src/app.test.ts "Review these together"
!npm run lint
!!npm run lint
pi -c
pi -r
pi --name "my task"
pi --session <path|id>
pi -p "Summarize this codebase"
cat README.md | pi -p "Summarize this text"
pi --mode json "List files"
pi --mode rpc --no-session
```

Use `!command` to run shell and send output to the model. Use `!!command` to run without adding output to model context.
