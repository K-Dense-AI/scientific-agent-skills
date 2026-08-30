# Repository Guidance

This repository is a collection of Agent Skills for science and research. Every skill lives in its
own directory under `skills/` and must conform to the open
[Agent Skills specification](https://agentskills.io/specification).

Read this file before creating or changing a skill. `CONTRIBUTING.md` covers the same ground at
more length, plus the pull-request process.

## What belongs here

**In scope:** a narrow skill for one scientific package, database, platform, or research workflow —
`scanpy`, `depmap`, `benchling-integration`, `experimental-design`.

**Out of scope**, and routinely declined:

- General software-engineering or coding-judgment skills — they compete for selection on every task.
- General infrastructure with a scientific example bolted on (a vector database, a cloud SDK) —
  accepting one implies carrying every competitor.
- Broad "orchestrator" skills that route to other skills — they overlap every specialist by design.
- A second provider for a service an existing skill already reaches.

The general-purpose skills that do exist are narrow output-format helpers (`docx`, `pdf`, `pptx`,
`generate-image`, `markdown-mermaid-writing`). They are not precedent for broadening scope.

## Layout

The repository root is an [Agent Plugins](https://agent-plugins.org/) 1.0.0 package: `plugin.json`
plus the portable `skills/` tree. Keep `plugin.json` valid against the Agent Plugins manifest
schema, and keep its `version` identical to `pyproject.toml` `[project].version`. Do not add
non-portable top-level fields to `plugin.json` (no inline MCP, hooks, or client-only keys — use
`mcp.json` or a reverse-domain `extensions` namespace if those are ever needed).

```text
plugin.json                 # Agent Plugins manifest (repo root)
skills/<skill-name>/
├── SKILL.md        # required
├── references/     # optional: long documentation, loaded only when needed
├── scripts/        # optional: executable helpers
└── assets/         # optional: templates and static resources
```

Only `SKILL.md` is required inside each skill. Reference other files with relative paths from the
skill root, kept one level deep.

**Tests never live under `skills/`.** A skill directory ships only what an agent loads. Checks for a
skill's scripts and structure go in the repository-level suite instead:

```text
tests/<skill-name>/          # same name as the skill directory
├── test_scripts.py
└── fixtures/                # optional test data
```

**Diagrams never live under `skills/` either.** A skill may have a generated workflow diagram at
`docs/images/<skill-name>.png`, produced by `scripts/generate_skill_image.py`. Diagrams are optional
— see [Skill diagrams](#skill-diagrams).

Tests reach their skill through an explicit anchor, never a relative walk:

```python
SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "<skill-name>"
```

## Creating a skill

1. Create `skills/<name>/` — **the directory name is the skill name** and must equal frontmatter
   `name`.
2. Write `SKILL.md` from the template below. Start at `metadata.version: "1.0"`.
3. Add `references/`, `scripts/`, or `assets/` only when they earn their place.
4. Run the commands and code you document. Scope claims to the release you actually tested
   ("targets stable GeoPandas 1.1.4"), and mark anything untested as illustrative.
5. If the skill ships `scripts/`, put their tests in **`tests/<name>/`** — never in the skill
   directory. Fixtures go in `tests/<name>/fixtures/`.
6. Validate and scan (below).

```markdown
---
name: skill-name
description: What the skill does and when an agent should use it, including the terms that should trigger it.
license: MIT
compatibility: Requires Python 3.12+ with <package> installed. Needs network access.
metadata:
  version: "1.0"
  skill-author: Your Name
---

# Skill Title

## When to use

Use this skill when...

## Workflow

1. ...

## Examples

...
```

## Updating a skill

1. Read the current `SKILL.md` and its supporting files first.
2. Check upstream docs — APIs move, and the skill may be pinned to an older release.
3. Make the smallest useful change.
4. **Bump `metadata.version` in the same change**: minor for normal improvements (`"1.2"` →
   `"1.3"`), major only for a breaking change or substantial redesign (`"1.9"` → `"2.0"`).
5. Re-run any example, command, or script you touched, plus `tests/<name>/` if that suite exists.
   Suites check that `metadata.version` is present and quoted, not what it equals, so a version bump
   never needs a matching test edit.
## Frontmatter

`SKILL.md` starts with YAML frontmatter. **Only these six fields are allowed** — the spec defines a
closed set, and any other top-level key is a validation error:

| Field | Required | Constraints |
| --- | --- | --- |
| `name` | Yes | 1–64 chars, lowercase letters/digits/hyphens only, no leading, trailing, or consecutive hyphens, and **must equal the directory name**. |
| `description` | Yes | 1–1024 chars. Say what the skill does *and* when to use it, with the keywords that should trigger it. Write it in third person. |
| `license` | No | License name, or a reference to a bundled license file. |
| `compatibility` | No | Max 500 chars. Environment requirements only — omit it if the skill has none. |
| `allowed-tools` | No | A **space-separated string**, e.g. `Read Write Edit Bash`. Not a YAML list, not comma-separated. |
| `metadata` | No | Mapping of string keys to **string** values, except the host manifest blocks below. Required here: `metadata.version`. |

Put anything else — authorship, upstream versions, review dates, client-specific config — inside
`metadata`, never at the top level. In particular, Hermes' top-level
`required_environment_variables` cannot be used here: it fails the validator and, because
`strictyaml` rejects the whole document, takes `name` and `description` down with it. Declare
credentials in `compatibility` and `metadata.openclaw.envVars` instead.

### Write block-style YAML, not JSON flow style

The reference validator parses frontmatter with `strictyaml`, which **rejects JSON-style flow
mappings and sequences**. A flow mapping does not merely fail one check: the whole frontmatter
fails to parse, so `name` and `description` become unreadable and the skill will not register.

```yaml
# Wrong -- breaks the validator
metadata: {"version": "1.1", "skill-author": "K-Dense Inc."}

# Right
metadata:
  version: "1.1"
  skill-author: K-Dense Inc.
```

### Quote `metadata` scalars

Quote values that would otherwise be parsed as a number, boolean, or date — `version: "1.0"`,
`last-reviewed: "2026-07-23"` — so they stay strings as the spec requires.

### Host manifest blocks stay nested mappings

`metadata.openclaw` and `metadata.hermes` are the documented exception: keep them as **nested
mappings**, not JSON strings. OpenClaw's `resolveOpenClawManifestBlock()` requires
`typeof candidate === "object"`, so a JSON string silently disables its dependency gating and
credential injection. Nested mappings still pass `skills-ref validate`.

```yaml
metadata:
  version: "1.1"
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

Only skills with external requirements need these blocks; most omit them. A failed `requires` /
`requires_toolsets` gate *hides* the skill from the agent, so gate only on something the skill
genuinely cannot run without.

## Body and layout

- Keep `SKILL.md` under 500 lines. CI warns above that. Move long reference material into
  `references/` so agents load it only when needed.
- A skill directory ships only what an agent loads. Tests, fixtures, scratch data, and generated
  artifacts stay out of it; tests go in `tests/<name>/`.
- Give concrete workflows, commands, and worked examples rather than background explanation.
- Name the required packages, system dependencies, credentials, and network access.
- Include the scientific caveats and validation checks that matter.
- Put fragile or repetitive logic in `scripts/` instead of asking the agent to recreate it.
- Never include secrets, API keys, private URLs, or unpublished data.

## Validate and scan

```bash
uv sync

# spec conformance for one skill
uv run skills-ref validate skills/<name>

# every skill, the way CI does
for d in skills/*/; do uv run skills-ref validate "$d"; done
```

`.github/workflows/skill-spec-validation.yml` runs that on every PR touching `skills/`, plus the
repo rules `skills-ref` does not check: `metadata.version` present, `allowed-tools` a
space-separated string, `metadata` scalars quoted, and a warning past 500 lines.

Security-scan new or substantially changed skills. Scanning uses
[Cisco AI Defense Skill Scanner](https://github.com/cisco-ai-defense/skill-scanner) — the
`cisco-ai-skill-scanner` package pinned in `pyproject.toml`, which detects prompt injection, data
exfiltration, and malicious code patterns in Agent Skills. Its README documents the rule IDs and
CLI flags; consult it when a finding's rule is unfamiliar.

`.github/workflows/pr-skill-scan.yml` runs the repo wrapper for changed skills on every PR and
posts a sticky comment, failing on HIGH or above:

```bash
# needs SKILL_SCANNER_LLM_API_KEY (see .env)
uv run python scan_pr_skills.py skills/<name>

# or the upstream CLI directly, without the repo wrapper
uv run skill-scanner scan skills/<name> --use-behavioral
```

**Verify a finding against the code before "fixing" it.** Known systematic false positives:
`BEHAVIOR_*_EXFILTRATION` and `BEHAVIOR_ENV_VAR_HARVESTING` on any skill that reads its own API key
and calls its own service; `MDBLOCK_PYTHON_SUBPROCESS` on any `subprocess` snippet, including the
safe argument-list form; and `*_EVAL_EXEC` on substrings inside ordinary identifiers (`retrieval`,
`executor`) or on `model.eval()`. Findings sometimes cite files a skill does not contain — check
against `find skills/<name> -type f` before acting.

If the skill has tests in `tests/<name>/`, run them:

```bash
uv run --with pytest python -m pytest tests/<name> -q

# every skill's suite, one process each, after the repo-wide guard
uv run --with pytest python tests/run_all.py
```

**One skill per pytest process.** Skills' `scripts/` directories own plain top-level module names —
32 of them ship a `scripts/_common.py` — so collecting two skills into one interpreter resolves
`_common` to whichever skill imported first and silently tests the wrong files. `tests/conftest.py`
refuses such a session; `tests/run_all.py` forks per skill.

### The repo-wide guard

```bash
uv run --with pytest python -m pytest tests/_meta -q
```

`tests/_meta` is the fastest useful signal in the repo: pure standard library, no scientific
packages, a couple of seconds. It runs the shared structural contract against **every** skill and
fails if a skill ships `scripts/` without a suite under `tests/<name>/` or an entry in
`tests/skill-requirements.toml`. `.github/workflows/skill-tests.yml` runs it on every pull request,
so a skill with untested scripts cannot land. A full run of `tests/run_all.py` starts with it.

It is not one of the per-skill processes because it deliberately spans all of them at once — safe
because it never imports skill code, only parses it.

### The shared contract

`tests/_contract/` holds the assertions every skill shares, so a per-skill suite contains only what
is actually specific to that skill. `tests/conftest.py` registers it as the importable module
`skill_contract`:

```python
import skill_contract

# every argparse script answers --help; skips when its packages are absent,
# runs for real under --isolated
CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)

# for library-style scripts with an `if __name__ == "__main__"` worked example
DemoBlockTests = skill_contract.cli.demo_test_case(SKILL_ROOT, ("doe_designs.py",))
```

- `structure` — frontmatter conformance, the 500-line limit, no tests or bytecode under `skills/`,
  local links resolve, scripts parse, no `eval`/`exec`/`os.system`, no standard-library shadowing,
  no hardcoded local paths, shell scripts valid. Run repo-wide by `tests/_meta`; do not duplicate
  these in a per-skill suite.
- `cli` — the `--help` and demo-block cases above.
- `office` / `schematic` — behaviour for files several skills ship byte-identical copies of (the
  OOXML tree under docx/pptx/xlsx; the AI schematic generator under five skills). `tests/_meta`
  separately fails if those copies drift apart, so fix them together.

### One environment per skill

The project environment deliberately does not carry the skills' scientific packages. Their upstream
pins are mutually exclusive — `opentrons` needs `numpy<2`, `esm` caps `transformers` below the
version the `transformers` skill targets, `geniml` and `spikeinterface` pin `zarr<3` against the
`zarr-python` skill's 3.x, `bioservices` caps `lxml<6` against `matchms`, and `pytdc`, `molfeat`,
`deepchem`, `histolab`, `vaex`, and `ete3` each need an interpreter older than 3.13. Installing them
together forces every one of those skills to the losing side of a version fight.

So `--isolated` builds a throwaway `uv` environment per skill instead, from
[`tests/skill-requirements.toml`](tests/skill-requirements.toml):

```bash
python tests/run_all.py --isolated                 # every suite, one env each
python tests/run_all.py --isolated scanpy qiskit   # just these
```

Each entry lists the packages that skill documents, plus an optional `python` when the skill cannot
run on the default interpreter; uv downloads that interpreter on demand. Packages that cannot be
installed at all — a GitHub-only SDK, a conda-forge-only library, a CUDA build — are recorded under
`[unavailable]` with the reason, and the runner prints them so the gap shows up in test output.

Adding a skill with `scripts/` means adding its `[skills.<name>]` entry — `tests/_meta` fails
without one. Use `packages = []` for skills whose bundled tooling is standard-library only; they
still get a clean environment, and CI runs exactly that set on every pull request. uv caches wheels
globally, so repeat runs create each environment in milliseconds.

The full `--isolated` sweep is not run in CI: it builds one environment per skill, several of which
need a CUDA toolchain, a JDK, or a local MATLAB install. Run it before a release, or whenever you
touch the shared contract.

## Skill diagrams

A skill may carry a generated workflow diagram at `docs/images/<skill-name>.png`. Diagrams are
optional: neither a new skill nor a change to an existing one is blocked on having or refreshing an
image, and no CI check enforces them. If you do ship one, note that it is derived from the
documentation, so regenerate it when the skill's workflow changes rather than leaving a picture that
misrepresents the skill.

`scripts/generate_skill_image.py` is local repository tooling, standard library only, and runs in
two stages on one `OPENROUTER_API_KEY` (environment variable, repository `.env`, or `--api-key`):
a text model reads `SKILL.md` plus everything under `references/` and a manifest of `scripts/` and
`assets/`, distils it into a description of one diagram, then an image model draws it. Because it
reads the whole skill, run it **after** the documentation is final, not before.

```bash
# one skill -> docs/images/<name>.png, replacing any existing image
uv run python scripts/generate_skill_image.py --skill <name>

# see which files feed the reader, and where the image lands — no API calls, nothing billed
uv run python scripts/generate_skill_image.py --skill <name> --dry-run

# read the skill and print the diagram prompt without drawing it
uv run python scripts/generate_skill_image.py --skill <name> --prompt-only

# several skills in one batch
uv run python scripts/generate_skill_image.py --skill <name-a> <name-b>

# backfill everything missing an image, six at a time
uv run python scripts/generate_skill_image.py --all --skip-existing -j 6
```

Look at the result before committing it. Image models misspell labels and occasionally point an
arrow at the wrong card; regenerate rather than ship a diagram whose text is wrong. `--quality low`
makes iteration cheap while checking composition, but commit a `high` render. Both the art direction
and the reader's instructions live at the top of the script — change them there rather than
hand-tuning one skill's prompt, so the set stays visually consistent.

## Before opening a PR

- Directory name and frontmatter `name` match exactly.
- No `tests/` directory and no `test_*.py` anywhere under `skills/<name>/` — tests belong in
  `tests/<name>/`.
- Only the six spec-defined top-level fields; everything else under `metadata`.
- `metadata.version` exists, is quoted, and is bumped if you changed an existing skill.
- `metadata` is a block mapping; `openclaw` / `hermes` blocks are nested mappings.
- `uv run skills-ref validate skills/<name>` passes.
- If the collection version changes, `plugin.json` `version` matches `pyproject.toml`.
- `uv run --with pytest python -m pytest tests/_meta -q` passes — this is what CI blocks on, and it
  catches a missing suite, a missing `skill-requirements.toml` entry, a broken local link, a
  leaked local path, and a drifted Agent Plugins manifest.
- If the skill ships `scripts/`: a suite exists at `tests/<name>/`, a `[skills.<name>]` entry exists
  in `tests/skill-requirements.toml`, and `python tests/run_all.py --isolated <name>` passes.
- If the skill ships `docs/images/<name>.png`, its labels are spelled correctly and its arrows point
  where they should. The image itself is optional.
- Examples and scripts are tested, or clearly marked illustrative.
- No secrets or private data; scan results clean or explained in the PR.
