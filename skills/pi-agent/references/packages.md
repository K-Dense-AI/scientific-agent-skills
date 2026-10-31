# Pi Packages

Source: https://pi.dev/docs/latest/packages

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Pi packages bundle extensions, skills, prompt templates, and themes for sharing through npm, git, URL, or local paths. Packages run with full system access — extensions execute arbitrary code and skills can instruct the model to run executables. Review third-party source before installing.

## Install and Manage

```bash
pi install npm:@foo/bar@1.0.0
pi install git:github.com/user/repo@v1
pi install https://github.com/user/repo
pi install /absolute/path/to/package
pi install ./relative/path/to/package

pi remove npm:@foo/bar
pi list                     # installed packages from settings
pi update                   # update pi only
pi update --all             # pi + packages; reconcile pinned git refs
pi update --extensions      # packages only; reconcile pinned git refs
pi update --models          # refresh model catalogs only
pi update --self            # update pi only
pi update --self --force    # reinstall pi even if current
pi update npm:@foo/bar      # update one package
pi update --extension npm:@foo/bar
pi config                   # enable/disable package resources
```

`install`/`remove` write to user settings by default; `-l` writes to project settings (`.pi/settings.json`), which can be shared with a team — Pi installs missing project packages automatically on startup after the project is trusted. To try a package for one run without installing, use `-e`/`--extension` (installs to a temporary directory):

```bash
pi -e npm:@foo/bar
pi -e git:github.com/user/repo
```

## Sources

**npm** — `npm:@scope/pkg@1.2.3` or `npm:pkg`. Versioned specs are pinned and skipped by package updates. User installs go under `~/.pi/agent/npm/`, project installs under `.pi/npm/`. `npmCommand` in settings pins npm operations to a wrapper such as `mise`.

**git** — `git:github.com/user/repo@v1`, `git:git@github.com:user/repo@v1`, `https://github.com/user/repo@v1`, `ssh://git@github.com/user/repo@v1`. Without the `git:` prefix only protocol URLs are accepted (`https://`, `http://`, `ssh://`, `git://`); with it, shorthand forms work. SSH URLs use your configured keys and respect `~/.ssh/config`. For CI, set `GIT_TERMINAL_PROMPT=0` and `GIT_SSH_COMMAND` (e.g. `ssh -o BatchMode=yes -o ConnectTimeout=5`) to fail fast. Refs are pinned tags or commits — updates reconcile an existing clone to the configured ref but never move it to a newer ref; use `pi install git:host/user/repo@new-ref` to move it. Clones live in `~/.pi/agent/git/<host>/<path>` or `.pi/git/<host>/<path>`. Reconciliation resets and cleans the clone, then runs `npm install` when `package.json` exists.

**Local paths** — absolute or relative, added to settings without copying. Relative paths resolve against the settings file. A file loads as a single extension; a directory loads using package rules.

## Package Manifest

```json
{
  "name": "my-package",
  "keywords": ["pi-package"],
  "pi": {
    "extensions": ["./extensions"],
    "skills": ["./skills"],
    "prompts": ["./prompts"],
    "themes": ["./themes"]
  }
}
```

Paths are relative to the package root and support glob patterns and `!exclusions`. The `pi-package` keyword makes the package visible in the [gallery](https://pi.dev/packages); add `pi.video` (MP4 only, autoplays on hover) or `pi.image` (PNG/JPEG/GIF/WebP) for a preview — video wins if both are set.

Without a manifest, Pi auto-discovers convention directories: `extensions/` (`.ts` and `.js`), `skills/` (recursive `SKILL.md` folders plus top-level `.md` files), `prompts/` (`.md`), `themes/` (`.json`).

## Dependencies

Third-party runtime dependencies belong in `dependencies`; Pi runs `npm install` when installing from npm or git.

Pi bundles core packages for extensions and skills. If you import `@earendil-works/pi-ai`, `@earendil-works/pi-agent-core`, `@earendil-works/pi-coding-agent`, `@earendil-works/pi-tui`, or `typebox`, list them in `peerDependencies` with `"*"` and do not bundle them or add physical runtime copies in `dependencies`. Managed installs suppress automatic peer installation; local packages retain the author's dependency tree. A duplicate host package can create separate classes and registries in compiled ESM.

Other Pi packages must be bundled: add them to `dependencies` **and** `bundledDependencies`, then reference their resources through `node_modules/` paths. Pi loads packages with separate module roots, so separate installs neither collide nor share modules.

## Filtering

```json
{
  "packages": [
    "npm:simple-pkg",
    {
      "source": "npm:my-package",
      "extensions": ["extensions/*.ts", "!extensions/legacy.ts"],
      "skills": [],
      "prompts": ["prompts/review.md"],
      "themes": ["+themes/legacy.json"]
    }
  ]
}
```

Omit a key to load all of that type, `[]` to load none, `!pattern` to exclude matches, `+path` to force-include an exact path, `-path` to force-exclude. `+`/`-` paths are exact and relative to the package root. Filters narrow what the manifest already allows.

## Enable/Disable and Scope

`pi config` toggles extensions, skills, prompt templates, and themes from installed packages and local directories. It starts in global settings; Tab switches between global and project-local, and `pi config -l` starts in project overrides with inherited global resources dimmed.

A package can appear in both global and project settings. The project entry wins unless it sets `autoload: false`, in which case it applies as a delta over the global entry. Identity: npm package name, git repository URL without ref, or resolved absolute path for local packages.

## Notable Ecosystem Packages

- `pi install npm:pi-subagents` — delegation, chains, parallel runs: `references/pi-subagents.md`
- `pi install npm:pi-mcp-adapter` — token-efficient MCP server access: `references/pi-mcp-adapter.md`
- `pi install npm:pi-web-access` — web search, URL/PDF/repo fetching, video understanding: `references/pi-web-access.md`
- `pi install npm:pi-interview` — interactive interview forms: `references/pi-interview.md`
- `pi install npm:glimpseui` — native macOS WebView windows used by several packages
- `pi install npm:@gotgenes/pi-permission-system` — runtime allow/ask/deny policy, composes with pi-subagents
