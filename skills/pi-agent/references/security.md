# Security

Source: https://pi.dev/docs/latest/security

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Pi is a local coding agent. It runs with the permissions of the user account that starts it and treats files writable by that user as inside the same local trust boundary.

## Project Trust

Project trust controls whether Pi loads project-local settings, resources, packages, and extensions. It is not a sandbox and does not restrict what the model can ask tools to do once you are working in a directory.

Pi considers a project to require trust when it finds any of these from the current working directory:

- `.pi/settings.json` or `.pi/mcp.json`
- `.pi/extensions`, `.pi/skills`, `.pi/prompts`, or `.pi/themes`
- `.pi/SYSTEM.md` or `.pi/APPEND_SYSTEM.md`
- project `.agents/skills` in the current directory or an ancestor

A bare `.pi` directory does not count.

When an interactive session starts in such a project with no saved decision for the current or a parent directory, Pi follows `defaultProjectTrust` (default `"ask"`). Saved decisions are stored by canonical directory in `~/.pi/agent/trust.json`, and the closest saved decision on the current or parent path applies before the global default.

Trusting a project allows Pi to load `.pi/settings.json`, `.pi` resources (extensions, skills, prompt templates, themes, system prompt files), install missing project packages configured through project settings, and execute project-local and project package-managed extensions.

Declining skips protected resources. Context files — `AGENTS.override.md`, `AGENTS.md`, and `CLAUDE.md` — load regardless of trust unless context loading is disabled. Before trust resolves, Pi loads only context files, user/global extensions, and CLI `-e` extensions — those can handle the `project_trust` event, and the first extension returning a yes/no decision owns it.

Non-interactive modes (`-p`, `--mode json`, `--mode rpc`) never prompt. Without an applicable saved decision, `"ask"` and `"never"` ignore trust-gated resources while `"always"` trusts them. `--approve`/`-a` and `--no-approve`/`-na` override for one run.

## No Built-in Sandbox

Built-in tools read, write, edit, and run shell commands with the permissions of the Pi process. Extensions are TypeScript modules with the same permissions. Package installs, shell commands, language servers, and test commands behave as ordinary local processes.

This is intentional: Pi is designed to operate on local source trees, invoke project toolchains, and integrate with an existing development environment. A partial in-process sandbox would be easy to mistake for a security boundary while still depending on the host shell, filesystem, package managers, credentials, and extension code. Real isolation must come from the OS or a virtualization/container boundary.

Project trust is only an input-loading guard. It prevents a repository from silently changing Pi's settings or extensions before you approve it. It does not make untrusted code, prompts, or model output safe. Prompt injection from repository files, comments, documentation, context files, or build output is expected local-agent risk and cannot be reliably prevented.

## Running Untrusted or Unmonitored Work

For untrusted repositories, generated code you will not monitor closely, or unattended automation, run Pi in a contained environment — container, VM, micro-VM, remote sandbox, or policy-controlled sandbox — with only the files and credentials the task needs. Patterns are documented in `references/containerization.md`:

- run the whole `pi` process inside a container/sandbox
- run host Pi while routing built-in tool execution into a Gondolin micro-VM
- mount only the workspace paths the agent should access
- avoid mounting host `~/.pi/agent` unless the container should reach host sessions, settings, and credentials
- pass the minimum required API keys or use short-lived credentials
- restrict network access when the task does not need it
- review diffs and outputs before copying results back to trusted systems

Bind-mounting a host workspace read/write means writes from inside the container or VM still modify host files. Use read-only mounts or copy files in and out when you need stronger protection.

## Reporting Security Issues

Follow the repository [Security Policy](https://github.com/earendil-works/pi/blob/main/SECURITY.md); do not open a public issue. Expected local-agent behavior, the absence of a built-in sandbox, prompt injection from untrusted content, and behavior of user-installed extensions or skills are generally outside the security boundary unless the report shows a real privilege-boundary bypass or access the local user did not already have.
