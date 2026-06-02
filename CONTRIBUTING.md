# Contributing Skills

Thanks for helping improve Scientific Agent Skills. This guide explains how to add or update a skill in this repository while following the open [Agent Skills specification](https://agentskills.io/specification).

## Ways to Contribute

- Add a new scientific package, database, platform, workflow, or research method skill.
- Improve an existing skill with clearer instructions, current APIs, better examples, references, or scripts.
- Fix outdated examples, broken install steps, security issues, or documentation gaps.
- Report bugs or request new skills through GitHub Issues.

## Skill Location

All repository skills live under `skills/`:

```text
skills/
└── skill-name/
    ├── SKILL.md
    ├── references/
    ├── scripts/
    └── assets/
```

Only `SKILL.md` is required. Use optional directories when they make the skill easier to maintain:

- `references/` for longer documentation that agents should read only when needed.
- `scripts/` for executable helpers, validators, or reusable workflow code.
- `assets/` for templates, static resources, or example data.

Keep references one level deep from `SKILL.md` where possible, and keep the main `SKILL.md` concise. The Agent Skills specification recommends keeping `SKILL.md` under 500 lines and using progressive disclosure for longer material.

## Required Skill Format

Every skill must be a directory containing a `SKILL.md` file with YAML frontmatter followed by Markdown instructions.

Use this minimum template:

```markdown
---
name: skill-name
description: Clear description of what the skill does and when an agent should use it.
metadata:
  version: "1.0"
---

# Skill Title

## When to Use

Use this skill when...

## Workflow

1. ...
2. ...

## Examples

...
```

### Frontmatter Requirements

Follow the [Agent Skills specification](https://agentskills.io/specification) and this repository's conventions:

- `name` is required, must match the parent directory name, and must be 1-64 characters.
- `name` may contain only lowercase letters, numbers, and hyphens.
- `name` must not start or end with a hyphen and must not contain consecutive hyphens.
- `description` is required, non-empty, and must be at most 1024 characters.
- `description` should explain both what the skill does and when an agent should use it.
- `metadata.version` is required in this repository, even though `metadata` is optional in the upstream spec.
- Version values must be quoted numeric strings, such as `"1.0"` or `"1.1"`.

Optional frontmatter fields from the specification may be used when relevant:

- `license`: the license for the individual skill, if different or worth stating explicitly.
- `compatibility`: environment requirements such as Python version, system packages, agent host, or network access.
- `metadata`: additional string key-value metadata.
- `allowed-tools`: space-separated tool permissions for hosts that support this experimental field.

## Versioning

Every `SKILL.md` must include:

```yaml
metadata:
  version: "1.0"
```

For a new skill, start at `"1.0"`.

When updating an existing skill, increment `metadata.version` in the same pull request:

- Use a minor bump for normal improvements, for example `"1.0"` to `"1.1"`.
- Use a major bump only for a breaking change or substantial redesign, for example `"1.9"` to `"2.0"`.

## Writing a Good Skill

Good skills are specific, practical, and easy for an agent to apply.

- Write the `description` in third person with useful trigger terms.
- Include concrete workflows, commands, and examples instead of broad background explanations.
- Prefer current official APIs, docs, and installation instructions.
- Document required Python packages, system dependencies, credentials, or network access.
- Include scientific best practices, caveats, and validation checks where they matter.
- Move long API details, tables, and extended examples into `references/`.
- Use scripts for fragile or repetitive logic instead of asking the agent to recreate it every time.
- Avoid secrets, credentials, API keys, private URLs, and unpublished data.

## Adding a New Skill

1. Fork the repository and create a branch:

   ```bash
   git checkout -b add-skill-name
   ```

2. Create a new directory under `skills/` whose name matches the skill name:

   ```text
   skills/skill-name/
   ```

3. Add `SKILL.md` with valid frontmatter, including `metadata.version`.

4. Add supporting `references/`, `scripts/`, or `assets/` only when they are useful.

5. Test any commands, code examples, and scripts included in the skill.

6. Update related documentation if the new skill changes repository-level lists, examples, or setup guidance.

7. Run validation and security checks before opening a pull request.

## Updating an Existing Skill

1. Read the current `SKILL.md` and any supporting files.
2. Check upstream package, API, or platform documentation for current behavior.
3. Make the smallest useful change that fixes or improves the skill.
4. Increment `metadata.version`.
5. Test changed examples, commands, and scripts.
6. Note any behavior changes in the pull request description.

## Validation

Validate Agent Skills format with the reference validator:

```bash
skills-ref validate ./skills/skill-name
```

If `skills-ref` is not installed, follow the installation instructions from the [skills-ref reference library](https://github.com/agentskills/agentskills/tree/main/skills-ref).

Security-scan new or substantially changed skills:

```bash
uv pip install cisco-ai-skill-scanner
skill-scanner scan ./skills/skill-name --use-behavioral
```

A clean scan reduces review noise but does not replace manual review.

## Pull Request Checklist

Before submitting a pull request, confirm:

- The skill directory name and `name` frontmatter match exactly.
- `SKILL.md` has valid YAML frontmatter and Markdown body content.
- `metadata.version` exists and is quoted.
- Existing skills have a version bump when changed.
- The `description` clearly says what the skill does and when to use it.
- Examples and scripts have been tested or clearly marked as illustrative.
- No secrets, credentials, private data, or unsafe instructions are included.
- Relevant official documentation is linked where useful.
- Security scanner results are clean or explained in the pull request.

## Pull Request Process

1. Push your branch to your fork.
2. Open a pull request with a clear title, such as `Add scanpy workflow examples` or `Update astropy skill for current API`.
3. Describe what changed, why it matters, and how you tested it.
4. Link related issues, package documentation, release notes, or security findings.
5. Respond to review comments and update the skill as needed.

Thank you for helping make scientific computing more accessible to AI agents and researchers.
