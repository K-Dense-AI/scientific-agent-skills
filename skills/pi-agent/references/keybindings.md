# Keybindings

Source: https://pi.dev/docs/latest/keybindings

All shortcuts can be customized in `~/.pi/agent/keybindings.json`. Run `/reload` after editing.

## Key Format

Use `modifier+key`; modifiers are `ctrl`, `shift`, and `alt`. Keys include letters, digits, special keys, function keys, and symbols.

## Common Defaults

Editor movement: arrows, Ctrl+B/F, Alt+Left/Right, Ctrl+A/E, PageUp/PageDown.

Deletion: Backspace, Delete/Ctrl+D, Ctrl+W, Alt+Backspace, Alt+D, Ctrl+U, Ctrl+K.

Input: `tui.input.submit` is Enter, `tui.input.newLine` is Shift+Enter, `tui.input.tab` is Tab.

Application: Escape interrupts, Ctrl+C clears editor/copies selection depending context, Ctrl+D exits when editor empty, Ctrl+G opens external editor, Ctrl+V/Alt+V pastes image.

Models: Ctrl+L opens model selector, Ctrl+P cycles forward, Shift+Ctrl+P cycles backward, Shift+Tab cycles thinking level, Ctrl+T toggles thinking block display.

Messages: Ctrl+O expands tools, Alt+Enter queues follow-up, Alt+Up retrieves queued messages.

## Custom Config

```json
{
  "tui.editor.cursorUp": ["up", "ctrl+p"],
  "tui.editor.cursorDown": ["down", "ctrl+n"],
  "tui.editor.deleteWordBackward": ["ctrl+w", "alt+backspace"]
}
```

User config overrides defaults. Native Windows has no default `app.suspend` binding; WSL uses normal Unix Ctrl+Z/fg behavior.
