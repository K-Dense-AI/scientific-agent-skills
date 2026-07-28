# Contributing Skills

Thanks for helping improve Scientific Agent Skills. This guide explains how to add or update a skill in this repository while following the open [Agent Skills specification](https://agentskills.io/specification).

Participation in this project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to Contribute

- Add a new scientific package, database, platform, workflow, or research method skill.
- Improve an existing skill with clearer instructions, current APIs, better examples, references, or scripts.
- Fix outdated examples, broken install steps, security issues, or documentation gaps.
- Add or extend a skill's tests under `tests/<skill-name>/` (see [Tests](#tests)).
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

Those four are the only directories a skill may contain. Anything else — tests, fixtures, scratch data, generated output — belongs outside `skills/`.

Keep references one level deep from `SKILL.md` where possible, and keep the main `SKILL.md` concise. The Agent Skills specification recommends keeping `SKILL.md` under 500 lines and using progressive disclosure for longer material.

A skill directory holds only what an agent loads, so tests do not belong there. They live in the repository-level suite under `tests/<skill-name>/`, mirroring the skill directory name, with any fixtures in `tests/<skill-name>/fixtures/`. See [Tests](#tests).

## Required Skill Format

Every skill must be a directory containing a `SKILL.md` file with YAML frontmatter followed by Markdown instructions.

Use this minimum template:

```markdown
---
name: skill-name
description: Clear description of what the skill does and when an agent should use it.
metadata:
  version: "1.0"
  skill-author: Your Name
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
- **Only the six fields defined by the specification are allowed** at the top level: `name`, `description`, `license`, `compatibility`, `allowed-tools`, and `metadata`. The spec defines a closed set and the reference validator rejects any other top-level key, so everything else belongs under `metadata`.
- **Write `metadata` as a block mapping, not single-line JSON.** The reference validator parses frontmatter with `strictyaml`, which rejects JSON-style flow mappings. A flow mapping does not merely fail one check — the entire frontmatter fails to parse, so `name` and `description` become unreadable and the skill does not register.

  ```yaml
  # Wrong -- breaks the reference validator
  metadata: {"version": "1.0", "skill-author": "K-Dense Inc."}

  # Right
  metadata:
    version: "1.0"
    skill-author: K-Dense Inc.
  ```

Optional frontmatter fields from the specification may be used when relevant:

- `license`: the license for the individual skill, if different or worth stating explicitly.
- `compatibility`: environment requirements such as Python version, system packages, agent host, or network access. Maximum 500 characters.
- `metadata`: additional metadata, as a block mapping of string keys to string values. Quote any value that would otherwise parse as a number, boolean, or date (`version: "1.0"`, `last-reviewed: "2026-07-23"`). Common keys: `version` (required), `skill-author`, and an optional nested `openclaw` or `hermes` block (see below).
- `allowed-tools`: a **space-separated string** of tool permissions for hosts that support this experimental field, for example `allowed-tools: Read Write Edit Bash`. Not a YAML list.

### OpenClaw gating (`metadata.openclaw`)

OpenClaw reads an optional `openclaw` object nested inside `metadata` for dependency gating, credential injection, and display. Because it lives under `metadata`, the Agent Skills spec permits it and other hosts ignore it. It is only needed for skills with external requirements (credentials, daemons, specific binaries) — most skills omit it entirely.

**Keep this block a nested mapping — never a JSON string.** OpenClaw's `resolveOpenClawManifestBlock()` requires `typeof candidate === "object"`, so a stringified block silently disables gating and credential injection with no error. This is the one documented exception to the string-values rule for `metadata`, and it still passes `skills-ref validate`.

Supported keys:

- `requires`: hard eligibility gates — `{"bins": [...]}` (all must be on `PATH`), `{"anyBins": [...]}` (at least one), `{"env": [...]}` (vars that must be set), `{"config": [...]}`. A failed gate hides the skill from the agent, so only gate on things the skill genuinely cannot run without.
- `primaryEnv`: the main credential variable; OpenClaw injects it from its config (`skills.entries.<name>.apiKey`).
- `envVars`: descriptive (non-gating) declarations — `[{"name": "X_API_KEY", "required": true, "description": "..."}]`. Declare every env var your scripts reference so ClawHub's security analysis does not flag a metadata mismatch.
- `os`: platform filter, e.g. `["darwin", "linux"]`.
- `emoji`, `homepage`: display only.

Example (an API-key skill that stays available even without the key set, so it gates nothing and only declares the credential):

```yaml
metadata:
  version: "1.0"
  skill-author: K-Dense Inc.
  openclaw:
    primaryEnv: EXA_API_KEY
    envVars:
      - name: EXA_API_KEY
        required: true
        description: Exa search API key.
```

### Hermes compatibility (`required_environment_variables` and `metadata.hermes`)

[Hermes](https://hermes-agent.nousresearch.com/docs) is Agent Skills-compatible, so every skill in this repository already loads and runs there with no changes. Two optional fields make credentialed skills first-class on Hermes:

- **`metadata.hermes`** (nested, spec-safe like `openclaw`): optional classification and gating — `tags`, `category`, `requires_toolsets`, `fallback_for_toolsets`. A failed `requires_toolsets` gate *hides* the skill, so only gate on a tool the skill genuinely cannot run without; prefer leaving it unset so the skill stays available. Keep it a nested mapping, not a JSON string.

Example (an API-key skill, declaring its credential for OpenClaw and classifying itself for Hermes):

```yaml
metadata:
  version: "1.0"
  skill-author: Exa
  openclaw:
    primaryEnv: EXA_API_KEY
    envVars:
      - name: EXA_API_KEY
        required: true
        description: Exa search API key.
  hermes:
    category: research
```

### `required_environment_variables` is not used in this repository

Hermes also reads a **top-level** `required_environment_variables` array to prompt for credentials. That field cannot coexist with spec conformance: the specification defines a closed set of six top-level fields, so the reference validator rejects it outright — and because `strictyaml` fails the whole frontmatter block on an unknown-shaped document, the failure is not confined to that one key.

This repository therefore does not use it. Declare credentials in two spec-legal places instead:

- `compatibility` — a human- and agent-readable sentence naming the variables the skill needs.
- `metadata.openclaw.envVars` — the machine-readable declaration, which ClawHub's security analysis also checks against the variables your scripts actually reference.

Skills still load and run on Hermes; only its automatic credential prompt is unavailable, and the required variables remain discoverable from the two fields above.

## Versioning

Every `SKILL.md` must include a quoted `version` inside the `metadata` mapping:

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

6. If the skill ships `scripts/`, add their tests in the repository-level suite, not in the skill directory:

   ```text
   tests/skill-name/
   ```

   See [Tests](#tests) for the layout, the path anchor to use, and how to run them.

7. Update related documentation if the new skill changes repository-level lists, examples, or setup guidance.

8. Run validation and security checks before opening a pull request.

## Updating an Existing Skill

1. Read the current `SKILL.md` and any supporting files.
2. Check upstream package, API, or platform documentation for current behavior.
3. Make the smallest useful change that fixes or improves the skill.
4. Increment `metadata.version`.
5. Test changed examples, commands, and scripts.
6. Run the skill's suite if it has one: `uv run --with pytest python -m pytest tests/skill-name -q`. Some suites assert the skill's exact version string, so a version bump can require a matching test edit.
7. Note any behavior changes in the pull request description.

## Validation

Validate Agent Skills format with the reference validator, which is already a dev dependency:

```bash
uv sync
uv run skills-ref validate ./skills/skill-name

# or check every skill at once, the same way CI does
for d in skills/*/; do uv run skills-ref validate "$d"; done
```

CI runs this on every pull request that touches `skills/`, along with the repo-specific checks in `.github/workflows/skill-spec-validation.yml` (a required `metadata.version`, `allowed-tools` as a string, quoted `metadata` scalars, and a warning above 500 lines).

Security-scan new or substantially changed skills:

```bash
uv pip install cisco-ai-skill-scanner
skill-scanner scan ./skills/skill-name --use-behavioral
```

A clean scan reduces review noise but does not replace manual review.

## Tests

**Tests never live under `skills/`.** A skill directory ships only what an agent loads, so tests go in the repository-level suite instead — one directory per skill, named exactly after the skill directory:

```text
tests/
└── skill-name/          # matches skills/skill-name/
    ├── test_scripts.py
    └── fixtures/        # optional test data
```

A test reaches the skill it covers through an explicit anchor rather than a relative walk:

```python
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "skill-name"
```

Anything the CLIs under test resolve relative to the working directory should be repo-root relative, since the suite runs from the repository root — `tests/skill-name/fixtures/manifest.json`, not `fixtures/manifest.json`.

Run one skill's suite, or the whole tree:

```bash
uv run --with pytest python -m pytest tests/skill-name -q

# every skill, in a separate process each
uv run --with pytest python tests/run_all.py
```

Each skill's suite must run in its own process. Skills' `scripts/` directories own plain top-level module names — 32 skills ship a `scripts/_common.py`, and names like `cluster.py` and `validate_manifest.py` recur — so collecting two skills into one interpreter would resolve those imports to whichever skill was imported first and silently test the wrong files. `tests/conftest.py` rejects a multi-skill session, and `tests/run_all.py` forks per skill.

### One environment per skill

Four suites fail on this repository's default environment because their scientific dependencies are not installed (`exa-search`, `qutip`, `scikit-survival`, `simpy`), and installing them all into one environment is not possible: the skills' upstream pins contradict each other. `opentrons` requires `numpy<2`; `esm` caps `transformers` below the release the `transformers` skill targets; `geniml` and `spikeinterface` pin `zarr<3` while the `zarr-python` skill targets 3.x; `bioservices` caps `lxml<6` while `matchms` requires 6.0.2+; and `pytdc`, `molfeat`, `deepchem`, `histolab`, `vaex`, and `ete3` each need an interpreter older than 3.13.

`--isolated` therefore gives each skill its own throwaway `uv` environment, built from [`tests/skill-requirements.toml`](tests/skill-requirements.toml):

```bash
python tests/run_all.py --isolated                    # every suite, one env each
python tests/run_all.py --isolated qutip exa-search   # just these
```

Nothing is installed into the project environment, so `uv sync` is unaffected. Each `[skills.<name>]` entry lists the packages that skill documents and, where needed, a `python` version for that skill alone — uv downloads the interpreter on demand. Packages that cannot be installed at all (a GitHub-only SDK, a conda-forge-only library, a CUDA build) are listed under `[unavailable]` with the reason, and the runner prints them so the gap appears in the test output.

A new skill that ships `scripts/` needs a `[skills.<name>]` entry. Use `packages = []` when its bundled tooling is standard-library only — the skill still gets a clean environment with just pytest. uv caches wheels globally, so repeat runs create each environment in milliseconds.

## Pull Request Checklist

Before submitting a pull request, confirm:

- The skill directory name and `name` frontmatter match exactly.
- The skill directory contains only `SKILL.md`, `references/`, `scripts/`, and `assets/` — no `tests/` directory and no `test_*.py` files. Tests live in `tests/<skill-name>/`.
- `SKILL.md` has valid YAML frontmatter and Markdown body content.
- `uv run skills-ref validate ./skills/<name>` passes.
- Only the six spec-defined top-level fields are present; anything else lives under `metadata`.
- `metadata` is a block mapping, not single-line JSON, and its scalar values are quoted where needed.
- Any `metadata.openclaw` or `metadata.hermes` block is a nested mapping, not a JSON string.
- If the skill needs credentials, they are named in `compatibility` and declared in `metadata.openclaw.envVars`.
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
