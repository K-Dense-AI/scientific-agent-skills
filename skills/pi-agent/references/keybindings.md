# Keybindings

Source: https://pi.dev/docs/latest/keybindings

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

All shortcuts are customizable in `~/.pi/agent/keybindings.json`, which uses the same namespaced ids Pi uses internally and that extension authors pass to `keyHint()` and the injected `keybindings` manager. Pre-namespaced ids from older configs (`cursorUp`, `expandTools`, …) migrate automatically on startup. Run `/reload` after editing.

## Key Format

`modifier+key` where modifiers are `ctrl`, `shift`, `alt`, `super` (combinable, e.g. `ctrl+shift+x`, `alt+ctrl+1`, `super+k`, `ctrl+super+k`). `super` bindings need a terminal that reports the modifier separately, typically via the Kitty keyboard protocol. Keys:

- Letters `a-z`, digits `0-9`
- Special: `escape`/`esc`, `enter`/`return`, `tab`, `space`, `backspace`, `delete`, `insert`, `clear`, `home`, `end`, `pageUp`, `pageDown`, `up`, `down`, `left`, `right`
- Function: `f1`–`f12`
- Symbols: `` ` ``, `-`, `=`, `[`, `]`, `\`, `;`, `'`, `,`, `.`, `/`, `!`, `@`, `#`, `$`, `%`, `^`, `&`, `*`, `(`, `)`, `_`, `+`, `|`, `~`, `{`, `}`, `:`, `<`, `>`, `?`

## Actions

**`tui.editor.*` cursor** — `cursorUp` (up; browses older history at the top), `cursorDown` (down; browses newer history at the bottom), `historyPrevious` / `historyNext` (no defaults), `cursorLeft` (left, ctrl+b), `cursorRight` (right, ctrl+f), `cursorWordLeft` (alt+left, ctrl+left, alt+b), `cursorWordRight` (alt+right, ctrl+right, alt+f), `cursorLineStart` (home, ctrl+home, ctrl+a), `cursorLineEnd` (end, ctrl+end, ctrl+e), `jumpForward` (ctrl+]), `jumpBackward` (ctrl+alt+]), `pageUp` (pageUp, ctrl+pageUp), `pageDown` (pageDown, ctrl+pageDown).

The dedicated `historyPrevious`/`historyNext` actions always change history entries regardless of cursor position in a multiline prompt, and explicit history bindings take precedence over application actions while the main editor is focused — binding `tui.editor.historyPrevious` to `ctrl+p` overrides model cycling in that context without changing `Ctrl+P` in selectors.

**`tui.editor.*` deletion** — `deleteCharBackward` (backspace), `deleteCharForward` (delete, ctrl+d), `deleteWordBackward` (ctrl+w, alt+backspace), `deleteWordForward` (alt+d, alt+delete), `deleteToLineStart` (ctrl+u), `deleteToLineEnd` (ctrl+k).

**`tui.editor.*` kill ring** — `yank` (ctrl+y), `yankPop` (alt+y), `undo` (ctrl+-, ctrl+z on native Windows, alt+z on WSL).

**`tui.input.*`** — `newLine` (shift+enter, ctrl+j), `submit` (enter), `tab` (tab), `copy` (ctrl+c).

**`tui.select.*`** — `up`, `down`, `pageUp`, `pageDown`, `confirm` (enter), `cancel` (escape, ctrl+c).

**`tui.altScreen.*` fullscreen viewport** (only in `--tui-mode fullscreen`) — `pageUp` (pageUp), `pageDown` (pageDown), `halfPageUp` / `halfPageDown` / `lineUp` / `lineDown` (no defaults), `previousPrompt` (ctrl+shift+up), `nextPrompt` (ctrl+shift+down), `search` (ctrl+shift+f), `searchNext` (enter, ctrl+g), `searchPrevious` (shift+enter, ctrl+shift+g), `searchClose` (escape), `top` (home), `bottom` (end).

These target the primary transcript scroll region and take precedence over editor bindings, so in fullscreen mode unmodified `home`/`end`/`pageUp`/`pageDown` drive the transcript while their `ctrl` variants still drive the editor; outside fullscreen both variants drive the editor. Rebind normally to change the routing (`"tui.altScreen.pageUp": "ctrl+pageUp"`), or set `[]` to disable a transcript shortcut. Mouse-wheel and two-finger input scroll the region under the pointer, OSC 8 hyperlinks open on click, and primary-button drag selects text and copies it (holding at an edge auto-scrolls).

**`app.*` application** — `interrupt` (escape), `clear` (ctrl+c; clears the editor first, exits on a second press), `exit` (ctrl+d when editor empty), `suspend` (ctrl+z; none on Windows), `editor.external` (ctrl+g), `clipboard.pasteImage` (ctrl+v; alt+v on Windows and WSL — pastes images or text).

**`app.session.*`** — `new`, `tree`, `fork`, `resume` (no defaults), `togglePath` (ctrl+p), `toggleSort` (ctrl+s), `toggleNamedFilter` (ctrl+n), `rename` (ctrl+r), `delete` (ctrl+d), `deleteNoninvasive` (ctrl+backspace).

**`app.model.*` / `app.thinking.*`** — `model.select` (ctrl+l), `model.cycleForward` (ctrl+p), `model.cycleBackward` (shift+ctrl+p), `thinking.cycle` (shift+tab), `thinking.toggle` (ctrl+t).

**`app.tools.*` / `app.message.*`** — `tools.expand` (ctrl+o), `message.copy` (ctrl+x), `message.followUp` (alt+enter, ctrl+q on Windows/WSL), `message.dequeue` (alt+up, alt+q on Windows/WSL).

**`app.tree.*`** — `foldOrUp` (ctrl+left, alt+left), `unfoldOrDown` (ctrl+right, alt+right), `editLabel` (shift+l), `toggleLabelTimestamp` (shift+t), `filter.default` (ctrl+d), `filter.noTools` (ctrl+t), `filter.userOnly` (ctrl+u), `filter.labeledOnly` (ctrl+l), `filter.all` (ctrl+a), `filter.cycleForward` (ctrl+o), `filter.cycleBackward` (shift+ctrl+o).

**`app.models.*`** (inside the `/scoped-models` selector) — `save` (ctrl+s), `enableAll` (ctrl+a), `clearAll` (ctrl+x), `toggleProvider` (ctrl+p), `reorderUp` (alt+up), `reorderDown` (alt+down).

## Custom Config

```json
{
  "tui.editor.historyPrevious": "ctrl+p",
  "tui.editor.historyNext": "ctrl+n",
  "tui.editor.deleteWordBackward": ["ctrl+w", "alt+backspace"]
}
```

Each action takes a single key or an array; user config overrides defaults. The docs include full Emacs and Vim example configs.

On native Windows, `app.suspend` has no default because Windows terminals lack Unix job control — bound manually, Pi shows a status message instead of suspending. WSL keeps normal `ctrl+z`/`fg` behavior.
