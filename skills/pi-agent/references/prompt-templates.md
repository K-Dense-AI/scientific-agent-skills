# Prompt Templates

Source: https://pi.dev/docs/latest/prompt-templates

Prompt templates are Markdown snippets that expand into full prompts. Invoke them by typing `/name` where `name` is the filename without `.md`.

## Locations

- Global: `~/.pi/agent/prompts/*.md`
- Project: `.pi/prompts/*.md` after project trust
- Packages: `prompts/` directories or `pi.prompts` manifest entries
- Settings: `prompts` array with files/directories
- CLI: `--prompt-template`, repeatable

Disable discovery with `--no-prompt-templates`.

## Format

```md
---
description: Review staged git changes
argument-hint: "[focus]"
---
Review the staged changes (`git diff --cached`). Focus on: $ARGUMENTS
```

The description is optional; if missing, Pi uses the first non-empty line. `argument-hint` appears in autocomplete.

## Arguments

- `$1`, `$2`: positional args.
- `$@` or `$ARGUMENTS`: all args joined.
- `${1:-default}`: default value.
- `${@:N}`: args from N.
- `${@:N:L}`: L args starting at N.

Discovery in `prompts/` is non-recursive unless subdirectories are explicitly configured in settings or package manifest.
