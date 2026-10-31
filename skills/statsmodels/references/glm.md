# Generalized Linear Models (GLM) Reference

This document provides comprehensive guidance on generalized linear models in statsmodels, including families, link functions, and applications.

## Overview

GLMs extend linear regression to non-normal response distributions through:
1. **Distribution family**: Specifies the conditional distribution of the response
2. **Link function**: Maps the conditional mean to the linear predictor; the inverse link maps back
3. **Variance function**: Relates variance to the mean

**General form**: g(μ) = Xβ, where g is the link function and μ = E(Y|X)

## When to Use GLM

- **Binary outcomes**: Logistic regression (Binomial family with logit link)
- **Count data**: Poisson or Negative Binomial regression
- **Positive continuous data**: Gamma or Inverse Gaussian
- **Conditional mean/variance structure**: Choose family from the response mechanism, not a normality test on the marginal response
- **Link functions**: Need non-linear relationship between predictors and response scale

Formula predictions take raw named columns; array predictions take the exact training design. Do not reuse a result from a different family in a later fragment. Use positive finite exposure, pass `exposure=e` or `offset=np.log(e)` (not both), and supply new exposure/offset when predicting new rows. Binomial proportions need trial counts (`var_weights=n`) or a two-column `[successes, failures]` response; arbitrary proportions are not Bernoulli observations.

## Distribution Families

### Binomial Family

For binary outcomes (0/1) or proportions (k/n).

**When to use:**
- Binary classification
- Success/failure outcomes
- Proportions or rates

**Common links:**
- Logit (default): log(μ/(1-μ))
- Probit: Φ⁻¹(μ)
- Log: log(μ)

```python
import statsmodels.api as sm
import statsmodels.formula.api as smf

# Binary logistic regression
model = sm.GLM(y, X, family=sm.families.Binomial())
results = model.fit()

# Formula API
results = smf.glm('success ~ x1 + x2', data=df,
                  family=sm.families.Binomial()).fit()

# Access predictions (probabilities)
probs = results.predict(new_df)  # Raw named predictors after a formula fit

# Classification (0.5 threshold)
predictions = (probs > 0.5).astype(int)
```

**Interpretation:**
```python
import numpy as np

# Odds ratios (for logit link)
odds_ratios = np.exp(results.params)
print("Odds ratios:", odds_ratios)

# For 1-unit increase in x, odds multiply by exp(beta)
```

### Poisson Family

For count data (non-negative integers).

**When to use:**
- Count outcomes (number of events)
- Rare events
- Rate modeling (with offset)

**Common links:**
- Log (default): log(μ)
- Identity: μ
- Sqrt: √μ

```python
# Poisson regression
model = sm.GLM(y, X, family=sm.families.Poisson())
results = model.fit()

# With exposure/offset for rates
# If modeling rate = counts/exposure
model = sm.GLM(y, X, family=sm.families.Poisson(),
               offset=np.log(exposure))
results = model.fit()

# Interpretation: exp(beta) = multiplicative effect on expected count
import numpy as np
rate_ratios = np.exp(results.params)
print("Rate ratios:", rate_ratios)
```

**Overdispersion check:**
```python
# Pearson dispersion is a screening statistic, not a calibrated universal test
overdispersion = results.pearson_chi2 / results.df_resid
print(f"Overdispersion: {overdispersion}")

# If >> 1, consider Negative Binomial
if overdispersion > 1.5:
    print("Consider Negative Binomial model for overdispersion")
```

### Negative Binomial Family

For overdispersed count data.

**When to use:**
- Count data with variance > mean
- Excess zeros or large variance
- Poisson model shows overdispersion

```python
# Negative Binomial GLM with fixed alpha
model = sm.GLM(y, X, family=sm.families.NegativeBinomial(alpha=1.0))
results = model.fit()

# Use the discrete count model when alpha should be estimated
from statsmodels.discrete.discrete_model import NegativeBinomial
nb_model = NegativeBinomial(y, X)
nb_results = nb_model.fit()

print(f"Dispersion parameter alpha: {np.asarray(nb_results.params)[-1]}")
```

### Gaussian Family

Equivalent to OLS but fit via IRLS (Iteratively Reweighted Least Squares).

**When to use:**
- Want GLM framework for consistency
- Need robust standard errors
- Comparing with other GLMs

**Common links:**
- Identity (default): μ
- Log: log(μ)
- Inverse: 1/μ

```python
# Gaussian GLM (equivalent to OLS)
model = sm.GLM(y, X, family=sm.families.Gaussian())
results = model.fit()

# Verify equivalence with OLS
ols_results = sm.OLS(y, X).fit()
print("Parameters close:", np.allclose(results.params, ols_results.params))
```

