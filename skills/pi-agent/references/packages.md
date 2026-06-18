# Pi Packages

Source: https://pi.dev/docs/latest/packages

Pi packages bundle extensions, skills, prompt templates, and themes for sharing through npm, git, URL, or local paths.

## Install and Manage

```bash
pi install npm:@foo/bar@1.0.0
pi install git:github.com/user/repo@v1
pi install https://github.com/user/repo
pi install /absolute/path/to/package
pi install ./relative/path/to/package
pi remove npm:@foo/bar
pi list
pi update
pi update --extensions
pi update --self
pi update npm:@foo/bar
pi update --extension npm:@foo/bar
```

Use `-l` to write install/remove to project settings `.pi/settings.json`; otherwise user settings are updated. Project packages install automatically after trust. Use `-e/--extension` to try a package for one run without installing.

## Sources

npm specs support pins. User installs go under `~/.pi/agent/npm/`; project installs under `.pi/npm/`. `npmCommand` can pin npm operations to a wrapper such as `mise`.

Git specs support HTTPS, SSH, and shorthand with `git:`. Refs are pinned tags or commits. Reconciliation may reset/clean clones and run `npm install` when `package.json` exists.

Local paths are referenced in settings without copying. Relative paths resolve against the settings file.

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

If no manifest exists, Pi auto-discovers conventional directories: `extensions/`, `skills/`, `prompts/`, `themes/`.

## Dependencies

Runtime deps belong in `dependencies`. Pi bundles core packages for extensions/skills; imports of `@earendil-works/pi-ai`, `@earendil-works/pi-agent-core`, `@earendil-works/pi-coding-agent`, `@earendil-works/pi-tui`, and `typebox` should be peer dependencies with `"*"` and not bundled.

## Filtering

Object settings can include/exclude resources with globs, `!pattern`, exact `+path`, exact `-path`, or `[]` to load none for a resource type.

## Notable Ecosystem Packages

- `pi install npm:pi-subagents` — delegate to child agents, chains, parallel runs: `references/pi-subagents.md`
- `pi install npm:pi-mcp-adapter` — token-efficient MCP server access: `references/pi-mcp-adapter.md`
- `pi install npm:pi-interview` — interactive interview forms for structured user input: `references/pi-interview.md`
- `pi install npm:pi-web-access` — web search, URL/PDF/repo fetching, video understanding: `references/pi-web-access.md`
- `pi install npm:pi-intercom` — child-to-parent coordination companion for pi-subagents

## Security

Packages run with full system access. Review third-party package code before installing.
