# Shell Aliases

Source: https://pi.dev/docs/latest/shell-aliases

Pi runs bash in non-interactive mode (`bash -c`), so aliases do not expand by default.

To enable aliases, set `shellCommandPrefix` in `~/.pi/agent/settings.json`:

```json
{
  "shellCommandPrefix": "shopt -s expand_aliases
eval "$(grep '^alias ' ~/.zshrc)""
}
```

Adjust the shell config path for `.zshrc`, `.bashrc`, or your environment.
