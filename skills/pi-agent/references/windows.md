# Windows Setup

Source: https://pi.dev/docs/latest/windows

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

On native Windows, Pi supports both `bash` and a dedicated `powershell` tool (PowerShell 7 when available, then Windows PowerShell). Select it explicitly with `"defaultTools": ["-bash", "+powershell"]`; `!` and `!!` commands still use Bash. For Bash execution, Pi checks, in order:

1. Custom path from `~/.pi/agent/settings.json`
2. Git Bash (`C:\Program Files\Git\bin\bash.exe`)
3. `bash.exe` on PATH (Cygwin, MSYS2, WSL)

[Git for Windows](https://git-scm.com/download/win) is sufficient for most users.

## Custom Shell Path

```json
{
  "shellPath": "C:\\cygwin64\\bin\\bash.exe"
}
```

The value is JSON, so each literal backslash in the Windows path must be doubled.

Related Windows notes: Ctrl+Enter for multi-line input, Alt+V to paste images, `app.suspend` has no default binding (`references/keybindings.md`), and the default follow-up shortcut is Ctrl+Q (Alt+Q dequeues); remap Alt+Enter only if explicitly binding it instead of fullscreen (`references/terminal-setup.md`).
