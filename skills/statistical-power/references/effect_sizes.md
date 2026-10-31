# Choosing and Converting Effect Sizes

The effect size is the input that makes or breaks a power analysis, and it is the
one people most often get wrong. Power computed from a guessed or inflated effect
is worse than no power analysis, because it carries false authority. This file
covers how to pick a defensible value and how to convert between the metrics
different tests use.

## How to choose (in order of preference)

### 1. Smallest effect size of interest (SESOI) — best
Power to detect the smallest effect that would actually **change a decision** or
matter scientifically/clinically, not the effect you hope or expect to see. Ways to
set it:
- **Anchor-based:** the smallest difference patients/users can perceive or that
  crosses a clinical threshold (e.g. a 5-point change on a validated scale).
- **Resource/decision-based:** the smallest effect that would justify adopting the
  intervention given its cost.
- **Benchmark-based:** an effect smaller than which you'd treat the result as
  practically null.

Powering on the SESOI is the most defensible choice: if the true effect is larger,
you're even better powered; if it's smaller, you've decided it doesn't matter.

### 2. Prior estimate — but shrink it
Pilot estimates are often very uncertain. Publication or significance-based
selection can bias an available estimate upward; it does not make every pilot
upward-biased. Use a relevant synthesis, justified shrinkage/assurance model, or
plausible range. A confidence-bound safeguard needs a prespecified confidence
level and direction. If the interval includes zero, no finite sample achieves
high power against every value in it; do not take an absolute negative endpoint
and call it conservative. There is no universal pilot-size cutoff that makes
effect estimation reliable.

### 3. Convention — last resort, and say so
Cohen's small/medium/large are arbitrary and field-blind. They were never meant as
substitutes for domain knowledge. Use them only when nothing better exists, state
explicitly that you did and examine several values. A generic "small" label is
not a scientific justification for any particular field.

## Always do a sensitivity analysis
Whatever you pick, report how required n varies across a plausible range of effects
(e.g. a power curve, or a small table of n at d = 0.3, 0.4, 0.5). A single n hides
the dominant source of uncertainty. This is the actual deliverable of a good power
analysis.

## Benchmark table (Cohen's conventions)

| Metric | Used for | Small | Medium | Large |
|--------|----------|-------|--------|-------|
| d | mean differences (t-tests) | 0.20 | 0.50 | 0.80 |
| f | ANOVA | 0.10 | 0.25 | 0.40 |
| f² | regression / multiple R² | 0.02 | 0.15 | 0.35 |
| r | correlation | 0.10 | 0.30 | 0.50 |
| η² (eta-squared) | ANOVA variance explained | 0.01 | 0.06 | 0.14 |
| h | proportions (arcsine) | 0.20 | 0.50 | 0.80 |
| w | chi-square | 0.10 | 0.30 | 0.50 |
Odds ratios have no universal small/medium/large thresholds. The same OR implies
different absolute risk differences at different baseline risks; use a justified
baseline and direction.

## Conversions

**d ↔ r** (population/two-group planning conversion to point-biserial r,
equal allocation and common within-group variance; not a general Pearson-r
conversion or an exact finite-sample correction)
```
r = d / sqrt(d^2 + 4)            # equal groups
d = 2r / sqrt(1 - r^2)
```

**d ↔ Cohen's f**  (k groups; for two equal groups f = d/2)
```
f = abs(d) / 2                   # two equal groups; f is nonnegative
```

**f ↔ η²**
```
f   = sqrt(eta2 / (1 - eta2))
eta2 = f^2 / (1 + f^2)
```

**f² ↔ R²**  (regression)
```
f2 = R2 / (1 - R2)               # whole model
f2 = dR2 / (1 - R2_full)         # increment from added predictors
```

**proportions → Cohen's h**
```
h = 2*asin(sqrt(p1)) - 2*asin(sqrt(p2))
```
In Python: `statsmodels.stats.proportion.proportion_effectsize(p1, p2)`.

**proportions → Cohen's w** (for chi-square, against expected p0_i)
```
w = sqrt( sum( (p_i - p0_i)^2 / p0_i ) )
```
For a Pearson chi-square statistic without continuity correction, `w = sqrt(chi2 / N)`, and `w = V * sqrt(min(r-1, c-1))` where V is
Cramér's V.

**odds ratio → log-odds** (for logistic-regression power by simulation)
```
beta = log(OR)                   # log-odds change per specified predictor unit
```

For a continuous predictor, OR per SD is `exp(beta * SD_x)`; for a binary
predictor it compares x=1 against x=0. With an intercept-only baseline `p0`,
`intercept=log(p0/(1-p0))` gives the conditional risk at x=0, not generally the
marginal population risk after adding covariate effects.

**standardized → raw**
A standardized effect is only as good as the SD you divide by. If you know the raw
difference and the SD, work in raw units and convert at the end:
`d = (mean1 - mean2) / sd_pooled`. For paired designs, `dz` uses the SD of the
*differences*, which depends on the within-pair correlation — see
`closed_form_recipes.md`.

## Common mistakes

- **Using the observed/expected effect instead of the SESOI** — you end up powered
  for your hopes, not for what matters.
- **Ignoring prior-estimate uncertainty and selection bias** — an optimistic effect can understate required n.
- **Mixing up d and f, or η² and f²** — they differ by the conversions above; a
  factor-of-2 error in d quadruples or quarters the required n.
- **Reporting one number** — always show the sensitivity range.
- **Treating Cohen's benchmarks as truth** — they're conventions, not measurements.


Reviewed 2026-10-01 against [Lakens (2022), Sample Size Justification](https://doi.org/10.1525/collabra.33267),
[statsmodels proportion_effectsize](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.proportion_effectsize.html),
and [statsmodels one-way effect-size definitions](https://www.statsmodels.org/stable/generated/statsmodels.stats.oneway.effectsize_oneway.html).
These are planning assumptions and algebraic conversions, not validation of a
scientific SESOI, pilot population, or clinical decision threshold.
