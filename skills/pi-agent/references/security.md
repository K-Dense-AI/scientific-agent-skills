# Security

Source: https://pi.dev/docs/latest/security

Pi is a local coding agent. It runs with the permissions of the user account that starts it and treats files writable by that user as inside the local trust boundary.

## Project Trust

Project trust controls whether Pi loads project-local settings, resources, packages, and extensions. It is not a sandbox.

Trust-gated inputs include `.pi/` in the current directory and `.agents/skills` in the current directory or ancestors. Trusting allows loading `.pi/settings.json`, `.pi` resources, missing project packages, project extensions, and project package-managed extensions.

`AGENTS.md` and `CLAUDE.md` context files load regardless of project trust unless context loading is disabled.

Non-interactive modes do not prompt. Without a saved trust decision, `defaultProjectTrust: "ask"` and `"never"` ignore trust-gated resources, while `"always"` trusts them. Use `--approve` or `--no-approve` for one-run override.

## No Built-in Sandbox

Built-in tools can read, write, edit, and run shell commands with the permissions of the Pi process. Extensions are TypeScript modules with the same permissions. Package installs and developer tools are ordinary local processes.

Project trust only guards input loading; it does not make untrusted code, prompts, model output, or build output safe.

## Untrusted Work

For untrusted repositories, generated code you will not monitor closely, or unattended automation, run Pi in a contained environment. Use Docker, OpenShell, Gondolin, a VM, micro-VM, or remote sandbox. Mount only needed files, avoid mounting host `~/.pi/agent` unless required, pass minimum credentials, restrict network where possible, and review diffs before copying results to trusted systems.
