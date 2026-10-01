# Aggregate Data Presentation

Present verified outputs without changing their meaning. Do not calculate a clinical conclusion, select an analysis, or repair source discrepancies.

## Mandatory table metadata

Every table should identify:

- artifact and analysis purpose;
- data cut and source-output version;
- analysis population/set;
- treatment/group labels;
- denominator for every group and row when it varies;
- whether a value is a subject count, event count, observation count, or estimate;
- units, time point/window, and summary statistic;
- missing, unknown, not assessed, suppressed, or not applicable values;
- coding dictionary/version/language where applicable;
- statistical method and multiplicity status only when copied from a verified output;
- provenance manifest and reviewer status.

## Counts and denominators

- Show `n/N (%)`, not a percentage alone, unless the governing output specifies another form.
- For a proportion of distinct participants, require `0 <= n <= N` and `N > 0`. This bound does not apply to recurrent event counts; preserve the verified count or exposure-time rate and label its denominator separately.
- Recalculate only for consistency checking; do not silently replace the reported percentage.
- State the rounding rule and tolerance.
- Do not add subgroup percentages when the subgroup denominator is unknown.
- Do not infer that denominators are randomized, treated, evaluable, or safety populations.
- Keep event counts distinct from subjects affected; event counts can exceed the number of subjects.
- Do not sum non-mutually-exclusive categories.

## Dates and time

- Use ISO 8601 in structured manifests.
- Preserve source timezone and precision.
- Distinguish event date, collection date, database cut, report date, and verification date.
- Flag start-after-end and conflicting dates.
- Do not impute a missing day, month, timezone, or chronology.
- For de-identified case reports, use an authorized relative timeline; do not distort intervals.

## Units and precision

- Preserve source units.
- Require a unit for every dimensional quantity.
- Use one verified unit per comparable series or expose the mismatch.
- Do not convert or normalize without an authorized traceable conversion rule.
- Preserve clinically meaningful precision; do not create extra significant digits.
- Identify SD, SE, CI, IQR, range, and denominator explicitly.

## Missing and suppressed values

Keep these states distinct:

- `missing`;
- `not_collected`;
- `not_assessed`;
- `unknown`;
- `not_applicable`;
- `suppressed_for_privacy`;
- `zero`.

Never convert a blank to zero. State small-cell suppression rules and ensure totals or complementary cells do not reveal suppressed values.

## Adverse-event tables

For term-level aggregate tables:

- state MedDRA version and language;
- state analysis set and denominator;
- state counting rule from the verified SAP/output;
- show subjects affected and event count separately;
- do not add p-values or causal labels;
- do not interpret between-group differences;
- preserve threshold rules exactly;
- have safety and statistical reviewers verify deduplication, hierarchy, and population.

## Figures

No figure is mandatory. Create one only when requested, supported by verified aggregate data, allowed by the target guidance, and reviewable without external image generation.

A CONSORT flow diagram is part of CONSORT 2025 reporting, but every count and reason must come from verified trial outputs. A missing count remains missing; do not create a decorative or inferred diagram.

## Deterministic consistency check

`consistency_checker.py` can inspect:

- ISO date and range ordering;
- unit-label consistency;
- `n/N (%)` arithmetic;
- component-total arithmetic.

It reports mismatches and review needs. It does not change the input, choose the correct source, or validate clinical/statistical meaning.