### Gamma Family

For positive continuous data, often right-skewed.

**When to use:**
- Positive outcomes (insurance claims, survival times)
- Right-skewed distributions
- Variance proportional to mean²

**Common links:**
- Inverse (default): 1/μ
- Log: log(μ)
- Identity: μ

```python
# Gamma regression (common for cost data)
model = sm.GLM(y, X, family=sm.families.Gamma())
results = model.fit()

# Log link often preferred for interpretation
model = sm.GLM(y, X, family=sm.families.Gamma(link=sm.families.links.Log()))
results = model.fit()

# With log link, exp(beta) = multiplicative effect
import numpy as np
effects = np.exp(results.params)
```

### Inverse Gaussian Family

For positive continuous data with specific variance structure.

**When to use:**
- Positive skewed outcomes
- Variance proportional to mean³
- Alternative to Gamma

**Common links:**
- Inverse squared (default): 1/μ²
- Log: log(μ)

```python
model = sm.GLM(y, X, family=sm.families.InverseGaussian())
results = model.fit()
```

### Tweedie Family

Flexible family covering multiple distributions.

**When to use:**
- Insurance claims (mixture of zeros and continuous)
- Semi-continuous data
- Need flexible variance function

**Special cases (power parameter p):**
- p=0: Normal
- p=1: Poisson
- p=2: Gamma
- p=3: Inverse Gaussian
- 1<p<2: Compound Poisson-Gamma (common for insurance)

```python
# Tweedie with power=1.5
model = sm.GLM(y, X, family=sm.families.Tweedie(link=sm.families.links.Log(),
                                                 var_power=1.5))
results = model.fit()
```

## Link Functions

Link functions connect the linear predictor to the mean of the response.

### Available Links

```python
from statsmodels.genmod import families

# Identity: g(μ) = μ
link = families.links.Identity()

# Log: g(μ) = log(μ)
link = families.links.Log()

# Logit: g(μ) = log(μ/(1-μ))
link = families.links.Logit()

# Probit: g(μ) = Φ⁻¹(μ)
link = families.links.Probit()

# Complementary log-log: g(μ) = log(-log(1-μ))
link = families.links.CLogLog()

# Inverse: g(μ) = 1/μ
link = families.links.InversePower()

# Inverse squared: g(μ) = 1/μ²
link = families.links.InverseSquared()

# Square root: g(μ) = √μ
link = families.links.Sqrt()

# Power: g(μ) = μ^p
link = families.links.Power(power=2)
```

### Choosing Link Functions

**Common default links** (canonical up to conventional scaling for these families):
- Binomial → Logit
- Poisson → Log
- Gamma → Inverse
- Gaussian → Identity
- Inverse Gaussian → Inverse squared

The default Gamma inverse link and binomial log/identity links may violate their response domains for some designs. Inspect warnings, finite fitted means and support; a converged optimizer does not make an invalid mean valid. Use a positive-mean link when appropriate.

**When to use non-canonical:**
- **Log link with Binomial**: Risk ratios instead of odds ratios
- **Identity link**: Direct additive effects (when sensible)
- **Probit vs Logit**: Similar results, preference based on field
- **CLogLog**: Asymmetric relationship, common in survival analysis

```python
# Example: Risk ratios with log-binomial model
model = sm.GLM(y, X, family=sm.families.Binomial(link=sm.families.links.Log()))
results = model.fit()

# exp(beta) now gives risk ratios, not odds ratios
risk_ratios = np.exp(results.params)
```

## Model Fitting and Results

### Basic Workflow

```python
import statsmodels.api as sm

# Add constant
X = sm.add_constant(X_data)

# Specify family and link
family = sm.families.Poisson(link=sm.families.links.Log())

# Fit model using IRLS
model = sm.GLM(y, X, family=family)
results = model.fit()

# Summary
print(results.summary())
```

### Results Attributes

```python
# Parameters and inference
results.params              # Coefficients
results.bse                 # Standard errors
results.tvalues            # Z-statistics
results.pvalues            # P-values
results.conf_int()         # Confidence intervals

# Predictions
results.fittedvalues       # Fitted values (μ)
results.predict(X_new)     # Predictions for new data

# Model fit statistics
results.aic                # Akaike Information Criterion
results.bic_llf            # Likelihood-based BIC (GLM .bic can be deviance-based)
results.deviance           # Deviance
results.null_deviance      # Null model deviance
results.pearson_chi2       # Pearson chi-squared statistic
results.df_resid           # Residual degrees of freedom
results.llf                # Log-likelihood

# Residuals
results.resid_response     # Response residuals (y - μ)
results.resid_pearson      # Pearson residuals
results.resid_deviance     # Deviance residuals
results.resid_anscombe     # Anscombe residuals
results.resid_working      # Working residuals
```

