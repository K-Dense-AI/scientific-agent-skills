# Effect Sizes and Power Analysis

This document provides guidance on calculating, interpreting, and reporting effect sizes, as well as conducting power analyses for study planning.

## Why Effect Sizes Matter

1. **Statistical significance ≠ practical significance**: p-values measure incompatibility with a null model under its assumptions, not existence or magnitude
2. **Sample size dependent**: With large samples, trivial effects become "significant"
3. **Interpretation**: Effect sizes provide magnitude and practical importance
4. **Meta-analysis**: Effect sizes enable combining results across studies
5. **Power analysis**: Required for sample size determination

**Golden rule**: ALWAYS report effect sizes alongside p-values.

---

## Effect Sizes by Analysis Type

### T-Tests and Mean Differences

#### Cohen's d (Standardized Mean Difference)

**Formula**:
- Independent groups: d = (M₁ - M₂) / SD_pooled
- Paired groups: specify the standardizer. d_z = M_diff / SD_diff; d_av = M_diff / sqrt((SD_pre² + SD_post²)/2). These are different effects.

**Interpretation** (Cohen, 1988):
- Small: |d| = 0.20
- Medium: |d| = 0.50
- Large: |d| = 0.80

**Context-dependent interpretation**:
- Justify a smallest scientifically meaningful effect from the outcome, intervention and context; no discipline-wide threshold is universally meaningful.
- In medicine: Small effect sizes can be clinically important

**Python calculation**:
```python
import pingouin as pg
import numpy as np

# Independent t-test with effect size
result = pg.ttest(group1, group2, correction=False)
cohens_d = pg.compute_effsize(group1, group2, eftype='cohen')  # signed; ttest returns abs(d)
# (pingouin 0.6.0 renamed columns; on 0.5.x use 'p-val', 'cohen-d', 'CI95%', 'p-unc')

# Manual calculation
mean_diff = np.mean(group1) - np.mean(group2)
n1, n2 = len(group1), len(group2)
pooled_std = np.sqrt(((n1 - 1) * np.var(group1, ddof=1) + (n2 - 1) * np.var(group2, ddof=1)) / (n1 + n2 - 2))
cohens_d = mean_diff / pooled_std

# Paired t-test
result = pg.ttest(pre, post, paired=True)
d_av = pg.compute_effsize(pre, post, paired=True, eftype='cohen')
d_z = pg.compute_effsize(pre, post, paired=True, eftype='cohen_dz')
```

**Confidence intervals for independent pooled d** (approximate parametric interval; supply analyzed, non-missing sample sizes; do not reuse this formula for d_av or assume unequal-variance validity):
```python
import pingouin as pg

# compute_effsize_from_t returns only the point estimate;
# get the CI separately with compute_esci
d = pg.compute_effsize(group1, group2, eftype='cohen')
ci = pg.compute_esci(stat=d, nx=len(group1), ny=len(group2),
                     eftype='cohen', confidence=0.95)
```

---

#### Hedges' g (Bias-Corrected d)

**Why use it**: Cohen's d has slight upward bias with small samples (n < 20)

**Formula**: g = d × correction_factor, where correction_factor = 1 - 3/(4df - 1)

**Python calculation**:
```python
# pg.ttest output has no Hedges' g column; compute it directly
hedges_g = pg.compute_effsize(group1, group2, eftype='hedges')
```

**Use Hedges' g when**:
- Sample sizes are small (n < 20 per group)
- Conducting meta-analyses (standard in meta-analysis)

---

#### Glass's Δ (Delta)

**When to use**: When one group is a control with known variability

**Formula**: Δ = (M₁ - M₂) / SD_control

**Use cases**:
- Clinical trials (use control group SD)
- When treatment affects variability

---

### ANOVA

#### Eta-squared (η²)

**What it measures**: Proportion of total variance explained by factor

**Formula**: η² = SS_effect / SS_total

**Interpretation**:
- Small: η² = 0.01 (1% of variance)
- Medium: η² = 0.06 (6% of variance)
- Large: η² = 0.14 (14% of variance)

**Limitation**: In multi-factor designs each effect's η² shrinks as other factors are added (orthogonal decompositions give additive shares; Type II/III sums in unbalanced designs need not add to total SS); it is partial η² that can sum to > 1.0 across factors

