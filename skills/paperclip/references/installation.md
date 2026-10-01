# Installing and authenticating GXL Paperclip

Reviewed on 2026-09-30 against CLI/SDK 0.7.92, the
[official installer](https://paperclip.gxl.ai/install.sh),
[installation page](https://paperclip.gxl.ai/install), and local CLI source/help.
Installer and account mutations were not executed. Commands below are illustrative unless noted.

## Native install

The documented macOS/Linux installer is:

```bash
curl -fsSL https://paperclip.gxl.ai/install.sh | bash
```

It requires **an existing Python 3.8+ interpreter**, Bash, and curl or wget. It downloads the wheel,
extracts it to `~/.paperclip/lib/`, supplies missing `requests`, `click`, and `pyyaml` dependencies,
and writes `~/.local/bin/paperclip`. The launcher uses `#!/usr/bin/env python3`; it does not bundle
an interpreter. The installer may edit the shell profile and opens interactive login/agent-selection
prompts. Read the script before an authorized installation; do not run it as a read-only probe.

```bash
curl -fsSL https://paperclip.gxl.ai/install.sh -o /tmp/paperclip-install.sh
less /tmp/paperclip-install.sh
```

The official `https://paperclip.gxl.ai/version.json` currently reports version `0.7.92` and a SHA-256
for the distributed wheel. This corrects the old claim that no checksum is published. The inspected
installer/updater does not enforce that checksum itself. For a reproducible environment, retain the
wheel, its observed version, and the published checksum; detect if the unversioned URL changes
between metadata retrieval and download.

For an environment managed by uv:

```bash
uv venv .venv
uv pip install --python .venv/bin/python https://paperclip.gxl.ai/paperclip.whl
.venv/bin/paperclip --version
```

The endpoint is unversioned. Do not install the unrelated PyPI package named `paperclip`.
Installation into a controlled environment exposes both the CLI and `gxl_paperclip` Python module.
The managed install's private library directory is not automatically on another interpreter's path.

If the launcher cannot be found:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Windows users can connect to hosted MCP without running the macOS/Linux installer.
Use the current vendor installation page for any client-specific setup.

## Credentials and precedence

For ordinary user authentication, inspected 0.7.92 code resolves:

| Surface | Precedence |
|---|---|
| CLI data commands | `PAPERCLIP_BEARER_TOKEN`, then explicit `--api-key`/`PAPERCLIP_API_KEY`, then stored OAuth |
| SDK `from_env()` | `PAPERCLIP_BEARER_TOKEN`, then `PAPERCLIP_API_KEY`, then stored OAuth |

Trusted internal execution has an additional internal-auth branch; it is not a user setup mechanism.
Do not mix identities inadvertently. `--api-key` overrides the key environment binding, but a bearer
token still takes precedence in the data-command client. Avoid secrets in command-line arguments.

Create keys privately at `https://paperclip.gxl.ai/keys`. API-key requests use `X-API-Key`; bearer
requests use `Authorization: Bearer ...`. Do not print, commit, or upload either credential.

Paperclip does not load `.env` automatically. If the user has a trusted, shell-compatible `.env`,
load it and execute the command in the same shell:

```bash
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi
paperclip config 2>&1 | grep -E 'Auth:|Health:'
```

The guard avoids the fatal missing-file behavior of POSIX `.`. Sourcing executes shell code, so
never source a downloaded or untrusted file. Exports persist within that shell and its children;
fresh tool-shell invocations need their own environment. A secret manager or pre-exported key needs
no dotenv prefix. The normal `.env` file belongs in `.gitignore`.

`paperclip login` opens a browser and writes OAuth credentials under `~/.paperclip/credentials.json`.
Use it when the user is present to complete sign-in. `logout` deletes stored credentials; it is an
account action, not an authentication check. Noninteractive missing-auth calls fail instead of
completing browser login.

## Diagnostics are not authentication validation

```bash
paperclip --version
paperclip config 2>&1 | grep -E 'Auth:|Health:'
```

`Auth` describes a configured credential, not its validity. CLI `config` uses an unauthenticated
`GET /health` for the reachability line. An invalid key may still look configured. The next
**task-authorized** request validates usable access; do not spend search or LLM quota just to test a
key. SDK `health()` is different: it dispatches the authenticated `status` command and returns a
`HealthStatus`; inspect `healthy`, `output`, and errors rather than reachability alone.

Do not print complete config files: they can contain account or credential information.

## Optional agent skill installation

`paperclip install` writes the vendor's agent entrypoint into a project. The installed file now
points the agent to `paperclip skill` for full instructions rather than embedding a frozen manual.
The inspected non-TTY selection order is 1 = Claude Code, 2 = Cursor, 3 = Codex:

```bash
# Only when this installation is requested; stdin answers the two prompts.
printf '3\n\n' | paperclip install --dir /path/to/project
```

The second blank answer accepts the provided directory. Multiple choices use commas at the active
prompt, not a later shell command. Paths are `.claude/skills/paperclip/`,
`.cursor/skills/paperclip/`, and `.agents/skills/paperclip/`. Native help does not currently expose
an `--agent` or `--yes` option. Installation behavior was inspected, not run in this review.

## Hosted MCP

The documented Streamable HTTP endpoint is:

```text
https://paperclip.gxl.ai/mcp
```

Use the client's supported OAuth flow or `X-API-Key` header. Configure secrets through the client;
do not embed a real key in a shared config example. See the vendor's
[per-client setup](https://paperclip.gxl.ai/install) for the current interface.

Release 0.7.90 changed the connector to expose one tool per CLI command. Do not assume the old
single `paperclip` tool catalogue. Discover the connected tools and load current instructions.
The SDK still uses a legacy command-dispatch MCP call internally, which is a distinct client
compatibility path. Native-only installation/account/local-file commands are unavailable over MCP;
connector uploads use the connector's upload flow, not a path on the user's local filesystem.
No authenticated MCP session was exercised during this review.

## Configuration and maintenance

```bash
paperclip config --sources-list
paperclip config --help
paperclip update --help
paperclip uninstall --help
```

In 0.7.92, `config --sources`, `--sources-list`, and `--sources-clear` all display defaults;
the callbacks no longer save or clear a persistent source filter. Pass `-s` on each query. The
old troubleshooting instruction to clear a stale source filter is therefore inapplicable.
`config --url URL` still changes the stored server. `PAPERCLIP_BASE_URL` overrides that setting.
Only send credentials to the server selected for the task.

When requested, `paperclip update` upgrades the managed install and refreshes installed agent
skills; `paperclip uninstall` removes the install and prompts for confirmation (`--keep-credentials`
retains credentials). Neither is a verification command. Managed data commands may also check for
updates and refresh skills automatically. Updating once is **not version pinning**. Record the
observed version for reproducibility, or use a controlled environment and retained wheel.
