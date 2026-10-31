# Prompt Templates

Source: https://pi.dev/docs/latest/prompt-templates

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Prompt templates are Markdown snippets that expand into full prompts. Type `/name` in the editor, where `name` is the filename without `.md` (`review.md` → `/review`).

## Locations

- Global: `~/.pi/agent/prompts/*.md`
- Project: `.pi/prompts/*.md` (only after project trust)
- Packages: `prompts/` directories or `pi.prompts` entries in `package.json`
- Settings: `prompts` array with files or directories
- CLI: `--prompt-template <path>` (repeatable)

Disable discovery with `--no-prompt-templates`.

## Format

```md
---
description: Review staged git changes
argument-hint: "<PR-URL>"
---
Review the staged changes (`git diff --cached`). Focus on: $ARGUMENTS
```

`description` is optional — without it Pi uses the first non-empty line. `argument-hint` is optional and shown **before** the description in the autocomplete dropdown; use `<angle brackets>` for required arguments and `[square brackets]` for optional ones.

## Usage

```text
/review                           # expands review.md
/component Button                 # one argument
/component Button "click handler"  # multiple arguments
```

## Arguments

- `$1`, `$2`, … positional
- `$@` or `$ARGUMENTS` all arguments joined
- `${1:-default}` argument 1 when present and non-empty, otherwise the default
- `${@:-default}` or `${ARGUMENTS:-default}` all arguments when present, otherwise the default
- `${@:N}` arguments from the Nth position (1-indexed)
- `${@:N:L}` `L` arguments starting at N

## Loading Rules

Discovery in `prompts/` is non-recursive. Templates in subdirectories must be added explicitly through the `prompts` setting or a package manifest.
