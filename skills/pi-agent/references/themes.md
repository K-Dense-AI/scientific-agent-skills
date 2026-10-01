# Themes

Source: https://pi.dev/docs/latest/themes

Reviewed against Pi 0.99.2 and its bundled theme schema on 2026-09-30.

## Select or create a theme

Built-ins are `system` (default, derives colors from the terminal palette), `dark`, and `light`. Choose through `/settings`; `theme: "light/dark"` follows terminal appearance. `--use-theme light` selects one invocation's initial theme without changing saved settings.

Copy a complete built-in `dark.json` or `light.json` from `packages/coding-agent/src/modes/interactive/theme/`, rename it, and save it as `~/.pi/agent/themes/<name>.json`. Change `vars` and `colors` while preserving all required color roles. The [versioned schema](https://github.com/earendil-works/pi/blob/v0.99.2/packages/coding-agent/src/modes/interactive/theme/theme-schema.json) defines the contract; a file containing only accent/text colors is invalid.

Themes also load from trusted `.pi/themes/`, packages, the settings `themes` list, and repeated `--theme <path>` flags. `--theme` loads a file; `--use-theme` selects by name. The active user theme hot-reloads only from `<agent-dir>/themes/<name>.json`; use `/reload` for other locations.

## File contract

`name` is required, unique, cannot contain `/`, and cannot be `system` (reserved). Optional `appearance` is `dark` or `light`; optional `vars` may reference other variables without missing names or cycles. `colors` supplies 51 required tokens. Five optional colors fall back: `scrollbarTrack` to `muted`, `scrollbarThumb` to `text`, `searchMatchBg` to `selectedBg`, `searchMatchText` to `text`, and `thinkingMax` to `thinkingXhigh`.

Accepted values are `#rgb`, `#rrggbb`, `oklch(...)`, `okhsl(...)`, ANSI indices 0–255, variable names, and `""` for terminal defaults. Pi uses truecolor when supported and approximates 256-color terminals; HTML export converts OKHSL to hex. `export.pageBg`, `cardBg`, and `infoBg` optionally override exported page colors.

Use callback-local `theme` in extensions. `theme.fg`, `bg`, `bold`, `italic`, `strikethrough`, `style`, `colors`, and `appearance` expose styling; rebuild cached colored child content in `invalidate()`. Verify long wrapped text, messages, tool states, diffs, and both terminal appearances. Graphical rendering was not exercised in this review.
