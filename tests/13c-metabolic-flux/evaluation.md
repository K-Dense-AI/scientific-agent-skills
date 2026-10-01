# Validation record

Checked on 2026-09-29 using the environment pinned in `tests/skill-requirements.toml`.

- Skill specification validation passed.
- Isolated numerical/CLI suite: 45 tests and one shared-contract subtest passed.
- Repository guard: 11 tests and 4,206 structural subtests passed.
- Documented installation, simulation, branch fits and TCA fits/profiles ran successfully.
- An independent reviewer reproduced and verified fixes for three numerical edge cases:
  unrelated loose bounds, very small flux units, and inconsistent rare-bin covariance.
- Security scan: no medium, high or critical findings. Two low informational findings
  were reviewed: omission of the optional `allowed-tools` field, and installation of
  upstream mfapy from its pinned Git commit. The installation source and build-code
  execution are disclosed; the environment is isolated. The scanner's suggested YAML
  list for `allowed-tools` is not compatible with this repository's string-only rule.

## Initial paired agent evaluation

The prompt and five assertions are in `evals.json`. One independent agent with the
skill and one without it received the same synthetic TCA inputs, input schema, and
preinstalled scientific dependencies, with a six-minute task budget.

| Configuration | Assertions passed | Result |
| --- | --- | --- |
| With skill | 5/5 | Used the CLI, recovered v3 near 50, profiled both targets, and verified v7's apparent upper limit comes from the v6 bound. |
| Without skill | 5/5 | Derived an independent positional-isotopomer solver, recovered the same limits, and checked the complete 176-state isotope balances. |

Both obtained an approximate v3 profile interval of 48.6201–51.4002 and recognized
that the isotope measurements do not determine v7. This single comparison provides
no evidence of a model-performance advantage or that the skill is necessary. Agent
time/token telemetry was unavailable; no efficiency claim is made. The paired runs
preceded the numerical edge-case fixes, which were subsequently covered by regression
tests, independent review, and rerunning every documented example.

The numerical tests verify implementation behavior on the listed cases. They do not
validate a biological model or establish reliability on organism-scale networks.
