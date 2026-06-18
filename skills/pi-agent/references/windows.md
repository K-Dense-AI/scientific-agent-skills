# Windows Setup

Source: https://pi.dev/docs/latest/windows

Pi requires a bash shell on Windows. It checks, in order:

1. Custom path from `~/.pi/agent/settings.json`.
2. Git Bash: `C:\Program Files\Gitinash.exe`.
3. `bash.exe` on PATH, such as Cygwin, MSYS2, or WSL.

Git for Windows is sufficient for most users.

## Custom Shell Path

```json
{
  "shellPath": "C:\cygwin64\bin\bash.exe"
}
```
