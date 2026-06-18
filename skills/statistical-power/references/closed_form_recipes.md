# Closed-Form Power Recipes

Exact argument tables and the underlying statsmodels/scipy calls for every test
the `scripts/power.py` helper supports. Use this when you need to call statsmodels
directly, understand an argument, or handle a case the wrapper doesn't cover.

The four solver quantities — `effect_size`, sample size, `alpha`, `power` — obey
one identity: pass three, set the fourth to `None`, and `solve_power` returns it.

## Table of contents
- [Two independent means (t-test)](#two-independent-means)
- [Paired / one-sample mean](#paired--one-sample-mean)
- [One-way ANOVA](#one-way-anova)
- [Two proportions](#two-proportions)
- [One proportion](#one-proportion)
- [Correlation](#correlation)
- [Chi-square (goodness-of-fit / contingency)](#chi-square)
- [Multiple regression (R² increment)](#multiple-regression)
- [Effect-size argument cheat sheet](#effect-size-units-per-test)

---

## Two independent means

Effect size = **Cohen's d** = (μ₁ − μ₂) / σ_pooled.

```python
from statsmodels.stats.power import TTestIndPower
analysis = TTestIndPower()

# n per group for d=0.5, 80% power, two-sided
n1 = analysis.solve_power(effect_size=0.5, alpha=0.05, power=0.80,
                          ratio=1.0, alternative="two-sided")

# achieved power at n1=64 per group
pw = analysis.solve_power(effect_size=0.5, nobs1=64, alpha=0.05,
                          ratio=1.0, alternative="two-sided")

# minimum detectable d at n1=30 per group, 80% power
d_min = analysis.solve_power(nobs1=30, alpha=0.05, power=0.80, ratio=1.0,
                             alternative="two-sided")
```

`ratio = nobs2 / nobs1`. For 2:1 allocation set `ratio=2.0`; the returned `nobs1`
is the smaller group. `alternative` ∈ `"two-sided"`, `"larger"`, `"smaller"`.

## Paired / one-sample mean

Effect size = **Cohen's dz** for paired (mean difference / SD of the differences),
or d for one-sample. Use `TTestPower` (single-sample solver); `nobs` is the number
of pairs / observations.

```python
from statsmodels.stats.power import TTestPower
TTestPower().solve_power(effect_size=0.4, alpha=0.05, power=0.80,
                         alternative="two-sided")  # -> number of pairs
```

Note: for paired designs dz depends on the within-pair correlation ρ:
`dz = d_raw / sqrt(2(1−ρ))`. Higher ρ ⇒ larger dz ⇒ smaller n. If you only know
the raw mean difference and SDs, estimate ρ or simulate.

## One-way ANOVA

Effect size = **Cohen's f** = sqrt(η² / (1 − η²)). `nobs` here is **total** n
across all groups; divide by `k_groups` for per-group n.

```python
from statsmodels.stats.power import FTestAnovaPower
total_n = FTestAnovaPower().solve_power(effect_size=0.25, k_groups=4,
                                        alpha=0.05, power=0.80)
per_group = total_n / 4
```

Conversions: f = 0.10 (small), 0.25 (medium), 0.40 (large). From η²:
`f = sqrt(eta2/(1-eta2))`. From R²: same formula with R².

## Two proportions

Effect size = **Cohen's h** = 2·asin(√p₁) − 2·asin(√p₂). Convert proportions to h,
then use the normal approximation `NormalIndPower`.

```python
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize
h = proportion_effectsize(0.40, 0.55)
n1 = NormalIndPower().solve_power(effect_size=h, alpha=0.05, power=0.80,
                                  ratio=1.0, alternative="two-sided")
```

Alternative (exact-ish, gives per-group n directly, handles unequal n via `ratio`):

```python
from statsmodels.stats.proportion import samplesize_proportions_2indep_onetail
# one-sided; double alpha intent by passing alpha/... per your convention
```

For small samples or rare events, prefer **simulation** with the exact test you'll
run (Fisher's exact, or a chi-square with continuity correction).

## One proportion

Test p against a fixed reference p₀. Convert both to the arcsine scale via Cohen's h
and treat the reference group as infinite (`ratio=0`).

```python
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize
h = proportion_effectsize(0.60, 0.50)
n = NormalIndPower().solve_power(effect_size=h, alpha=0.05, power=0.80, ratio=0.0)
```

For exact binomial planning use `statsmodels.stats.proportion.proportion_effectsize`
with the exact-test power via simulation if the sample is small.

## Correlation

Effect size = **Pearson r**. No statsmodels solver; use the Fisher z transform
(implemented in `power.py`). Required n for r at power 1−β, two-sided:

```
z_r = arctanh(r)
n   = ((z_{1-α/2} + z_{1-β}) / z_r)^2 + 3
```

`pingouin.power_corr(r=0.3, power=0.8, alternative="two-sided")` gives the same
answer if you prefer a library call.

## Chi-square

Effect size = **Cohen's w** = sqrt(Σ (p_i − p0_i)² / p0_i). For a contingency table,
`w = sqrt(χ²/N)` and equals Cramér's V·sqrt(min(r−1, c−1)). Degrees of freedom:
goodness-of-fit `dof = k − 1`; contingency `dof = (r−1)(c−1)`. `n_bins = dof + 1`.

```python
from statsmodels.stats.power import GofChisquarePower
n = GofChisquarePower().solve_power(effect_size=0.3, n_bins=5, alpha=0.05, power=0.80)
```

w benchmarks: 0.10 (small), 0.30 (medium), 0.50 (large).

## Multiple regression

Effect size = **Cohen's f²** = R²/(1−R²) for the overall model, or
ΔR²/(1−R²_full) for a set of added predictors. `power.py` solves this directly via
the noncentral F (noncentrality λ = f²·n), which is more reliable than
statsmodels' `FTestPower` for sample-size search.

```python
from power import sample_size, power
# detect f^2 = 0.15 from 3 tested predictors (3 total in the model)
sample_size("linear_regression", effect_size=0.15, df_num=3, k_total=3, power=0.80)
```

- `df_num` = number of predictors being **tested** (the numerator df).
- `k_total` = total predictors in the model (including controls). `df_denom = n − k_total − 1`.

f² benchmarks: 0.02 (small), 0.15 (medium), 0.35 (large).

## Effect-size units per test

| Test | `power.py` `test=` | Effect size | Small / Medium / Large |
|------|--------------------|-------------|------------------------|
| Two independent means | `t_ind` | Cohen's d | 0.2 / 0.5 / 0.8 |
| Paired / one-sample | `t_paired`, `t_one` | Cohen's d (dz) | 0.2 / 0.5 / 0.8 |
| One-way ANOVA | `anova` | Cohen's f | 0.1 / 0.25 / 0.4 |
| Two proportions | `two_proportions` | Cohen's h (auto from props) | 0.2 / 0.5 / 0.8 |
| One proportion | `one_proportion` | Cohen's h (auto) | 0.2 / 0.5 / 0.8 |
| Correlation | `correlation` | Pearson r | 0.1 / 0.3 / 0.5 |
| Chi-square | `chi2` | Cohen's w | 0.1 / 0.3 / 0.5 |
| Regression (ΔR²) | `linear_regression` | Cohen's f² | 0.02 / 0.15 / 0.35 |

Benchmarks are last-resort conventions — prefer a smallest-effect-of-interest.
See `effect_sizes.md`.
