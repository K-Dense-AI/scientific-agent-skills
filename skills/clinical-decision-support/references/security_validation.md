# Security Validation Record

Validation date: **2026-07-23** (local project date).

## Baseline

The repository `SECURITY.md` section recorded 11 findings:

- 3 CRITICAL findings for cross-file environment-variable/network exfiltration behavior;
- 1 HIGH finding for transmitting a credential to an external service;
- 5 MEDIUM findings for command chaining, credential flow, undeclared network use, and environment harvesting;
- 2 LOW findings for mandatory cross-skill invocation and dependency concerns.

The affected external schematic wrappers were the now-deleted files
`generate_schematic.py` and `generate_schematic_ai.py`.

## Remediation

- Deleted both schematic-generation scripts.
- Removed all external service, LLM, image, credential, and environment-variable behavior.
- Removed mandatory figures and cross-skill calls.
- Replaced unsafe person-level classification and care-pathway helpers with aggregate or planning-only tools.
- Added bounded local JSON handling, person-level-key rejection, output limits, and deterministic schemas.
- Added static AST tests that reject network libraries, dynamic code execution, credential access, and executable serialization.

## Historical July 2026 Scan Results

- Direct behavioral scan: **SAFE, 0 findings**.
- Pull-request gate with `--fail-on HIGH`: **passed** with 0 CRITICAL and
  0 HIGH. Repeated LLM-assisted runs returned 2–3 LOW findings because the
  analyzer is nondeterministic.

## Accepted LOW Findings

Across repeated runs, the nondeterministic analyzer reported different subsets of
these LOW observations:

1. **Optional `allowed-tools` field absent** — accepted as informational. The
   Agent Skills specification does not require it; compatibility and runtime
   instructions explicitly prohibit network and credential access.
2. **Broad description** — accepted. The scope intentionally covers the related research-evaluation artifacts requested for this safety refresh, while the frontmatter and first body section explicitly exclude care and live operation.
3. **Person-level key filtering uses a denylist** — accepted as a documented limitation, not a privacy guarantee. Input is contractually restricted to synthetic or aggregate schemas, common person-level fields are rejected as defense in depth, and the documentation repeatedly requires qualified privacy review. The filter cannot detect every identifier name or sensitive value and is never presented as de-identification.
4. **Occasional missing-file report** — accepted as an analyzer false
   positive. Some runs invented a `templates/` directory and nonexistent
   `assets/*.md` references. The deterministic
   `test_documented_local_paths_exist` check resolves every documented local
   path and passes.

None of the accepted findings permits network access, sensitive-data handling, or clinical action.

## September 2026 Maintenance

The 2.4 refresh keeps all runtime helpers offline. Invalid aggregate/matrix inputs now withhold results or exports; denominator checks run before suppression; undefined balanced accuracy stays null; CSV text is escaped and dangling output symlinks are rejected. Synthetic regression tests cover these cases and the updated GRADE imprecision label. The July scanner results above are historical, not a claim about a new scan of version 2.4.

## Reproduction

```bash
uv run skill-scanner scan skills/clinical-decision-support --use-behavioral

uv run python scan_pr_skills.py \
  --fail-on HIGH \
  --output /tmp/clinical-decision-support-pr-scan.md \
  skills/clinical-decision-support
```
