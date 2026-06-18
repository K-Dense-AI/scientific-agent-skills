# Termux Setup

Source: https://pi.dev/docs/latest/termux

Pi runs on Android through Termux.

## Prerequisites

Install Termux from GitHub or F-Droid, not Google Play. Install Termux:API for clipboard and device integrations.

## Install

```bash
pkg update && pkg upgrade
pkg install nodejs termux-api git
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
mkdir -p ~/.pi/agent
pi
```

## Clipboard

Pi uses `termux-clipboard-set` and `termux-clipboard-get` when available. Image clipboard is not supported in Termux.

## Useful `AGENTS.md` Context

Add Termux environment notes to `~/.pi/agent/AGENTS.md`: OS is Android/Termux, home is `/data/data/com.termux/files/home`, prefix is `/data/data/com.termux/files/usr`, shared storage is `/storage/emulated/0`, use `termux-open-url`, `termux-open`, `termux-share`, `termux-notification`, and clipboard commands where appropriate.

## Limitations and Troubleshooting

No image clipboard. Some optional native binaries may be unavailable on Android ARM64. Run `termux-setup-storage` once for `/storage/emulated/0`. If npm fails, try `npm cache clean --force`.
