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
metadata: {"version": "1.0", "skill-author": "Your Name"}
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
- **Write `metadata` as a single-line JSON object** (flow style), for example `metadata: {"version": "1.0", "skill-author": "K-Dense Inc."}`. This is valid YAML — so it parses identically in Claude Code, Cursor, Codex, Hermes, Pi, and any Agent Skills-compliant host — and it is the only form OpenClaw's line-based frontmatter reader can parse (a multi-line block `metadata:` is silently dropped there). Do not use a nested `metadata:` block.

Optional frontmatter fields from the specification may be used when relevant:

- `license`: the license for the individual skill, if different or worth stating explicitly.
- `compatibility`: environment requirements such as Python version, system packages, agent host, or network access.
- `metadata`: additional metadata. Must be a single-line JSON object (see above). Common keys: `version` (required), `skill-author`, an optional `openclaw` block, and an optional `hermes` block (see below).
- `allowed-tools`: space-separated tool permissions for hosts that support this experimental field.
- `required_environment_variables`: top-level Hermes credential declarations (see below). Other hosts ignore it.

### OpenClaw gating (`metadata.openclaw`)

OpenClaw reads an optional `openclaw` object nested inside `metadata` for dependency gating, credential injection, and display. Because it lives under `metadata`, the Agent Skills spec permits it and other hosts ignore it. It is only needed for skills with external requirements (credentials, daemons, specific binaries) — most skills omit it entirely. Supported keys:

- `requires`: hard eligibility gates — `{"bins": [...]}` (all must be on `PATH`), `{"anyBins": [...]}` (at least one), `{"env": [...]}` (vars that must be set), `{"config": [...]}`. A failed gate hides the skill from the agent, so only gate on things the skill genuinely cannot run without.
- `primaryEnv`: the main credential variable; OpenClaw injects it from its config (`skills.entries.<name>.apiKey`).
- `envVars`: descriptive (non-gating) declarations — `[{"name": "X_API_KEY", "required": true, "description": "..."}]`. Declare every env var your scripts reference so ClawHub's security analysis does not flag a metadata mismatch.
- `os`: platform filter, e.g. `["darwin", "linux"]`.
- `emoji`, `homepage`: display only.

Example (an API-key skill that stays available even without the key set, so it gates nothing and only declares the credential):

```yaml
metadata: {"version": "1.0", "skill-author": "K-Dense Inc.", "openclaw": {"primaryEnv": "EXA_API_KEY", "envVars": [{"name": "EXA_API_KEY", "required": true, "description": "Exa search API key."}]}}
```

### Hermes compatibility (`required_environment_variables` and `metadata.hermes`)

[Hermes](https://hermes-agent.nousresearch.com/docs) is Agent Skills-compatible, so every skill in this repository already loads and runs there with no changes. Two optional fields make credentialed skills first-class on Hermes:

- **`required_environment_variables`** (top level): the credentials Hermes should prompt for. Write it as a single-line JSON array — `[{"name": "X_API_KEY", "prompt": "What it is", "required_for": "full functionality"}]`. This is the one Hermes-specific field that is *not* nested under `metadata`, because Hermes reads secrets at the top level. Writing it as single-line JSON keeps it valid YAML for every host and lets OpenClaw's line-based reader skip it cleanly; Claude Code, Cursor, and Codex ignore the unknown key. Mirror the same variables you declare in `metadata.openclaw.envVars`, using `required_for: "full functionality"` for required vars and `"optional features"` for optional ones.
- **`metadata.hermes`** (nested, spec-safe like `openclaw`): optional classification and gating — `tags`, `category`, `requires_toolsets`, `fallback_for_toolsets`. A failed `requires_toolsets` gate *hides* the skill, so only gate on a tool the skill genuinely cannot run without; prefer leaving it unset so the skill stays available.

Example (an API-key skill, declaring its credential for Hermes alongside the OpenClaw block):

```yaml
required_environment_variables: [{"name": "EXA_API_KEY", "prompt": "Exa search API key.", "required_for": "full functionality"}]
metadata: {"version": "1.0", "skill-author": "Exa", "openclaw": {"primaryEnv": "EXA_API_KEY", "envVars": [{"name": "EXA_API_KEY", "required": true, "description": "Exa search API key."}]}}
```

## Versioning

Every `SKILL.md` must include a quoted `version` inside the single-line `metadata` object:

```yaml
metadata: {"version": "1.0"}
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
- `metadata` is a single-line JSON object (not a multi-line block), so it parses on OpenClaw as well as Claude Code, Cursor, Codex, Hermes, and Pi.
- If the skill needs credentials, `required_environment_variables` is present as a single-line JSON array and mirrors the variables in `metadata.openclaw.envVars`.
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