### Pseudo R-squared

```python
# Likelihood-based McFadden measure: appropriate for discrete outcomes
pseudo_r2 = results.pseudo_rsquared(kind="mcf")
print(f"McFadden pseudo R²: {pseudo_r2:.4f}")
# Cox-Snell is available for discrete or continuous likelihoods
print("Cox-Snell:", results.pseudo_rsquared(kind="cs"))
# 1 - deviance/null_deviance is a different measure; do not label it McFadden.
```

## Diagnostics

### Goodness of Fit

```python
# Chi-square goodness-of-fit approximations need adequate expected cell counts;
# these are not generally calibrated for sparse counts or ungrouped Bernoulli data
from scipy import stats

deviance_pval = stats.chi2.sf(results.deviance, results.df_resid)
print(f"Deviance test p-value: {deviance_pval}")

# Pearson chi-squared test
pearson_pval = stats.chi2.sf(results.pearson_chi2, results.df_resid)
print(f"Pearson chi² test p-value: {pearson_pval}")

# Check for overdispersion/underdispersion
dispersion = results.pearson_chi2 / results.df_resid
print(f"Dispersion: {dispersion}")
# For a Poisson model with an adequate mean, >1 flags extra-Poisson dispersion.
# Gaussian/Gamma/InverseGaussian estimate scale; this ratio need not be 1.
```

### Residual Analysis

```python
import matplotlib.pyplot as plt

# Deviance residuals vs fitted
plt.figure(figsize=(10, 6))
plt.scatter(results.fittedvalues, results.resid_deviance, alpha=0.5)
plt.xlabel('Fitted values')
plt.ylabel('Deviance residuals')
plt.axhline(y=0, color='r', linestyle='--')
plt.title('Deviance Residuals vs Fitted')
plt.show()

# Q-Q plot of deviance residuals
from statsmodels.graphics.gofplots import qqplot
qqplot(results.resid_deviance, line='s')
plt.title('Q-Q Plot of Deviance Residuals')
plt.show()

# For binary outcomes: binned residual plot
if isinstance(results.model.family, sm.families.Binomial):
    from statsmodels.graphics.gofplots import qqplot
    # Group predictions and compute average residuals
    # (custom implementation needed)
    pass
```

### Influence and Outliers

```python
from statsmodels.stats.outliers_influence import GLMInfluence

influence = results.get_influence()  # Supplies the GLM-specific leverage and scale

# Leverage
leverage = influence.hat_matrix_diag

# Cook's distance
cooks_d = influence.cooks_distance[0]

# Standardized approximate change in fitted means (not OLS DFFITS)
d_fitted_scaled = influence.d_fittedvalues_scaled

# Find influential observations
influential = np.where(cooks_d > 4/len(y))[0]
print(f"Influential observations: {influential}")
```

## Hypothesis Testing

```python
# Wald test for single parameter (automatically in summary)

# Likelihood ratio test for nested models
# Fit reduced model
model_reduced = sm.GLM(y, X_reduced, family=family).fit()
model_full = sm.GLM(y, X_full, family=family).fit()

# LR statistic
lr_stat = 2 * (model_full.llf - model_reduced.llf)
df_diff = model_full.df_model - model_reduced.df_model

from scipy import stats
lr_pval = stats.chi2.sf(lr_stat, df_diff)
print(f"LR test p-value: {lr_pval}")

# Wald test for multiple parameters
# Test beta_1 = beta_2 = 0
R = [[0, 1, 0, 0], [0, 0, 1, 0]]
wald_test = results.wald_test(R)
print(wald_test)
```

## Robust Standard Errors

```python
# Heteroscedasticity-robust (sandwich estimator)
results_robust = results.model.fit(cov_type='HC0')

# Cluster-robust
results_cluster = results.model.fit(cov_type='cluster',
                                    cov_kwds={'groups': cluster_ids})

# Compare standard errors
print("Regular SE:", results.bse)
print("Robust SE:", results_robust.bse)
```

Robust covariance addresses the variance calculation under its asymptotic assumptions. It does not repair separation, an incorrect mean model, few independent clusters, or endogeneity. GLM influence approximations are experimental, especially with exposure/offset.

## Model Comparison

