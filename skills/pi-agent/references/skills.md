# Skills

Source: https://pi.dev/docs/latest/skills

Reviewed against Pi 0.99.2 and the package versions listed in `../SKILL.md` on 2026-09-30.

Pi implements the [Agent Skills standard](https://agentskills.io/specification). Skills are self-contained capability packages loaded on demand, providing workflows, setup instructions, helper scripts, and reference documentation. Pi warns about most spec violations but stays lenient — notably it allows a skill name that differs from its parent directory, because the standard's matching rule is awkward for skill directories shared across harnesses.

## Locations

Global:

- `~/.pi/agent/skills/`
- `~/.agents/skills/`

Project, only after project trust:

- `.pi/skills/`
- `.agents/skills/` in cwd and ancestors, up to the git repo root (or filesystem root outside a repo)

Also: packages (`skills/` directories or `pi.skills` entries in `package.json`), the `skills` settings array, and CLI `--skill <path>` (repeatable, additive even with `--no-skills`).

Discovery rules:

- In `~/.pi/agent/skills/` and `.pi/skills/`, direct root `.md` files are discovered as individual skills.
- In all locations, directories containing `SKILL.md` are discovered recursively.
- In `~/.agents/skills/` and project `.agents/skills/`, root `.md` files are ignored.

To reuse skills from other harnesses, add their directories to settings:

```json
{ "skills": ["~/.claude/skills", "~/.codex/skills"] }
```

## How Skills Work

At startup Pi scans skill locations and extracts names and descriptions. The system prompt includes available skills in XML format per the specification. When a task matches, the agent uses `read` to load the full `SKILL.md` (models do not always do this — prompt explicitly or force with `/skill:name`) and follows the instructions using relative paths. Only descriptions stay in context; full instructions load on demand.

## Skill Commands

Skills register as `/skill:name`; arguments after the command are appended as `User: <args>`. Toggle via `/settings` or `"enableSkillCommands": true`.

```bash
/skill:brave-search
/skill:pdf-tools extract
```

## Structure

```text
my-skill/
  SKILL.md          # required: frontmatter + instructions
  scripts/process.sh
  references/api-reference.md
  assets/template.json
```

Use relative paths from the skill directory.

## Frontmatter

| Field | Required | Constraints |
|---|---|---|
| `name` | Yes | Max 64 chars, lowercase a–z, 0–9, hyphens. Pi does not require it to match the parent directory. |
| `description` | Yes | Max 1024 chars — what the skill does and when to use it. |
| `license` | No | License name or reference to a bundled file. |
| `compatibility` | No | Max 500 chars; environment requirements. |
| `metadata` | No | Arbitrary key-value mapping. |
| `allowed-tools` | No | Space-delimited pre-approved tools (experimental). |
| `disable-model-invocation` | No | `true` hides the skill from the system prompt; users must call `/skill:name`. |

Name rules: 1–64 characters, lowercase letters/numbers/hyphens, no leading or trailing hyphen, no consecutive hyphens. Valid: `pdf-processing`. Invalid: `PDF-Processing`, `-pdf`, `pdf--processing`.

`disable-model-invocation` and lenient directory-name handling are Pi-specific behavior, not portable Agent Skills conformance. Skills in this repository must use only the six standard fields and must match the parent directory name; do not add that Pi-only field here.

## Validation

Most violations warn but still load: over-length or invalid names, leading/trailing/consecutive hyphens, description over 1024 chars. Unknown frontmatter fields are ignored. **Exception:** a missing description prevents loading. Name collisions across locations warn and keep the first skill found.

## Security

Skills can instruct the model to perform any action and may include executable code the model invokes. Review skill content before use.

## Skill Repositories

- [Anthropic Skills](https://github.com/anthropics/skills) — document processing, web development
- [Pi Skills](https://github.com/badlogic/pi-skills) — web search, browser automation, Google APIs, transcription
