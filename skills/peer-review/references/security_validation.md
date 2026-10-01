# Security Validation Record

Historical validation date: **2026-07-23** (local project date). Counts and scanner results below describe that run, not a new security certification.

## Baseline

The repository `SECURITY.md` entry recorded **10 findings** with maximum severity **CRITICAL**:

- Cross-file environment-variable and network exfiltration
- A multi-file collection/transmission chain
- Environment harvesting in both schematic scripts
- API-key transmission to an external model service
- Full environment propagation to a subprocess
- Repeated costly model/image operations
- Mandatory external schematic/cross-skill behavior

The affected files were:

- Deleted: scripts/generate_schematic.py
- Deleted: scripts/generate_schematic_ai.py
- The former `SKILL.md`

## Remediation

- Deleted both external schematic scripts.
- Removed credentials, environment access, `.env` loading, subprocess chaining, network requests, model calls, image generation, mandatory figures, and cross-skill calls.
- Replaced them with bounded deterministic local JSON/CSV/Markdown validators and generators.
- Added strict schemas, duplicate-key/header detection, size/row/cell limits, symlink rejection, private atomic output, and no implicit overwrite.
- Added report minimization: IDs, counts, rule codes, and line numbers instead of manuscript/review prose.
- Added AST tests that reject network libraries, executable serialization, dynamic code execution, and environment credential access.
- Added confidentiality, no-reuse, authorization, conflict, competence, AI-policy, disclosure, and deletion/retention gates.

## Validation results

- Agent Skills reference validator: **PASS**
- Dependency-free CLI help checks: **PASS**
- Synthetic standard-library tests: **26 passed**
- Explicit AST parse with bytecode disabled: **8 scripts parsed**
- Bytecode artifacts: **0**
- IDE lints: **0**
- Documented local-path link test: **PASS**
- Markdown link check: **PASS** (access-controlled HTTP 403 treated as reachable)
- Direct behavioral security scan: **SAFE, 0 findings**
- Pull-request gate with `--fail-on HIGH`: **PASS**
  - CRITICAL: 0
  - HIGH: 0
  - LOW: 3

## Residual LOW findings

The final LLM-assisted pull-request scan reported:

1. **Missing `allowed-tools` declaration** — informational. This field is optional under the Agent Skills specification. The compatibility and body explicitly constrain bundled tools to local standard-library processing with no network, model, image, credential, or environment access.
2. **Broad description** — accepted as a scoped capability description. The mandatory authorization and venue-policy gate applies before confidential content is read, and the body limits all functions to peer-review assessment.
3. **Bounded CSV/JSON processing** — defensive observation with “no action required” in the scanner output. Inputs are already limited to 4 MiB, 5,000 CSV rows, 12,000 characters per cell, and finite list sizes; tests cover oversize rejection.

None of the LOW findings permits data transmission or credential access. No CRITICAL or HIGH issue remains.

## Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with pytest python -m pytest tests/peer-review -q

uv run skills-ref validate skills/peer-review

uv run skill-scanner scan skills/peer-review --use-behavioral

uv run python scan_pr_skills.py \
  --fail-on HIGH \
  --output /tmp/peer-review-pr-scan.md \
  skills/peer-review
```

The repository-level `SECURITY.md` was intentionally not edited in this scoped refresh; its generated snapshot will update through the repository’s normal scan process.

## 2026-10-01 maintenance checks

The intake now distinguishes a disclosed conflict awaiting clearance from actual editor clearance. The reporting catalog adds SPIRIT-AI protocols and non-prediction LLM studies. Standard-library synthetic tests pass (30 tests and 7 CLI-help subtests), and `skills-ref validate` passes. A new collection-level security scan is coordinated separately; the historical scanner counts above were not rerun for this record. These checks use synthetic inputs and do not constitute a live manuscript review.
