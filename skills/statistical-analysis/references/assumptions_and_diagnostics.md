# Statistical Assumptions and Diagnostic Procedures

This document provides comprehensive guidance on checking and validating statistical assumptions for various analyses.

## General Principles

1. **Always check assumptions before interpreting test results**
2. **Use multiple diagnostic methods** (visual + formal tests)
3. **Consider robustness**: Some tests are robust to violations under certain conditions
4. **Document all assumption checks** in analysis reports
5. **Report violations and remedial actions taken**

## Common Assumptions Across Tests

### 1. Independence of Observations

**What it means**: Each observation is independent; measurements on one subject do not influence measurements on another.

**How to check**:
- Review study design and data collection procedures
- For time series: Check autocorrelation (ACF/PACF plots, Durbin-Watson test)
- For clustered data: Consider intraclass correlation (ICC)

**What to do if violated**:
- Use mixed-effects models for clustered/hierarchical data
- Use time series methods for temporally dependent data
- Use generalized estimating equations (GEE) for correlated data

**Critical severity**: HIGH - violations can severely inflate Type I error

---

### 2. Normality

**What it means**: Data or residuals follow a normal (Gaussian) distribution.

**When required**:
- Small-sample normal-theory t/ANOVA inference: the relevant errors (paired differences for paired tests), not arbitrary pooled data
- Linear regression: normal errors support exact finite-sample t/F inference; coefficient estimation itself does not require normal outcomes or predictors
- Some correlation tests (Pearson)

**How to check**:

**Visual methods** (primary):
- Q-Q (quantile-quantile) plot: Points should fall on diagonal line
- Histogram with normal curve overlay
- Kernel density plot

**Formal tests** (secondary):
- Shapiro-Wilk test (good default; scipy handles n up to ~5000 and warns above that)
- Lilliefors test (`statsmodels.stats.diagnostic.lilliefors`) — use this instead of a plain Kolmogorov-Smirnov test, which is invalid when the mean/SD are estimated from the data
- Anderson-Darling test

**Python implementation**:
```python
from scipy import stats
import matplotlib.pyplot as plt

# Shapiro-Wilk test
statistic, p_value = stats.shapiro(data)

# Q-Q plot
stats.probplot(data, dist="norm", plot=plt)
```

**Interpretation guidance**:
- Assess plots, tail behavior, sample balance, dependence and the estimand at every sample size. Formal tests have low power in small samples and detect tiny departures in large samples; non-rejection does not validate a model.
- Look for severe skewness, outliers, or bimodality

**What to do if violated**:
- **Departures**: Evaluate robustness for the target effect and design; there is no universal n=30 threshold. Prespecify robust inference or simulation-based sensitivity. Rank methods change the target and retain assumptions; they are not automatic replacements.
- **Severe violations**:
  - Transform data (log, square root, Box-Cox)
  - Use non-parametric methods
  - Use robust regression methods
  - Consider bootstrapping

**Critical severity**: MEDIUM - parametric tests are often robust to mild violations with adequate sample size

---

### 3. Homogeneity of Variance (Homoscedasticity)

**What it means**: Variances are equal across groups or across the range of predictors.

**When required**:
- Pooled Student's t-test and classical equal-variance ANOVA (not Welch tests)
- Usual homoscedastic OLS standard errors; HC3 addresses independent heteroscedastic errors, not clusters

**How to check**:

**Visual methods** (primary):
- Box plots by group (for t-test/ANOVA)
- Residuals vs. fitted values plot (for regression) - should show random scatter
- Scale-location plot (square root of standardized residuals vs. fitted)

