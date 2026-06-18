# TUI Components

Source: https://pi.dev/docs/latest/tui

Extensions and custom tools can render custom terminal UI components through `@earendil-works/pi-tui`.

## Component Interface

```ts
interface Component {
  render(width: number): string[];
  handleInput?(data: string): void;
  wantsKeyRelease?: boolean;
  invalidate(): void;
}
```

`render(width)` returns one string per line; each line must not exceed `width`. The TUI appends style resets at line ends, so reapply styles per line or use helpers that preserve ANSI styles.

## Focusable and IME

Text cursor components that need IME support implement `Focusable` and emit `CURSOR_MARKER` before their fake cursor. Containers with embedded inputs must propagate focus to the child input, or IME candidate windows appear in the wrong place. Hardware cursor visibility is controlled by `showHardwareCursor`, `setShowHardwareCursor(true)`, or `PI_HARDWARE_CURSOR=1`.

## Usage

In extensions:

```ts
pi.on("session_start", async (_event, ctx) => {
  const handle = ctx.ui.custom(myComponent);
  handle.requestRender();
  handle.close();
});
```

In custom tools, use `pi.ui.custom()` inside `execute` and close handles when done.

## Overlays

Pass `{ overlay: true }` to render on top of existing content. `overlayOptions` controls width, height, anchor, offsets, row/col, margins, and responsive visibility. Overlay handles support focus/unfocus, hide, and visibility toggles. Do not reuse disposed overlay component instances; create fresh ones for each show.

## Built-ins

Import `Text`, `Box`, `Container`, `Spacer`, `Markdown`, `Input`, `Editor`, `SelectList`, `SettingsList`, `BorderedLoader`, and helpers from `@earendil-works/pi-tui`. Prefer existing components for selectors, settings/toggles, loaders, markdown, and layout before building custom primitives.

## Theming Rules

Use the theme object passed into callbacks; do not import a global theme. Implement `invalidate()` so theme changes clear cached styled output. Use explicit color callback parameters such as `(s: string) => theme.fg("accent", s)`.

## Key Rules

- Always respect `render(width)`.
- Implement `invalidate()` on custom components and child trees.
- Propagate focus for embedded inputs.
- Use overlays for temporary panels/dialogs.
- Guard TUI features when running in non-TUI modes.
