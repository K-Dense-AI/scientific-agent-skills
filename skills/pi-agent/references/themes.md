# Themes

Source: https://pi.dev/docs/latest/themes

Themes are JSON files defining TUI colors.

## Locations

- Built-in: `dark`, `light`
- Global: `~/.pi/agent/themes/*.json`
- Project: `.pi/themes/*.json` after project trust
- Packages: `themes/` or `pi.themes`
- Settings: `themes` array
- CLI: `--theme`, repeatable

Disable with `--no-themes`. Select through `/settings` or `{"theme": "my-theme"}`. Pi detects terminal background on first run.

## Format

A theme has `$schema`, required `name`, optional `vars`, required `colors`, and optional `export` colors for HTML exports. All 51 color tokens must be defined.

Color values can be 6-digit hex strings, xterm 256-color indices, variable names from `vars`, or `""` for terminal default.

## Token Groups

- Core UI: accent, borders, success/error/warning, muted/dim/text/thinkingText.
- Background/content: selected/user/custom/tool states.
- Markdown: headings, links, code, quote, hr, list bullets.
- Tool diffs: added, removed, context.
- Syntax: comment, keyword, function, variable, string, number, type, operator, punctuation.
- Thinking levels: off, minimal, low, medium, high, xhigh.
- Bash mode.

Hot reload applies edits to the active custom theme for immediate feedback.