```python
# AIC/BIC for non-nested models
models = [model1_results, model2_results, model3_results]
for i, res in enumerate(models, 1):
    print(f"Model {i}: AIC={res.aic:.2f}, BIC={res.bic_llf:.2f}")

# Likelihood ratio test for nested models (as shown above)

# Cross-validation for predictive performance
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import log_loss

# Binary independent observations only; X already includes the intercept.
X_array, y_array = np.asarray(X), np.asarray(y)
family = sm.families.Binomial()
kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = []

for train_idx, val_idx in kf.split(X_array, y_array):
    X_train, X_val = X_array[train_idx], X_array[val_idx]
    y_train, y_val = y_array[train_idx], y_array[val_idx]

    model_cv = sm.GLM(y_train, X_train, family=family).fit()
    pred_probs = model_cv.predict(X_val)

    score = log_loss(y_val, pred_probs)
    cv_scores.append(score)

print(f"CV Log Loss: {np.mean(cv_scores):.4f} ± {np.std(cv_scores):.4f}")
```

## Prediction

```python
# Point predictions
predictions = results.predict(X_new)

# For classification: get probabilities and convert
if isinstance(family, sm.families.Binomial):
    probs = predictions
    class_predictions = (probs > 0.5).astype(int)

# For counts: predictions are expected counts
if isinstance(family, sm.families.Poisson):
    expected_counts = predictions

# Conditional mean confidence intervals, not intervals for a new observation
mean_prediction = results.get_prediction(X_new, which="mean")
mean_ci = mean_prediction.conf_int(alpha=0.05)
mean_table = mean_prediction.summary_frame()
# A bootstrap of fitted means alone also omits future outcome noise.
# Outcome prediction intervals need the fitted family/scale plus parameter uncertainty.
```

## Common Applications

### Logistic Regression (Binary Classification)

```python
import statsmodels.api as sm

# Fit logistic regression
X = sm.add_constant(X_data)
model = sm.GLM(y, X, family=sm.families.Binomial())
results = model.fit()

# Odds ratios
odds_ratios = np.exp(results.params)
odds_ci = np.exp(results.conf_int())

# Classification metrics
from sklearn.metrics import classification_report, roc_auc_score

probs = results.predict(X)
predictions = (probs > 0.5).astype(int)

print(classification_report(y, predictions))
print(f"AUC: {roc_auc_score(y, probs):.4f}")

# ROC curve
from sklearn.metrics import roc_curve
import matplotlib.pyplot as plt

fpr, tpr, thresholds = roc_curve(y, probs)
plt.plot(fpr, tpr)
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve')
plt.show()
```

### Poisson Regression (Count Data)

```python
# Fit Poisson model
X = sm.add_constant(X_data)
model = sm.GLM(y_counts, X, family=sm.families.Poisson())
results = model.fit()

# Rate ratios
rate_ratios = np.exp(results.params)
print("Rate ratios:", rate_ratios)

# Check overdispersion
dispersion = results.pearson_chi2 / results.df_resid
if dispersion > 1.5:
    print(f"Elevated Pearson dispersion ({dispersion:.2f}); investigate mean, dependence and count family.")
```

### Gamma Regression (Cost/Duration Data)

```python
# Fit Gamma model with log link
X = sm.add_constant(X_data)
model = sm.GLM(y_cost, X,
               family=sm.families.Gamma(link=sm.families.links.Log()))
results = model.fit()

# Multiplicative effects
effects = np.exp(results.params)
print("Multiplicative effects on mean:", effects)
```

## Best Practices

1. **Check conditional assumptions**: Examine response support, mean structure, exposure and residual patterns; marginal response normality does not choose a GLM
2. **Verify link function**: Use canonical links unless there's a reason not to
3. **Examine residuals**: Discrete deviance residuals need not be normal; evaluate calibration and simulation-based diagnostics appropriate to the family
4. **Test for overdispersion**: Especially for Poisson models
5. **Use offsets appropriately**: For rate modeling with varying exposure
6. **Consider robust SEs**: When variance assumptions questionable
7. **Compare models**: Use AIC/BIC for non-nested, LR test for nested
8. **Interpret on original scale**: Transform coefficients (e.g., exp for log link)
9. **Check influential observations**: Use Cook's distance
10. **Validate predictions**: Use cross-validation or holdout set

## Common Pitfalls

1. **Forgetting to add constant**: No intercept term
2. **Using wrong family**: Check distribution of response
3. **Ignoring overdispersion**: Use Negative Binomial instead of Poisson
4. **Misinterpreting coefficients**: Remember link function transformation
5. **Not checking convergence**: IRLS may not converge; check warnings
6. **Complete separation in logistic**: Some categories perfectly predict outcome
7. **Using identity link with bounded outcomes**: May predict outside valid range
8. **Comparing models with different samples**: Use same observations
9. **Forgetting offset in rate models**: Must use log(exposure) as offset
10. **Not considering alternatives**: Mixed models, zero-inflation for complex data
