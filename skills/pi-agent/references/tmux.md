# tmux Setup

Source: https://pi.dev/docs/latest/tmux

tmux strips modifier information from some keys by default. Without configuration, Shift+Enter and Ctrl+Enter are often indistinguishable from Enter.

## Recommended Configuration

For tmux 3.5+:

```tmux
set -g extended-keys on
set -g extended-keys-format csi-u
```

Restart tmux fully:

```bash
tmux kill-server
tmux
```

With tmux 3.2 through 3.4, omit `extended-keys-format csi-u`; Pi still supports tmux's default xterm modifyOtherKeys format.

## What It Fixes

With CSI-u forwarding, modified Enter keys arrive distinctly:

- Enter: ``
- Shift+Enter: `[13;2u`
- Ctrl+Enter: `[13;5u`
- Alt/Option+Enter: `[13;3u`

This affects default Enter submit, Shift+Enter newline, and custom keybindings.