**Formal tests** (secondary):
- Levene's test (robust to non-normality)
- Bartlett's test (sensitive to non-normality, not recommended)
- Brown-Forsythe test (median-based version of Levene's)
- Breusch-Pagan test (for regression)

**Python implementation**:
```python
from scipy import stats
import pingouin as pg

# Median-centered Levene is the Brown-Forsythe variance test
statistic, p_value = stats.levene(group1, group2, group3, center='median')

# For regression
# Breusch-Pagan test
# Note: exog must include the constant column (e.g. exog = sm.add_constant(X),
# or pass the fitted model's model.exog)
from statsmodels.stats.diagnostic import het_breuschpagan
_, p_value, _, _ = het_breuschpagan(residuals, exog)
```

**Interpretation guidance**:
- No variance-ratio cutoff certifies validity. Balanced designs can help robustness but do not remove tail, dependence or variance concerns.
- Do not choose pooled versus Welch inference based only on a preliminary variance p-value.
- For regression: Look for funnel patterns in residual plots

**What to do if violated**:
- **t-test**: Use Welch's t-test (does not assume equal variances)
- **ANOVA**: Use Welch's ANOVA or Brown-Forsythe ANOVA
- **Regression**:
  - Transform dependent variable (log, square root)
  - Use weighted least squares (WLS)
  - Use robust standard errors (HC3)
  - Use generalized linear models (GLM) with appropriate variance function

**Critical severity**: MEDIUM - tests can be robust with equal sample sizes

---

## Test-Specific Assumptions

### T-Tests

**Assumptions**:
1. Independence of observations
2. Normality (each group for independent t-test; differences for paired t-test)
3. Homogeneity only for pooled Student's independent t-test; Welch permits unequal variances

**Diagnostic workflow**:
```python
import scipy.stats as stats
import pingouin as pg

# Check normality for each group
stats.shapiro(group1)
stats.shapiro(group2)

# Check homogeneity of variance
stats.levene(group1, group2)

# Prespecify inference from the design/estimand rather than the screening p-values:
# Option 1: Welch's t-test (unequal variances)
pg.ttest(group1, group2, correction=True)  # correction=True applies Welch's
# (correction='auto' applies Welch only when sample sizes are unequal;
# correction=False forces Student's t-test)

# Option 2: A separately justified rank/distribution question
pg.mwu(group1, group2)  # Mann-Whitney U
```

---

### ANOVA

**Assumptions**:
1. Independence of observations within and between groups
2. Normality in each group
3. Homogeneity of variance across groups

**Additional considerations**:
- For repeated measures ANOVA: Sphericity assumption (Mauchly's test)

**Diagnostic workflow**:
```python
import pingouin as pg
from scipy import stats

# Check normality per group
for group in df['group'].unique():
    data = df[df['group'] == group]['value']
    w, p = stats.shapiro(data)
    print(f"{group}: W = {w:.3f}, p = {p:.4f}")

# Check homogeneity of variance
print(pg.homoscedasticity(df, dv='value', group='group'))

# For repeated measures: Check sphericity
# Pingouin 0.7 supports one/two-way sphericity diagnostics; earlier interaction
# corrections had bugs. Specify subject IDs and complete within-subject cells.
```

**What to do if sphericity violated** (repeated measures):
- Prespecify a correction such as Greenhouse-Geisser; Pingouin rm_anova reports GG.
- Do not infer Huynh-Feldt is automatically available from an epsilon threshold.
- Use multivariate approach (MANOVA)

---

### Linear Regression

**Assumptions**:
1. **Mean specification**: Conditional mean is linear in fitted coefficients (can include justified nonlinear predictor terms)
2. **Independence**: Residuals are independent
3. **Homoscedasticity**: Constant variance of residuals
4. **Normality**: Normal errors for exact small-sample conventional inference; fitted residuals are correlated projections, so residual Shapiro is only a screen
5. **Identifiability**: Full-rank design; high collinearity affects precision but is not by itself bias
6. **Exogeneity**: The conditional error mean is zero; residual plots do not establish causal identification

**Diagnostic workflow**:

**1. Linearity**:
```python
import matplotlib.pyplot as plt
import seaborn as sns

# Scatter plots of Y vs each X
# Residuals vs. fitted values (should be randomly scattered)
plt.scatter(fitted_values, residuals)
plt.axhline(y=0, color='r', linestyle='--')
```

**2. Independence**:
```python
from statsmodels.stats.stattools import durbin_watson

# Durbin-Watson test (for time series)
dw_statistic = durbin_watson(residuals)
# Meaningful row order is required; no universal 1.5-2.5 acceptance interval.
# This statistic cannot establish independence, particularly for clustered data.
```

**3. Homoscedasticity**:
```python
# Breusch-Pagan test
# Note: exog must include the constant column (e.g. sm.add_constant(X))
from statsmodels.stats.diagnostic import het_breuschpagan
_, p_value, _, _ = het_breuschpagan(residuals, exog)

# Visual: Scale-location plot
plt.scatter(fitted_values, np.sqrt(np.abs(std_residuals)))
```

**4. Normality of residuals**:
```python
# Q-Q plot of residuals
stats.probplot(residuals, dist="norm", plot=plt)

# Shapiro-Wilk test
stats.shapiro(residuals)
```

**5. Multicollinearity**:
```python
from statsmodels.stats.outliers_influence import variance_inflation_factor

# Calculate VIF for each predictor
vif_data = pd.DataFrame()
vif_data["feature"] = X.columns
vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(len(X.columns))]

# VIF > 10 indicates severe multicollinearity
# VIF > 5 indicates moderate multicollinearity
```

**What to do if violated**:
- **Non-linearity**: Add polynomial terms, use GAM, or transform variables
- **Heteroscedasticity**: Transform Y, use WLS, use robust SE
- **Non-normal residuals**: Transform Y, use robust methods, check for outliers
- **Multicollinearity**: Examine precision and identification; dropping confounders can bias estimates. Regularization changes inference and must match the purpose.

---

### Logistic Regression

**Assumptions**:
1. **Independence**: Observations are independent
2. **Linearity**: Linear relationship between log-odds and continuous predictors
3. **No perfect multicollinearity**: Predictors not perfectly correlated
4. **Information and identification**: Adequate events/non-events for parameters, effect sizes and precision; check separation and convergence. No fixed events-per-variable ratio guarantees valid inference.

**Diagnostic workflow**:

**1. Linearity of logit**:
```python
# Box-Tidwell test: Add interaction with log of continuous predictor
# If interaction is significant, linearity violated
```

**2. Multicollinearity**:
```python
# Use VIF as in linear regression
```

**3. Influential observations**:
```python
# Cook's distance, DFBetas, leverage (statsmodels >= 0.10)
# Do NOT use OLSInfluence on Logit/GLM results; use get_influence(),
# which returns MLEInfluence (Logit) or GLMInfluence (GLM)
influence = model.get_influence()
cooks_d, cooks_p = influence.cooks_distance  # tuple: (distances, approximate p-values)
# Outside Gaussian linear models these F-based p-values are approximate.
```

**4. Model fit / calibration**:
```python
# Calibration curve: compare predicted probabilities to observed event rates
# (e.g. sklearn.calibration.calibration_curve), plus the Brier score
# Pseudo R-squared
# Classification metrics (accuracy, AUC-ROC)
# Note: the Hosmer-Lemeshow test is not implemented in scipy/statsmodels
# and is sensitive to the choice of bins; prefer calibration curves
```

---

## Outlier Detection

**Methods**:
1. **Visual**: Box plots, scatter plots
2. **Statistical**:
   - Z-scores: |z| > 3 suggests outlier
   - IQR method: Values < Q1 - 1.5×IQR or > Q3 + 1.5×IQR
   - Modified Z-score using median absolute deviation (robust to outliers)

**For regression**:
- **Leverage**: High leverage points (hat values)
- **Influence**: Cook's distance > 4/n suggests influential point
- **Outliers**: Studentized residuals > ±3

**What to do**:
1. Investigate data entry errors
2. Consider if outliers are valid observations
3. Report sensitivity analysis (results with and without outliers)
4. Use robust methods if outliers are legitimate

---

## Sample Size Considerations

### Design-specific planning

Plan using the target effect or desired interval width, variance, prevalence, number of fitted parameters, clustering and attrition. Generic n=30/n=50 or events-per-variable thresholds do not establish power, robustness or model reliability. Simulate the actual planned estimator/design when closed-form assumptions do not apply.

### Small Sample Considerations

For small samples:
- Assumptions become more critical
- Use exact tests when available (Fisher's exact, exact logistic regression)
- Consider non-parametric alternatives
- Use permutation tests or bootstrap methods
- Be conservative with interpretation

---

## Reporting Assumption Checks

When reporting analyses, include:

1. **Statement of assumptions checked**: List all assumptions tested
2. **Methods used**: Describe visual and formal tests employed
3. **Results of diagnostic tests**: Report test statistics and p-values
4. **Assessment**: State evidence of departures and limits of the screens; never equate non-rejection with verified assumptions
5. **Actions taken**: If violated, describe remedial actions (transformations, alternative tests, robust methods)

**Example reporting statement**:
> "Normality was assessed using Shapiro-Wilk tests and Q-Q plots. Data for Group A (W = 0.97, p = .18) and Group B (W = 0.96, p = .12) showed no significant departure from normality. Homogeneity of variance was assessed using Levene's test, which was non-significant (F(1, 58) = 1.23, p = .27), providing no detected departure from equal variances at this sample size. Non-rejection does not verify equality; the prespecified Welch test and design review were retained."

## Current API sources

Reviewed 2026-10-01: [SciPy Shapiro](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.shapiro.html) requires at least three observations and warns that n>5000 p-values may be inaccurate; [Levene](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.levene.html) defaults to median centering. [statsmodels Breusch-Pagan](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.het_breuschpagan.html) defaults to the Koenker variant (`robust=True`), needs an intercept, and also returns the finite-sample F variant; report which one is used. [Durbin-Watson](https://www.statsmodels.org/stable/generated/statsmodels.stats.stattools.durbin_watson.html) is a statistic of adjacent residuals, not an independence certificate.
