# Security Validation Record

Historical security-scan date: **2026-07-23** (local project date). These scan results describe that run, not a fresh scan of later edits.

## Maintenance validation 2026-10-01

The isolated Python 3.13 suite passes **31 tests**, including strict calendar dates, rejection of nonstandard JSON numeric constants, a 64-level JSON nesting bound, and correct scaffold date provenance. Skill specification validation also passes. The original runtime scope remains local-only. Repository-wide security scanning is handled separately by the collection maintainer; the historical scanner findings below are not evidence of a new scan.

## Baseline

The repository `SECURITY.md` section recorded **10 findings** with maximum severity **CRITICAL**:

- cross-file environment-variable/network exfiltration;
- a multi-file collection/transmission chain;
- environment harvesting in both schematic scripts;
- credential transmission and local `.env` loading;
- subprocess delegation and full-environment propagation;
- fabricated or unverified model identifiers;
- unpinned external dependencies.

The affected files were:

- deleted: scripts/generate_schematic.py;
- deleted: scripts/generate_schematic_ai.py;
- the former credential and mandatory-figure instructions in `SKILL.md`.

## Remediation

- Deleted both external schematic scripts and all former LaTeX/figure assets.
- Removed credential declarations, environment access, `.env` loading, subprocesses, HTTP requests, external models, image generation, mandatory figures, and cross-skill behavior.
- Replaced the workflow with bounded deterministic local JSON/CSV/Markdown validators and a preregistration scaffold generator.
- Added strict duplicate-key/header detection, size/row/cell/list limits, symlink and URL-path rejection, private atomic outputs, and no implicit overwrite.
- Added AST tests rejecting network libraries, subprocesses, executable serialization, dynamic code execution, and environment credential access.
- Added local-first confidentiality, source verification, human accountability, ethics, biosafety, dual-use, data, clinical-scope, and regulatory gates.
- Tools report declarations and cross-links only; they do not score or select hypotheses.

## Validation results

- Agent Skills reference validator: **PASS**
- Dependency-free CLI help checks: **PASS** for all 7 public CLIs
- Synthetic standard-library tests: **27 passed**
- Explicit AST parse with bytecode disabled: **8 scripts parsed**
- Bytecode artifacts: **0**
- IDE lints: **0**
- Documented local-path link test: **PASS**
- Authoritative-source link extraction: **36/36 reachable, 0 errors**
- Direct behavioral security scan: **SAFE, 0 findings**
- Pull-request gate with `--fail-on HIGH`: **PASS**
  - CRITICAL: 0
  - HIGH: 0
  - LOW: 2

## Residual LOW findings

The LLM-assisted pull-request scan reported:

1. **Missing `allowed-tools` declaration** — informational. The Agent Skills specification does not require this optional field. The compatibility declaration and body constrain bundled tools to bounded local standard-library processing with no network, models, images, credentials, or environment access.
2. **Missing referenced files** — analyzer false positive. It invented paths under `templates/` and mismatched existing `assets/` and `references/` files. The deterministic local-path test resolved every documented bundled path and passed. No script implements network fallback or substitute retrieval.

Neither LOW finding permits data transmission, credential access, scientific scoring, or automatic hypothesis selection. No CRITICAL or HIGH issue remains.

## Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 python tests/run_all.py --isolated hypothesis-generation

uv run skills-ref validate skills/hypothesis-generation

uv run skill-scanner scan skills/hypothesis-generation --use-behavioral

uv run python scan_pr_skills.py \
  --fail-on HIGH \
  --output /tmp/hypothesis-generation-pr-scan.md \
  skills/hypothesis-generation
```

The repository-level `SECURITY.md` is intentionally not edited in this scoped refresh; its generated snapshot updates through the repository’s normal scan process.