**Python calculation**:
```python
import pingouin as pg

# One-way ANOVA (detailed=True is required for the SS column)
aov = pg.anova(dv='value', between='group', data=df, detailed=True)
eta_squared = aov['SS'][0] / aov['SS'].sum()

# Or read pingouin's np2 column, which is PARTIAL eta-squared:
partial_eta_sq = aov['np2'][0]
# np2 coincides with classical eta-squared only for one-way (single-factor) designs
```

---

#### Partial Eta-squared (η²_p)

**What it measures**: Proportion of variance explained by factor, excluding other factors

**Formula**: η²_p = SS_effect / (SS_effect + SS_error)

**Interpretation**: Same benchmarks as η²

**When to use**: Multi-factor ANOVA (standard in factorial designs)

**Limitation**: Across factors, partial η² values can sum to > 1.0 — they are not additive shares of total variance

**Python calculation**:
```python
aov = pg.anova(dv='value', between=['factor1', 'factor2'], data=df)
# pingouin reports partial eta-squared by default
partial_eta_sq = aov['np2']
```

---

#### Omega-squared (ω²)

**What it measures**: Less biased estimate of population variance explained

**Why use it**: η² overestimates effect size; ω² provides better population estimate

**Formula**: ω² = (SS_effect - df_effect × MS_error) / (SS_total + MS_error)

**Interpretation**: Same benchmarks as η², but typically smaller values

**Python calculation** (one-way table with effect row first and residual row last; the estimator can be negative, so state any truncation convention):
```python
def omega_squared(aov_table):
    ss_effect = aov_table.loc[0, 'SS']
    ss_total = aov_table['SS'].sum()
    ms_error = aov_table.loc[aov_table.index[-1], 'MS']  # Residual MS
    df_effect = aov_table.loc[0, 'DF']

    omega_sq = (ss_effect - df_effect * ms_error) / (ss_total + ms_error)
    return omega_sq
```

---

#### Cohen's f

