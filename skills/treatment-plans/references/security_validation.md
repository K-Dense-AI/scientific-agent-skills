# Security Validation Record

Historical validation date: **2026-07-23**. Current local review: **2026-10-01**.

## Current refresh

- Read all six JSON templates, eight helpers, and all references. Kept the documentation-only scope and schema version `2.0`; bumped skill metadata to `2.4`.
- Refreshed official-source content, dates, redirects, and program applicability; see `source_ledger.md`. HTTP success alone was not treated as source validation.
- Fixed malformed enum collections, deeply nested JSON and oversized integer parser failures, whitespace-only required strings, unknown-key/document-type leakage into reports, and broader-than-documented timestamp/date-filter acceptance.
- Schedule generation now rejects cross-record inconsistencies before extracting dates. It preserves local calendar dates, not a converted timezone.
- Replaced overwrite-capable publication with hard-link publication; a competing destination is preserved and temporary files are cleaned. Unsupported filesystems fail. A package is still not a transaction, and local-path checks are not a filesystem sandbox.
- Replaced the misleading readiness output with `documentation_declarations_complete` and explicit `handoff_authorized_by_script: false`.
- Agent Skills validator: **PASS**. Isolated Python 3.13.3 suite: **29 passed**. Standard-library CLI smoke: **20 invocations passed**, including all seven help paths, deliberately incomplete templates, complete synthetic records, existing-output refusal, malformed enum input, and strict filters. **8 scripts parsed**; generated schedule contained exactly **7 supplied-date events**; local POSIX output modes checked.
- No patient data, clinical judgment, signature authentication, licensure, de-identification, live EHR integration, external reporting, Windows ACL behavior, or clinical validity was tested. Six JSON templates require no LaTeX/PDF compilation.
- The aggregate repository security scan is coordinated separately. The scanner results below describe the historical July redesign, not a fresh scan of version 2.4.

## Historical redesign evidence

## Baseline

The repository `SECURITY.md` entry recorded **11 findings** with maximum severity **CRITICAL**:

- three CRITICAL cross-file/environment/network exfiltration findings;
- one HIGH API-key transmission finding;
- five MEDIUM findings involving environment harvesting, command chaining, and mandatory external-tool behavior;
- two LOW findings involving unsafe template content and unpinned dependencies.

The affected files included the former `generate_schematic.py`, `generate_schematic_ai.py`, `SKILL.md`, and `medical_treatment_plan.sty`.

## Remediation

- Deleted both schematic-generation scripts.
- Removed network requests, API keys, environment access, `.env` loading, subprocesses, external models, image generation, and cross-skill calls.
- Deleted the hardcoded LaTeX style and all specialty templates containing clinical treatment content.
- Replaced them with generic, fail-closed JSON records.
- Rebuilt every remaining script as a dependency-free, bounded, deterministic local JSON helper.
- Added strict duplicate-key, schema, unknown-field, collection, depth, path, symlink, and output controls.
- Added minimized reports that do not echo clinician-authored content.
- Added AST tests prohibiting network libraries, dynamic execution, executable serialization, subprocesses, and environment access.

## Historical validation results

- Agent Skills reference validator: **PASS**
- Dependency-free CLI help checks: **PASS**
- Synthetic standard-library tests: **21 passed**
- Explicit AST parse with bytecode disabled: **8 scripts parsed**
- Bytecode artifacts after cleanup: **0**
- IDE lints: **0**
- Documented local-path check: **PASS**
- External source links: **PASS** (HTTP 403 from HHS/AHRQ is access control; REMS@FDA returned HTTP 200 with a browser user agent)
- Direct behavioral security scan: **SAFE, 0 findings**
- Pull-request gate with `--fail-on HIGH`: **PASS**
  - CRITICAL: 0
  - HIGH: 0
  - LOW: 2

The first direct scan reported a CRITICAL test-only false positive because the synthetic AST test contained literal names for dynamic-execution functions and used a subprocess to exercise `--help`. The help test was changed to call each parser directly and the prohibited names were constructed without executable references. The final direct scan is clean.

## Historical residual LOW findings

The LLM-assisted pull-request scan reported:

1. **Missing `allowed-tools` declaration** — informational. The field is optional. The compatibility statement and body explicitly limit bundled tools to local standard-library JSON processing, and the direct behavioral scan confirms no network, credential, process, model, or image behavior.
2. **Invented missing-file variants** — scanner false positive. It claimed files under `templates/` and swapped `assets/` and `references/` paths that do not appear in the skill. The deterministic documented-local-path test resolves every actual local path and passes.

Neither LOW finding permits data transmission or clinical decision-making. The recorded July scan reported no actual CRITICAL or HIGH finding after review. The repository-level `SECURITY.md` is intentionally not edited in this scoped refresh; its generated snapshot will update through the repository's normal process.

## Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s tests/treatment-plans -p 'test_*.py' -v

uv run skills-ref validate skills/treatment-plans

uv run skill-scanner scan skills/treatment-plans --use-behavioral

uv run python scan_pr_skills.py \
  --fail-on HIGH \
  --output /tmp/treatment-plans-pr-scan.md \
  skills/treatment-plans
```
