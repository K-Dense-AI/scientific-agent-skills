# Statistical Test Selection Guide

Choose a model for the estimand, sampling unit and dependence structure. A Shapiro-Wilk/Levene p-value is not an automatic switch between tests. The routes below are candidates whose assumptions must match the study.

## Decision Tree for Test Selection

### 1. Comparing Groups

#### Two Independent Groups
- **Independent mean contrast**: Welch's t-test (`pg.ttest(..., correction=True)`); pooled Student's test only with justified common variance
- **Rank/distribution contrast**: Mann-Whitney U (Wilcoxon rank-sum); a median shift interpretation requires comparable distributional shapes
- **Binary outcome**: Chi-square test or Fisher's exact test (if expected counts < 5)
- **Ordinal outcome**: Mann-Whitney U test

#### Two Paired/Dependent Groups
- **Paired mean contrast**: Paired t-test on aligned within-subject differences; assess differences, not marginal normality
- **Symmetric paired difference distribution**: Wilcoxon signed-rank; otherwise consider a sign test for the prespecified median-difference question
- **Binary outcome**: McNemar's test
- **Ordinal outcome**: Signed-rank only when difference magnitudes and symmetry are meaningful; consider a sign test or ordinal model otherwise

#### Three or More Independent Groups
- **Continuous outcome, normally distributed, equal variances**: One-way ANOVA
- **Continuous outcome, normally distributed, unequal variances**: Welch's ANOVA
- **Independent rank/distribution contrast**: Kruskal-Wallis H; a median interpretation requires comparable shapes
- **Binary/categorical outcome**: Chi-square test
- **Ordinal outcome**: Kruskal-Wallis H test

#### Three or More Paired/Dependent Groups
- **Repeated continuous means**: Repeated measures ANOVA with suitable covariance/sphericity correction, or a mixed model
- **Complete blocks/repeated rank contrast**: Friedman test; missing/unequal visits may require a model
- **Binary outcome**: Cochran's Q test

#### Multiple Factors (Factorial Designs)
- **Continuous outcome**: Two-way ANOVA (or higher-way ANOVA)
- **With covariates**: ANCOVA
- **Mixed within and between factors**: Mixed ANOVA

### 2. Relationships Between Variables

#### Two Continuous Variables
- **Linear association**: Pearson correlation; usual small-sample parametric inference assumes an appropriate joint model
- **Monotone rank association**: Spearman rank correlation, selected by the estimand rather than a marginal normality test
- **Rank-based data**: Spearman or Kendall's tau

#### One Continuous Outcome, One or More Predictors
- **Single continuous predictor**: Simple linear regression
- **Multiple continuous/categorical predictors**: Multiple linear regression
- **Categorical predictors**: ANOVA/ANCOVA framework
- **Non-linear relationships**: Polynomial regression or generalized additive models (GAM)

#### Binary Outcome
- **Single predictor**: Logistic regression
- **Multiple predictors**: Multiple logistic regression
- **Rare events**: Exact logistic regression or Firth's method

#### Count Outcome
- **Poisson-distributed**: Poisson regression
- **Overdispersed counts**: Negative binomial regression
- **Excess zeros with a justified separate structural-zero process**: Zero-inflated Poisson/negative binomial; many zeros alone do not establish zero inflation

#### Time-to-Event Outcome
- **Comparing survival curves**: Log-rank test
- **Modeling with covariates**: Cox proportional hazards regression
- **Parametric survival models**: Weibull, exponential, log-normal

### 3. Agreement and Reliability

#### Inter-Rater Reliability
- **Categorical ratings, 2 raters**: Cohen's kappa
- **Categorical ratings, >2 raters**: Fleiss' kappa or Krippendorff's alpha
- **Continuous ratings**: Intraclass correlation coefficient (ICC)

#### Test-Retest Reliability
- **Continuous measurements**: Choose and report an ICC model (agreement/consistency, single/average, random/fixed raters); Pearson correlation alone does not measure agreement
- **Internal consistency**: Cronbach's alpha

#### Agreement Between Methods
- **Continuous measurements**: Bland-Altman analysis
- **Categorical classifications**: Cohen's kappa

### 4. Categorical Data Analysis

#### Contingency Tables
- **2x2 table**: Chi-square test or Fisher's exact test
- **Larger than 2x2**: Chi-square when expected counts support the approximation; current SciPy also supports generalized exact/resampling procedures
- **Ordered categories**: Cochran-Armitage trend test
- **Paired categories**: McNemar's test (2x2) or McNemar-Bowker test (larger)

### 5. Bayesian Alternatives

Any of the above tests can be performed using Bayesian methods:
- **Group comparisons**: Bayesian t-test, Bayesian ANOVA
- **Correlations**: Bayesian correlation
- **Regression**: Bayesian linear/logistic regression

**Advantages of Bayesian approaches:**
- Provides probability of hypotheses given data
- Naturally incorporates prior information
- Provides credible intervals instead of confidence intervals
- No p-value interpretation issues

## Key Considerations

### Sample Size
- No universal n=30 rule establishes validity or power. For small samples assess model assumptions; exact/permutation methods need exchangeability, tie handling and the correct sampling unit
- Very large samples: Even small effects may be statistically significant; focus on effect sizes

### Multiple Comparisons
- When conducting multiple tests, adjust for multiple comparisons using:
  - Bonferroni correction (conservative)
  - Holm-Bonferroni (less conservative)
  - False Discovery Rate (FDR) control (Benjamini-Hochberg)
  - Tukey HSD for post-hoc ANOVA comparisons

### Missing Data
- Complete case analysis (listwise deletion)
- Multiple imputation
- Maximum likelihood methods
- Ensure missing data mechanism is understood (MCAR, MAR, MNAR)

### Effect Sizes
- Always report effect sizes alongside p-values
- See `effect_sizes_and_power.md` for guidance

### Study Design Considerations
- Randomized controlled trials: Standard parametric/non-parametric tests
- Observational studies: Consider confounding and use regression/matching
- Clustered/nested data: Use mixed-effects models or GEE
- Time series: Use time series methods (ARIMA, etc.)

## Implementation sources and limits

Reviewed 2026-10-01: [SciPy Mann-Whitney](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mannwhitneyu.html), [Wilcoxon](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html), [Pingouin repeated measures](https://pingouin-stats.org/generated/pingouin.rm_anova.html). Small tied samples need an appropriate permutation/asymptotic method; the default automatic method is not universally exact. Compute rounded difference scores when floating-point subtraction creates spurious distinct ranks. Survival, Firth/exact logistic, agreement, missing-data and complex factorial routes here are design guidance, not executed implementations.
