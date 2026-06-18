# Skills

Source: https://pi.dev/docs/latest/skills

Pi implements the Agent Skills standard. Skills are self-contained capability packages loaded on demand. They provide instructions, workflows, scripts, and references.

## Locations

Global:

- `~/.pi/agent/skills/`
- `~/.agents/skills/`

Project, after project trust:

- `.pi/skills/`
- `.agents/skills/` in cwd and ancestors up to git root or filesystem root

CLI `--skill` is repeatable and loads additively even with `--no-skills`.

## Discovery

Directories containing `SKILL.md` are discovered recursively in all skill locations. In `~/.pi/agent/skills/` and `.pi/skills/`, direct root `.md` files are individual skills. In `.agents/skills`, root `.md` files are ignored.

## How Skills Work

At startup Pi scans skills and extracts names/descriptions. The system prompt includes available skills. The agent should read the full `SKILL.md` when a task matches; users can force with `/skill:name`.

## Skill Commands

Skills register as `/skill:name`. Arguments after the command are appended as `User: ...`. Enable/disable with `enableSkillCommands`.

## Structure

```text
my-skill/
  SKILL.md
  scripts/process.sh
  references/api-reference.md
  assets/template.json
```

Use relative paths from the skill directory.

## Frontmatter

Required: `name` and `description`. Optional: `license`, `compatibility`, `metadata`, `allowed-tools`, `disable-model-invocation`.

Name rules: 1-64 chars, lowercase letters/numbers/hyphens, no leading/trailing hyphens, no consecutive hyphens. Pi warns on most spec violations but does not require the name to match parent directory. Missing description prevents loading.

## Security

Skills can instruct the model to perform any action and may include executable code. Review third-party skills before use.
