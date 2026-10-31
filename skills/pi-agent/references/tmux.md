# tmux Setup

Source: https://pi.dev/docs/latest/tmux

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

tmux strips modifier information from some keys by default, so without configuration `Shift+Enter` and `Ctrl+Enter` are indistinguishable from plain `Enter`.

## Recommended Configuration

Add to `~/.tmux.conf`:

```tmux
set -g extended-keys on
set -g extended-keys-format csi-u
```

Save work and close existing sessions before restarting. `tmux kill-server` terminates every session on that server:

```bash
tmux kill-server
tmux
```

Pi requests extended key reporting automatically when the Kitty keyboard protocol is unavailable. `extended-keys-format csi-u` requires **tmux 3.5 or later** (check with `tmux -V`). With tmux 3.2–3.4, omit that line; Pi still supports tmux's default xterm `modifyOtherKeys` format.

## Why csi-u

With only `set -g extended-keys on`, tmux defaults to `extended-keys-format xterm` and forwards modified keys as `modifyOtherKeys` sequences — `Ctrl+C` as `ESC [27;5;99~`, `Ctrl+Enter` as `ESC [27;5;13~`. With `csi-u` the same keys arrive as `ESC [99;5u` and `ESC [13;5u`. Pi supports both formats; `csi-u` is the recommended setup.

## What It Fixes

`ESC` below is the escape byte (`0x1b`).

| Key | Without extended keys | With `csi-u` |
|---|---|---|
| Enter | `CR` | `CR` |
| Shift+Enter | `CR` | `ESC [13;2u` |
| Ctrl+Enter | `CR` | `ESC [13;5u` |
| Alt/Option+Enter | `ESC CR` | `ESC [13;3u` |

This affects the default bindings (Enter to submit, Shift+Enter for newline) and any custom keybindings using modified Enter.

## Requirements

tmux 3.5+ for `extended-keys-format csi-u`, plus a terminal emulator that supports extended keys: Ghostty, Kitty, iTerm2, WezTerm, or Windows Terminal.