**What it measures**: Effect size for ANOVA (analogous to Cohen's d)

**Formula**: f = √(η² / (1 - η²))

**Interpretation**:
- Small: f = 0.10
- Medium: f = 0.25
- Large: f = 0.40

**Python calculation**:
```python
eta_squared = 0.06  # From ANOVA
cohens_f = np.sqrt(eta_squared / (1 - eta_squared))
```

**Use in power analysis**: Required for ANOVA power calculations

---

### Correlation

#### Pearson's r / Spearman's ρ

**Interpretation**:
- Small: |r| = 0.10
- Medium: |r| = 0.30
- Large: |r| = 0.50

**Important notes**:
- For Pearson correlation in simple OLS with an intercept, r² equals R². Spearman ρ² concerns ranks and is not raw-outcome variance explained.
- Pearson r = 0.30 gives r² = 0.09; association is not causal explanation.
- Consider direction (positive/negative) and context

**Python calculation**:
```python
import pingouin as pg

# Pearson correlation with CI
result = pg.corr(x, y, method='pearson')
r = result['r'].values[0]
ci = result['CI95'].values[0]  # pingouin 0.6.0 renamed CI95% to CI95

# Spearman correlation
result = pg.corr(x, y, method='spearman')
rho = result['r'].values[0]
```

---

### Regression

#### R² (Coefficient of Determination)

**What it measures**: Proportion of variance in Y explained by model

**Interpretation**:
- Small: R² = 0.02
- Medium: R² = 0.13
- Large: R² = 0.26

**Context-dependent**:
- Interpret R² relative to outcome variability, measurement error and purpose; no field-wide cutoff establishes fit or predictive performance. Evaluate predictions on held-out data when prediction is the goal.

**Python calculation**:
```python
import statsmodels.api as sm

# Using statsmodels (add_constant adds the intercept column)
model = sm.OLS(y, sm.add_constant(X)).fit()
r_squared = model.rsquared
adjusted_r_squared = model.rsquared_adj

# Manual
r_squared = 1 - (SS_residual / SS_total)
```

---

#### Adjusted R²

**Why use it**: R² artificially increases when adding predictors; adjusted R² penalizes model complexity

**Formula**: R²_adj = 1 - (1 - R²) × (n - 1) / (n - k - 1)

**When to use**: Always report alongside R² for multiple regression

---

#### Standardized Regression Coefficients (β)

**What it measures**: Effect of one-SD change in predictor on outcome (in SD units)

**Interpretation**: Conditional on all included predictors and their coding; β has no universal small/medium/large thresholds and is not Cohen's d.

**Python calculation**:
```python
import statsmodels.api as sm

# Numeric predictor DataFrame, each column nonconstant; standardize columnwise
X_std = (X - X.mean()) / X.std()
y_std = (y - y.mean()) / y.std()

model = sm.OLS(y_std, sm.add_constant(X_std)).fit()
beta = model.params
```

---

#### f² (Cohen's f-squared for Regression)

**What it measures**: Effect size for individual predictors or model comparison

**Formula**: f² = (R²_AB - R²_A) / (1 - R²_AB)

Where:
- R²_AB = R² for full model with predictor
- R²_A = R² for reduced model without predictor

**Interpretation**:
- Small: f² = 0.02
- Medium: f² = 0.15
- Large: f² = 0.35

**Python calculation**:
```python
# Compare two nested models
import statsmodels.api as sm
# Same observations and outcome in both models; include intercepts
model_full = sm.OLS(y, sm.add_constant(X_full)).fit()
model_reduced = sm.OLS(y, sm.add_constant(X_reduced)).fit()

r2_full = model_full.rsquared
r2_reduced = model_reduced.rsquared

f_squared = (r2_full - r2_reduced) / (1 - r2_full)
```

---

### Categorical Data Analysis

#### Cramér's V

**What it measures**: Association strength for χ² test (works for any table size)

**Formula**: V = √(χ² / (n × (k - 1)))

Where k = min(rows, columns)

**Interpretation** (benchmarks depend on df* = min(rows, columns) − 1):

| df* | Small | Medium | Large |
|-----|-------|--------|-------|
| 1 (2×2) | 0.10 | 0.30 | 0.50 |
| 2 | 0.07 | 0.21 | 0.35 |
| 3 | 0.06 | 0.17 | 0.29 |

**For 2×2 tables**: Use phi coefficient (φ)

**Python calculation**:
```python
import numpy as np
from scipy.stats.contingency import association

# Cramér's V
cramers_v = association(contingency_table, method='cramer')

# Phi coefficient (2x2): |phi| equals Cramér's V for a 2x2 table.
# Caution: method='pearson' is Pearson's contingency coefficient, NOT phi.
a, b, c, d = np.asarray(contingency_table, dtype=float).ravel()
phi = (a * d - b * c) / np.sqrt((a + b) * (c + d) * (a + c) * (b + d))  # signed phi
```

---

#### Odds Ratio (OR) and Risk Ratio (RR)

**For 2×2 contingency tables**:

|           | Outcome + | Outcome - |
|-----------|-----------|-----------|
| Exposed   | a         | b         |
| Unexposed | c         | d         |

**Odds Ratio**: OR = (a/b) / (c/d) = ad / bc

**Interpretation**:
- OR = 1: No association
- OR > 1: Positive association (increased odds)
- OR < 1: Negative association (decreased odds)
- OR = 2: Twice the odds
- OR = 0.5: Half the odds

**Risk Ratio**: RR = (a/(a+b)) / (c/(c+d))

**When to use**:
- Cohort studies: Use RR (more interpretable)
- Case-control studies: Use OR (RR not available)
- Logistic regression: OR is natural output

**Python calculation**:
```python
import numpy as np
from scipy import stats
import statsmodels.api as sm

# From contingency table
odds_ratio = (a * d) / (b * c)

# For a 2x2 table with method=None, Fisher returns sample OR and p-value (no CI);
# larger/resampled tables have a different statistic. Require nonnegative integer counts.
table = np.array([[a, b], [c, d]])
oddsratio, pvalue = stats.fisher_exact(table)

# Odds-ratio confidence interval (scipy >= 1.10; conditional MLE estimate)
or_result = stats.contingency.odds_ratio(table)
ci = or_result.confidence_interval(confidence_level=0.95)

# From logistic regression
model = sm.Logit(y_binary, sm.add_constant(X)).fit()
odds_ratios = np.exp(model.params)  # Exponentiate coefficients
ci = np.exp(model.conf_int())  # Exponentiate CIs
```

---

### Nonparametric Effect Sizes

**Rank-biserial correlation (r_rb)**: Effect size for Mann-Whitney U and Wilcoxon signed-rank tests (range −1 to 1; interpret |r_rb| roughly like r). Returned by `pg.mwu` and `pg.wilcoxon` as the `RBC` column.

**Common-language effect size (CLES)**: P(X > Y) + 0.5 P(X = Y) for independent group draws (0.5 is no directional superiority, not proof of identical distributions). Returned by `pg.mwu` as `CLES`.

**r = z / √N**: Classic effect size when a z approximation is reported for Mann-Whitney/Wilcoxon (small 0.10, medium 0.30, large 0.50).

**Epsilon-squared (ε²)**: Effect size for Kruskal-Wallis: ε² = H × (n + 1) / (n² − 1).

**Python calculation**:
```python
import numpy as np
import pandas as pd
import pingouin as pg

res = pg.mwu(group1, group2)
print(res[['U_val', 'p_val', 'RBC', 'CLES']])

# Kruskal-Wallis with epsilon-squared
df = pd.DataFrame({'value': np.concatenate([group1, group2, group3]),
                   'group': np.repeat(['a', 'b', 'c'],
                                      [len(group1), len(group2), len(group3)])})
kw = pg.kruskal(df, dv='value', between='group')
H, n = kw['H'].values[0], len(df)
epsilon_sq = H * (n + 1) / (n**2 - 1)
```

---

### Bayesian Evidence (Not an Effect Size)

#### Bayes Factor (BF)

**What it measures**: Ratio of evidence for alternative vs. null hypothesis

**Interpretation**:
- BF₁₀ = 1: Equal evidence for H₁ and H₀
- BF₁₀ = 3: the data have 3× greater marginal likelihood under H₁ than H₀ (moderate evidence)
- BF₁₀ = 10: the data have 10× greater marginal likelihood under H₁ than H₀ (strong evidence)
- BF₁₀ > 100: Decisive evidence for H₁ (30-100 counts as "very strong" on the Jeffreys scale)
- BF₁₀ = 0.33: the data have about 3× greater marginal likelihood under H₀ than H₁
- BF₁₀ = 0.10: the data have 10× greater marginal likelihood under H₀ than H₁

Posterior odds = Bayes factor × prior odds; BF alone is not posterior model probability. For the full Jeffreys interpretation table and BF reporting language, see `bayesian_statistics.md`.

**Python calculation**:
```python
import pingouin as pg

# Pingouin 0.5+: two-sided BF10 on independent t-tests; use BayesFactor/JASP/PyMC for full inference
result = pg.ttest(group1, group2, correction=False)
bf10 = float(result['BF10'].values[0])  # formatted string in default Pingouin output
```

---

### Bootstrap Confidence Intervals

When no analytic CI exists for an effect size (or its assumptions are doubtful), bootstrap one:

```python
import numpy as np
from scipy import stats

def cohen_d(x, y):
    nx, ny = len(x), len(y)
    sp = np.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1))
                 / (nx + ny - 2))
    return (np.mean(x) - np.mean(y)) / sp

boot = stats.bootstrap((group1, group2), cohen_d, n_resamples=9999,
                       method='BCa', rng=np.random.default_rng(42))
print(boot.confidence_interval)  # 95% BCa CI by default
```

Resample the sampling unit: correlations and paired effects require `paired=True`, and clustered designs require cluster resampling. BCa can be undefined for degenerate/discrete samples; inspect warnings, finite interval endpoints and Monte Carlo stability. More resamples cannot fix the wrong design.

---

## Power Analysis

### Concepts

**Statistical power**: Probability of rejecting a specified null under a specified alternative effect, variance and design (1 - β).

**Conventional standards**:
- Power = 0.80 (80% chance of detecting effect)
- α = 0.05 (5% Type I error rate)

**Four interconnected parameters** (given 3, can solve for 4th):
1. Sample size (n)
2. Effect size (d, f, etc.)
3. Significance level (α)
4. Power (1 - β)

---

### A Priori Power Analysis (Planning)

**Purpose**: Determine required sample size before study

**Steps**:
1. Specify expected effect size (from literature, pilot data, or minimum meaningful effect)
2. Set α level (typically 0.05)
3. Set desired power (typically 0.80)
4. Calculate required n

**Python implementation**:
```python
from statsmodels.stats.power import (
    tt_ind_solve_power,
    zt_ind_solve_power,
    FTestAnovaPower,
    NormalIndPower
)

# T-test power analysis
n_required = tt_ind_solve_power(
    effect_size=0.5,  # Cohen's d
    alpha=0.05,
    power=0.80,
    ratio=1.0,  # Equal group sizes
    alternative='two-sided'
)

# ANOVA power analysis (kwarg is k_groups, not ngroups)
anova_power = FTestAnovaPower()
n_total = anova_power.solve_power(
    effect_size=0.25,  # Cohen's f
    k_groups=3,
    alpha=0.05,
    power=0.80
)
# Returns the TOTAL sample size across all groups:
# f = 0.25, k = 3 -> ~158 total; round UP to 53/group, implemented total 159
import math
planned_n_per_group = math.ceil(n_required)
planned_anova_per_group = math.ceil(n_total / 3)

# Correlation power analysis
from pingouin import power_corr
n_required = power_corr(r=0.30, power=0.80, alpha=0.05)
```

---

### Post Hoc Power Analysis (After Study)

**⚠️ CAUTION**: Post hoc power is controversial and often not recommended

**Why it's problematic**:
- Observed power is a direct function of p-value
- If p > 0.05, power is always low
- Provides no additional information beyond p-value
- Can be misleading

**When it might be acceptable**:
- Study planning for future research
- Using effect size from multiple studies (not just your own)
- Explicit goal is sample size for replication

**Better alternatives**:
- Report confidence intervals for effect sizes
- Conduct sensitivity analysis
- Report minimum detectable effect size

---

### Sensitivity Analysis

**Purpose**: Determine minimum detectable effect size given study parameters

**When to use**: After study is complete, to understand study's capability

**Python implementation**:
```python
# What effect size could we detect with n=50 per group?
detectable_effect = tt_ind_solve_power(
    effect_size=None,  # Solve for this
    nobs1=50,
    alpha=0.05,
    power=0.80,
    ratio=1.0,
    alternative='two-sided'
)

print(f"With n=50 per group, we could detect d ≥ {detectable_effect:.2f}")
```

---

## Reporting Effect Sizes

Numerical prose templates below are illustrative, not computed study results; use the actual fitted estimates and interval method.

### APA Style Guidelines

**T-test example**:
> "Group A (M = 75.2, SD = 8.5) scored significantly higher than Group B (M = 68.3, SD = 9.2), t(98) = 3.82, p < .001, d = 0.77, 95% CI [0.36, 1.18]."

**ANOVA example**:
> "There was a significant main effect of treatment condition on test scores, F(2, 87) = 8.45, p < .001, η²p = .16. Post hoc comparisons using Tukey's HSD revealed..."

**Correlation example**:
> "There was a moderate positive correlation between study time and exam scores, r(148) = .42, p < .001, 95% CI [.27, .55]."

**Regression example**:
> "The regression model significantly predicted exam scores, F(3, 146) = 45.2, p < .001, R² = .48. Study hours (β = .52, p < .001) and prior GPA (β = .31, p < .001) were significant predictors."

**Bayesian example**: See `bayesian_statistics.md` (Reporting Bayesian Results) for Bayes Factor and posterior reporting templates.

---

## Effect Size Pitfalls

1. **Don't only rely on benchmarks**: Context matters; small effects can be meaningful
2. **Report confidence intervals**: CIs show precision of effect size estimate
3. **Distinguish statistical vs. practical significance**: Large n can make trivial effects "significant"
4. **Consider cost-benefit**: Even small effects may be valuable if intervention is low-cost
5. **Multiple outcomes**: Effect sizes vary across outcomes; report all
6. **Don't cherry-pick**: Report effects for all planned analyses
7. **Publication bias**: Published effects are often overestimated

---

## Quick Reference Table

| Analysis | Effect Size | Small | Medium | Large |
|----------|-------------|-------|--------|-------|
| T-test | Cohen's d | 0.20 | 0.50 | 0.80 |
| ANOVA | η², ω² | 0.01 | 0.06 | 0.14 |
| ANOVA | Cohen's f | 0.10 | 0.25 | 0.40 |
| Correlation | r, ρ | 0.10 | 0.30 | 0.50 |
| Regression | R² | 0.02 | 0.13 | 0.26 |
| Regression | f² | 0.02 | 0.15 | 0.35 |
| Chi-square (df* = 1, 2×2) | Cramér's V, φ | 0.10 | 0.30 | 0.50 |
| Chi-square (df* = 2) | Cramér's V | 0.07 | 0.21 | 0.35 |
| Chi-square (df* = 3) | Cramér's V | 0.06 | 0.17 | 0.29 |

*Note*: df* = min(rows, columns) − 1.

---

## Current API Sources

Reviewed 2026-10-01: [Pingouin effect sizes](https://pingouin-stats.org/generated/pingouin.compute_effsize.html), [approximate effect intervals](https://pingouin-stats.org/generated/pingouin.compute_esci.html), [SciPy bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html), [statsmodels power](https://www.statsmodels.org/stable/stats.html#power-and-sample-size-calculations).

## Resources

- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences* (2nd ed.)
- Lakens, D. (2013). Calculating and reporting effect sizes
- Ellis, P. D. (2010). *The Essential Guide to Effect Sizes*
