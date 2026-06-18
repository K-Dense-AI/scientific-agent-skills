# Terminal Setup

Source: https://pi.dev/docs/latest/terminal-setup

Pi uses the Kitty keyboard protocol for reliable modifier detection. Most modern terminals support it; some need setup.

## Works Out of Box

Kitty and iTerm2 work out of the box. Apple Terminal uses enhanced key reporting when available and a local macOS fallback for Shift+Enter when running on the same Mac.

## Ghostty

Add:

```text
keybind = alt+backspace=text:
```

Remove older `shift+enter=text:
` mappings unless needed for other tools. If keeping that mapping for tmux, add `ctrl+j` to Pi's newline keybinding.

## WezTerm

Usually works. To force Kitty keyboard:

```lua
local wezterm = require 'wezterm'
local config = wezterm.config_builder()
config.enable_kitty_keyboard = true
return config
```

On macOS, remap Option+Enter to send `[13;3u` if you want follow-up queueing.

## Alacritty

On macOS, add Alt+Enter binding to send `[13;3u`.

## VS Code Integrated Terminal

VS Code 1.109.5+ enables Kitty keyboard by default. Older versions need a Shift+Enter `workbench.action.terminal.sendSequence` keybinding sending `[13;2u`.

## Windows Terminal

Add actions for Shift+Enter (`[13;2u`) and Alt+Enter (`[13;3u`). Fully restart if old fullscreen behavior persists.

## Limited Terminals

xfce4-terminal, terminator, and IntelliJ's integrated terminal cannot distinguish modified Enter keys reliably. Use a terminal with Kitty keyboard support for the best experience.
