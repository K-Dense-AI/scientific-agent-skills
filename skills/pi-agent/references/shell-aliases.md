# Shell Aliases

Source: https://pi.dev/docs/latest/shell-aliases

Reviewed against Pi 0.99.2 on 2026-09-30.

Pi normally runs a separate non-interactive `bash -c` for each built-in Bash or `!`/`!!` command. To use aliases, create a Bash-compatible `~/.bash_aliases`:

```bash
alias ll='ls -la'
alias gs='git status --short'
```

Then configure `~/.pi/agent/settings.json`:

```json
{
  "shellCommandPrefix": "shopt -s expand_aliases\nsource ~/.bash_aliases"
}
```

Run `/reload`, then `!ll`. The prefix runs before every Bash command. Do not parse/evaluate arbitrary alias lines from `.zshrc` or source a zsh configuration into Bash. Configure `shellPath` when Bash is unavailable; `shopt` will fail under a `sh` fallback. Extensions replacing the shell own their setup.
