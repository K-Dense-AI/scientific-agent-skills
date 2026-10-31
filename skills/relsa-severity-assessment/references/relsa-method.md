# RELSA equations and current upstream contract

Reviewed 2026-10-01 against the [official RELSA repository](https://github.com/mytalbot/RELSA),
version 0.0.1.9000, commit `e68e8451e8719ccc3600179f55900cd7254ede9d`, and the
[primary methods paper](https://doi.org/10.3389/fvets.2022.937711).
This skill implements the equations independently in Python. Source inspection and agreement
with the published worked example do not establish exhaustive native R parity.

## Preparation

For each animal and ratio-compatible variable, use a prespecified healthy baseline:

```
x_norm(t) = 100 * x(t) / mean(x at the selected baseline times)
```

The baseline must be finite and positive for the intended ratio interpretation. Missing or
nonpositive baselines produce missing trajectories with a warning. A multi-time window uses
available finite values; inspect completeness before accepting that mean. Select it before
looking at outcome trajectories and before the forecast cutoff. With no explicit baseline,
the Python helper uses the earliest time per animal. Never silently use a first post-treatment
observation as a healthy baseline. Units must match between cohorts. Ratios of Celsius
temperatures are origin-dependent; preserve and disclose the published unit convention if
replicating it, and do not claim physical percentage temperature loss is unit-invariant.

RELSA expects 100 at baseline. A percentage of baseline of 90 is already suitable; a signed
change of -10 requires `100 + change`, and a positive loss of 10 requires `100 - loss`.
They are not interchangeable input columns.

For an ordinal score use `score_to_percent(values, max_score, baseline_score=0)`:

```
100 + 100 * (score - baseline_score) / (max_score - baseline_score)
```

The mapped variable is always turned (higher mapped values mean worsening). `max_score`
can be below baseline for a lower-is-worse instrument. Out-of-range values are rejected;
missing scores stay missing. This local convention assumes numerical distances between
categories. A common affine multiplier cancels between numerator and reference denominator
before rounding; it does not independently tune the variable's final weight. Category
encoding, healthy anchor, rounding and the chosen reference remain consequential.

## Direction and reference

Declare worsening direction from the experimental model and validated measurement meaning.
Default variables fall; `turned` variables rise. Neither fever nor hypothermia is a universal
temperature direction. A unidirectional score ignores deviation the other way; if both
extremes matter, this implementation does not supply a validated bidirectional transformation.

For a frozen reference cohort on the normalized scale:

```
maxsev_i   = min(reference_i)           # max for turned variables
maxdelta_i = abs(100 - maxsev_i)
delta_i(t) = max(100 - x_norm_i(t), 0)  # max(x_norm_i(t) - 100, 0) if turned
RW_i(t)    = delta_i(t) / maxdelta_i
RELSA(t)   = sqrt(sum(RW_i(t)^2) / n_present)
```

The default rounds deltas, weights and the final score to two decimals, following current
upstream source. `round_digits=None` disables rounding. Fix that choice across cohorts.
Reference variables must be unique and have finite, nonzero denominators. Unknown turned or
dropped variable names fail. A direction mismatch with no baseline row can still produce
an opposite-direction reference extreme; the helper warns. Such a reference requires review.
A reference whose variable never worsens should not be used to calibrate that variable.

Reference extrema may occur in different animals and at different times. Consequently the
largest **observed reference composite** can be below 1. In full precision, reaching 1 while
all component weights are at most 1 requires every present weight to equal 1. A new composite
above 1 implies at least one reference-scaled deviation exceeds 1; a single exceeded component
can still be diluted to a composite below 1. A value of 0.73 is an RMS ratio, not 73% of an
animal's burden or of a legal severity category. Zero also includes observations on the
non-worsening side of baseline; it does not prove normal welfare.

## Missingness and time

Only observed variables enter the RMS. An entirely missing row stays missing. Changing the
panel changes the estimand even if physiology does not change; inspect `n_vars` and the actual
variable identities, and use a stable panel for comparisons. Informative loss to observation,
euthanasia and survival-related censoring affect both trajectories and density estimates.
Do not fill post-endpoint rows with zero, interpolate across an endpoint, or treat unobserved
recovery as established. Preserve reasons for missingness outside the numeric score table.

Use one row per animal per observation interval. Duplicate times are rejected. Aggregate
telemetry using a declared interval and measurement-appropriate rule (e.g. mean temperature,
sum activity); include observation counts and missing intervals in provenance. Aggregation can
hide short severe episodes, which remain relevant to welfare assessment.

## Current R APIs and differences

Official source signatures:

- `relsa_norm(set, normthese=NULL, ontime=1)`: `ontime` is a **one-based within-animal row
  index**, despite its time-point wording, not the day value. Python `baseline_time` instead
  selects actual time values and supports windows.
- `relsa_baselines(dataset=NULL, bslday=-1, variables=NULL, turnvars=NULL)`: `bslday` selects
  stored baseline rows; extrema are computed over the entire supplied normalized dataset.
- `relsa(set, bsl, a=1, drop=NULL, turnvars=NULL, relsaNA=NA)`: `a` indexes the unique IDs;
  measurements are selected positionally after the first metadata columns. The composite is
  returned under `$relsa$rms`, not `$relsa$wf`.
- `relsa_levels(refset, mypath, filename=NULL, bsl=bsl, drops=NULL, turns=NULL, ..., k=4)`:
  documents k-means-derived levels from a reference set. Nested R data-frame column handling
  and this clustering path were not executed here. The original paper's clustering of
  animal-level maxima also differs from KDE of all longitudinal observations.

The checked `relsa()` source divides the auxiliary `wf` by the missing-variable count, then
uses its missingness to mask `rms`. At complete baseline rows this can return NA. The official
README/vignette prints zero, which the Python formula and tests preserve intentionally.
R's positional layout and row-index normalization differ from the Python named-column APIs.

The existing regression fixture transcribes the published `Ca_001` normalized values and
weights, and scores 0.00, 0.73, 0.55, 0.44, 0.44, 0.41. It tests printed-example agreement,
not a fresh R execution or equivalence for arbitrary inputs. This refresh uses only tiny
synthetic runtime data; it does not repeat earlier full published-cohort analyses.

## Persisting a scale

The CLI applies identical ordinal mappings and normalization to `--reference-data` and target
data. New reference JSON stores the preprocessing contract and `--load-reference` reuses it;
conflicting explicit options fail. Legacy JSON or programmatic `ReferenceModel` objects may
lack this contract: reproduce preprocessing explicitly and retain that provenance. JSON
contains extrema, direction, cohort counts and a label, not raw cohort records. Archive the
reference selection, units, specimen population, instrument definitions and input hashes
separately. Changing any of them requires a new declared calibration and evaluation.
