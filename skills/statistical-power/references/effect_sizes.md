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
Pilot studies and published effects are **biased upward** (publication bias, the
"winner's curse," and the fact that significant pilots are the ones that get
followed up). Powering on a raw pilot d routinely underpowers the real study. If
you must use a prior estimate:
- Use the **lower bound of its confidence interval**, or
- Apply a **shrinkage / safeguard** (e.g. Perugini et al.'s safeguard power uses the
  CI lower limit), and
- Never rely on a single small pilot (n < ~50) for a point estimate of the effect.

### 3. Convention — last resort, and say so
Cohen's small/medium/large are arbitrary and field-blind. They were never meant as
substitutes for domain knowledge. Use them only when nothing better exists, state
explicitly that you did, and prefer "small" unless you have a reason — most real
effects in many fields are small.

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
| OR | 2×2 odds ratio | ~1.5 | ~2.5 | ~4.3 |

(OR benchmarks are very context-dependent and depend on the base rate — treat as
rough only.)

## Conversions

**d ↔ r**  (two-group comparison ↔ point-biserial)
```
r = d / sqrt(d^2 + 4)            # equal groups
d = 2r / sqrt(1 - r^2)
```

**d ↔ Cohen's f**  (k groups; for two equal groups f = d/2)
```
f = d / 2                        # two groups
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
For a 2×2 table, `w = sqrt(chi2 / N)`, and `w = V * sqrt(min(r-1, c-1))` where V is
Cramér's V.

**odds ratio → log-odds** (for logistic-regression power by simulation)
```
beta = log(OR)                   # coefficient to plug into the simulated linear predictor
```

**standardized → raw**
A standardized effect is only as good as the SD you divide by. If you know the raw
difference and the SD, work in raw units and convert at the end:
`d = (mean1 - mean2) / sd_pooled`. For paired designs, `dz` uses the SD of the
*differences*, which depends on the within-pair correlation — see
`closed_form_recipes.md`.

## Common mistakes

- **Using the observed/expected effect instead of the SESOI** — you end up powered
  for your hopes, not for what matters.
- **Copying a published d without shrinking** — inflated by publication bias.
- **Mixing up d and f, or η² and f²** — they differ by the conversions above; a
  factor-of-2 error in d quadruples or quarters the required n.
- **Reporting one number** — always show the sensitivity range.
- **Treating Cohen's benchmarks as truth** — they're conventions, not measurements.
