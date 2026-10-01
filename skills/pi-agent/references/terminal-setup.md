# Terminal Setup

Source: https://pi.dev/docs/latest/terminal-setup

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Pi uses the [Kitty keyboard protocol](https://sw.kovidgoyal.net/kitty/keyboard-protocol/) for reliable modifier detection. Most modern terminals support it; some need configuration.

## Works Out of the Box

Kitty and iTerm2 (regular TUI mode). Apple Terminal enables enhanced key reporting when available; if it still sends plain Return for `Shift+Enter`, Pi uses a local macOS modifier fallback — which only works when Pi runs on the same Mac, not over SSH. VS Code 1.109.5+ also works by default.

### iTerm2 in fullscreen TUI mode

Pi owns the viewport, so iTerm2 sends mouse-wheel reports instead of scrolling its native scrollback. With iTerm2's default fast-trackpad behavior those reports can lose most of an accelerated wheel delta. If fast gestures move only ~one line at a time, open **iTerm2 → Settings → Advanced**, find **Trackpad scrolls fast?** and set it to **No**. This is an iTerm2-wide workaround (tracked in iTerm2 issue 9619). Inline images also render as text placeholders in fullscreen mode because iTerm2's inline-image protocol cannot delete or crop placements during application-owned scrolling.

## Ghostty

Config at `~/Library/Application Support/com.mitchellh.ghostty/config` (macOS) or `~/.config/ghostty/config` (Linux):

```text
keybind = alt+backspace=text:\x1b\x7f
```

Older Claude Code versions may have added `keybind = shift+enter=text:\n`. That sends a raw linefeed, which inside Pi is indistinguishable from `Ctrl+J`, so tmux and Pi no longer see a real `shift+enter` event. Remove it unless you still need it for Claude Code in tmux. Pi binds `Ctrl+J` as a default newline alias, so `Shift+Enter` keeps working through that remap without extra Pi configuration.

In fullscreen TUI mode links stay clickable, but Ghostty hides its hover underline and lower-left URL preview while Pi captures mouse input. Hold `Shift+Command` (macOS) or `Shift+Ctrl` (Linux) for Ghostty's native link handling.

## WezTerm

Usually works via xterm `modifyOtherKeys`. To force the Kitty protocol, in `~/.wezterm.lua`:

```lua
local wezterm = require 'wezterm'
local config = wezterm.config_builder()
config.enable_kitty_keyboard = true
return config
```

On macOS `Option+Enter` is bound to fullscreen; to use it for follow-up queueing add to `config.keys`:

```lua
{ key = 'Enter', mods = 'ALT', action = wezterm.action.SendString('\x1b[13;3u') }
```

On WSL, WezTerm may need a visible hardware cursor for IME candidate positioning — set `PI_HARDWARE_CURSOR=1` or `showHardwareCursor: true`.

## Alacritty

Usually works for `Shift+Enter`. On macOS `Option+Enter` may arrive as plain `Enter`; add to `~/.config/alacritty/alacritty.toml` and restart:

```toml
[[keyboard.bindings]]
key = "Enter"
mods = "Alt"
chars = "\u001b[13;3u"
```

## VS Code Integrated Terminal

1.109.5+ enables the Kitty protocol by default. Older versions need an explicit `keybindings.json` entry (macOS `~/Library/Application Support/Code/User/keybindings.json`, Linux `~/.config/Code/User/keybindings.json`, Windows `%APPDATA%\Code\User\keybindings.json`):

```json
{
  "key": "shift+enter",
  "command": "workbench.action.terminal.sendSequence",
  "args": { "text": "\u001b[13;2u" },
  "when": "terminalFocus"
}
```

## Windows Terminal

Add to `settings.json` (Ctrl+Shift+, then Open JSON file) so the modified Enter keys reach Pi:

```json
{
  "actions": [
    { "command": { "action": "sendInput", "input": "\u001b[13;2u" }, "keys": "shift+enter" },
    { "command": { "action": "sendInput", "input": "\u001b[13;3u" }, "keys": "alt+enter" }
  ]
}
```

Windows/WSL now use Ctrl+Q for follow-up by default. Windows Terminal binds `Alt+Enter` to fullscreen; the optional remap above is useful only when you also bind Pi follow-up to Alt+Enter. Fully close and reopen Windows Terminal if the old fullscreen behavior persists.

## Limited Terminals

xfce4-terminal, terminator, and IntelliJ IDEA's integrated terminal cannot distinguish modified Enter keys from plain Enter, so bindings such as `submit: ["ctrl+enter"]` will not work. Prefer a terminal with Kitty keyboard support: Kitty, Ghostty, WezTerm, iTerm2, or Alacritty compiled with Kitty protocol support. In IntelliJ, set `PI_HARDWARE_CURSOR=1` if you want the hardware cursor visible (off by default for compatibility).
