# Security Validation Record

Historical validation date: **2026-07-23**

The results below describe the earlier remediation, not a fresh scan. The
2026-10-01 refresh adds synthetic regression coverage for evaluation-round
agreement, bounded pair aggregation, scale consistency, unrounded sensitivity,
and companion membership. Collection-wide security scanning is recorded by
the refresh coordinator; do not infer a current scan from this historical record.

## Baseline

The repository `SECURITY.md` entry recorded **10 findings** with maximum
severity **CRITICAL**:

- four CRITICAL cross-file, environment, and network-exfiltration findings;
- three MEDIUM credential, prompt, and environment-harvesting findings; and
- three LOW cross-skill, command, and resource-use findings.

The affected files were the two former schematic-generation scripts and the
old `SKILL.md`.

## Remediation

- Deleted both schematic-generation scripts.
- Removed all network requests, API-key handling, environment access,
  environment-file loading, third-party model behavior, image handling,
  child-process execution, cross-skill invocation, and mandatory figure
  instructions.
- Replaced the former recommendation-producing score calculator with bounded,
  transparent descriptive rubric math.
- Added a strict prohibition on automated or assisted hiring, promotion,
  tenure, admissions, funding, awards, discipline, person ranking, and other
  high-impact personnel decisions.
- Added qualitative-first metric and prestige safeguards.
- Added construct, provenance, content-evidence, rater, agreement, uncertainty,
  missingness, not-applicable, traceability, sensitivity, subgroup, conflict,
  appeal, accessibility, privacy, and accountable-human controls.
- Added dependency-free, bounded local JSON/CSV tools with duplicate-key,
  unknown-field, size, depth, non-finite-number, symbolic-link, and private
  application-field rejection.
- Added minimized reports that never copy source-document content or emit rater
  identifiers.
- Added static AST tests that prohibit network libraries, dynamic-code calls,
  executable serialization, process launching, environment access, and the
  deleted schematic files.

## Validation results

- Agent Skills reference validator: **PASS**
- Dependency-free CLI help checks: **8 passed**
- Synthetic standard-library tests: **29 passed**
- Explicit AST parse with bytecode disabled: **8 scripts parsed**
- Bytecode artifacts: **0**
- IDE lints: **0**
- Documented local-path check: **PASS**
- External source links: **24 passed**
- Direct behavioral security scan: **SAFE, 0 findings**
- Pull-request gate with `--fail-on HIGH`: **PASS**
  - CRITICAL: 0
  - HIGH: 0
  - LOW: 2 (latest final run; LOW-only LLM wording varied between runs)

## Residual LOW findings

The latest LLM-assisted pull-request scan reported:

1. **Bash is broad but constrained.** Informational: the manifest declares Bash
   because the documented fixed `python3` commands are shell invocations. The
   body limits Bash to those local commands, and the direct behavioral scan
   confirms no process-launching code in the scripts.
2. **Invented missing-file aliases.** False positive: the scanner claimed
   inconsistent alternate directories for bundled assets and references. A
   direct text search found no alternate template-directory path; every
   documented local path is under the actual `assets`, `references`, or
   `scripts` directory; and the deterministic path-resolution test resolves
   every backticked local path.

The direct behavioral scan is clean. The residual findings neither permit data
transmission nor create a missing-file fallback. The generated root
`SECURITY.md` snapshot was intentionally not edited in this scoped refresh.

## Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s tests/scholar-evaluation -p 'test_*.py' -v

for script in skills/scholar-evaluation/scripts/*.py; do
  PYTHONDONTWRITEBYTECODE=1 python3 "$script" --help >/dev/null || exit 1
done

uv run skills-ref validate skills/scholar-evaluation

uv run skill-scanner scan skills/scholar-evaluation --use-behavioral

uv run python scan_pr_skills.py \
  --fail-on HIGH \
  --output /tmp/scholar-evaluation-pr-scan.md \
  skills/scholar-evaluation
```
