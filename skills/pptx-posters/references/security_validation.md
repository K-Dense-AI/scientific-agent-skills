# Security validation record

Historical security validation date: **2026-07-24**.

## 2026-10-01 maintenance validation

- Exact generation pins are now python-pptx 1.0.2, Pillow 12.3.0, and lxml 6.1.3.
- The isolated per-skill suite passed **52 tests**, including generation/reopen,
  deterministic bytes, UTC conversion across day boundaries, metadata limits,
  in-directory final-symlink rejection, and distinct canvas/artboard PDF dimensions.
- The spec validator passed. New aggregate security scan results are tracked by the
  repository refresh; the historical scan findings below are not a new scan.
- No native PowerPoint, PDF export, accessibility, or physical printer validation was
  performed in this maintenance pass.

## Baseline

The repository `SECURITY.md` snapshot records **10 findings** for the former v1.2
skill, with maximum severity **CRITICAL**:

- three CRITICAL cross-file/environment/network transmission findings;
- four MEDIUM credential, prompt, and environment-harvesting findings;
- three LOW dependency, environment-file, and broken-reference findings.

The affected implementation used two external schematic-generation scripts plus
network, credential, environment-file, subprocess, and model behavior.

## Remediation

- Deleted both external schematic scripts and the unused HTML template.
- Removed network/model calls, credentials, environment access, subprocesses, external
  templates, mandatory figures, and cross-skill behavior.
- Replaced the workflow with strict local JSON, exact source IDs, author approval
  binding, optional hashed PNG/JPEG assets, and deterministic one-slide generation.
- Added bounded ZIP central-directory, part-path, content-type, relationship, XML,
  image-signature, macro, OLE, ActiveX, embedded-file, and external-link checks.
- Added safe no-overwrite publication, lazy optional imports, exact dependency pins,
  and AST policy tests that prohibit network, process, environment, executable
  deserialization, and dynamic-code behavior.

## Validation results

- Agent Skills reference validator: **PASS**
- Dependency-free CLI help checks: **PASS**
- Synthetic tests with standard library only: **47 passed, 2 exact-pin tests skipped**
- Exact-pinned round trip (`python-pptx==1.0.2`, `Pillow==12.3.0`,
  `lxml==6.1.1`): **49 passed**
- Generated PPTX reopen, deterministic hash, package reinspection, alt text, title,
  language, layout, image inventory, and no-overwrite checks: **PASS**
- Explicit AST parse with bytecode disabled: **14 Python files parsed**
- Bytecode artifacts: **0**
- IDE lints: **0**
- Diff whitespace check: **PASS**
- Documented local-path check: **PASS**
- External Markdown links checked: **39, no failures**
- Direct behavioral security scan: **SAFE, 0 findings**
- Pull-request gate with `--fail-on HIGH`: **PASS**
  - CRITICAL: 0
  - HIGH: 0
  - LOW: 2

## Residual LOW findings

The LLM-assisted pull-request scan reported:

1. **Bounded resource use.** Full image decoding is capped at 100 million pixels;
   archives are capped at 512 MiB compressed, 1 GiB expanded, 4,096 members, 128 MiB
   per member, and 100:1 expansion. Repeated maximum-size local inputs can still use
   material CPU/memory. These documented limits are accepted; callers should apply
   an execution timeout appropriate to their environment.
2. **Invented broken-path variants.** The scan claimed `templates/` paths and swapped
   `assets/`/`references/` variants that do not occur in the skill. The deterministic
   local-path test resolves every actual documented path and passes.

Neither finding permits network access, credential access, code execution, macro
activation, or overwrite. No CRITICAL or HIGH issue remains. The repository-level
`SECURITY.md` is intentionally unchanged; its generated snapshot can update through
the repository's normal scan process.

## Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s tests/pptx-posters -p "test_*.py" -v

PYTHONDONTWRITEBYTECODE=1 uv run --no-project \
  --with "python-pptx==1.0.2" \
  --with "Pillow==12.3.0" \
  --with "lxml==6.1.3" \
  python -B -m unittest discover \
  -s tests/pptx-posters -p "test_*.py" -v

uv run skills-ref validate skills/pptx-posters

uv run skill-scanner scan skills/pptx-posters --use-behavioral

uv run python scan_pr_skills.py \
  --fail-on HIGH \
  --output /tmp/pptx-posters-pr-scan.md \
  skills/pptx-posters
```
