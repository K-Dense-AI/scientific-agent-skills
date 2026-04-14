# Parameter Recovery Diagnostic Visualizations and Templates

This reference provides templates and guidance for the key diagnostic visualizations in a parameter recovery study.

---

## 1. Scatter Plot: Recovered vs. True Parameters

### Purpose

The most fundamental recovery diagnostic. Each point represents one simulated dataset. The x-axis shows the ground-truth parameter value; the y-axis shows the recovered (fitted) value.

### What to Plot

- One scatter plot per free parameter
- Include the identity line (y = x; dashed) for reference
- Include a regression line with confidence band
- Report Pearson r, bias (mean deviation from identity), and RMSE in the plot annotation

### Interpretation Guide

| Pattern | Interpretation |
|---------|---------------|
| Points cluster tightly along identity line | Excellent recovery |
| Points along identity line but with spread | Acceptable recovery; noise from limited data |
| Slope < 1 (regression toward mean) | Shrinkage bias; extreme values are underestimated |
| Slope > 1 | Overshoot; extreme values are overestimated |
| Systematic offset from identity | Constant bias; recovered = true + constant |
| Scatter with no clear relationship | Poor recovery; parameter is non-identifiable |
| Fan shape (variance increases with value) | Heteroscedastic recovery; precision depends on true value |

### Example Code (Python)

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

def plot_recovery(true_vals, recovered_vals, param_name, ax=None):
 """Plot parameter recovery scatter with diagnostics."""
 if ax is None:
 fig, ax = plt.subplots(1, 1, figsize=(6, 6))

 ax.scatter(true_vals, recovered_vals, alpha=0.3, s=20)

 # Identity line
 lims = [min(true_vals.min(), recovered_vals.min()),
 max(true_vals.max(), recovered_vals.max())]
 ax.plot(lims, lims, 'k--', alpha=0.5, label='Identity')

 # Regression line
 slope, intercept, r, p, se = stats.linregress(true_vals, recovered_vals)
 x_fit = np.linspace(lims[0], lims[1], 100)
 ax.plot(x_fit, slope * x_fit + intercept, 'r-', label=f'Fit (r={r:.3f})')

 # Metrics
 bias = np.mean(recovered_vals - true_vals)
 rmse = np.sqrt(np.mean((recovered_vals - true_vals)**2))

 ax.set_xlabel(f'True {param_name}')
 ax.set_ylabel(f'Recovered {param_name}')
 ax.set_title(f'{param_name}: r={r:.3f}, bias={bias:.3f}, RMSE={rmse:.3f}')
 ax.legend()
 ax.set_aspect('equal')
 return ax
```

---

## 2. Bland-Altman Plot (Difference vs. Mean)

### Purpose

Detects range-dependent bias that scatter plots can miss. Shows whether recovery quality varies across the parameter range.

### What to Plot

- X-axis: mean of true and recovered values: (true + recovered) / 2
- Y-axis: difference: recovered - true
- Horizontal line at y = 0 (no bias)
- Horizontal lines at mean difference +/- 1.96 * SD (limits of agreement)

### Interpretation Guide

| Pattern | Interpretation |
|---------|---------------|
| Points scattered evenly around 0 | Unbiased recovery |
| Points above 0 | Systematic overestimation |
| Points below 0 | Systematic underestimation |
| Funnel shape (spread increases with mean) | Proportional bias; consider log-transforming |
| Trend in difference vs. mean | Range-dependent bias; recovery worse at extremes |

---

## 3. Cross-Parameter Correlation Matrix

### Purpose

Identifies parameter tradeoffs that compromise individual parameter interpretation even when marginal recovery is good.

### What to Plot

- Compute correlations between ALL pairs of recovered parameters
- Display as a heatmap with correlation coefficients annotated
- Flag correlations |r| > 0.5 as potential tradeoffs (Wilson & Collins, 2019)

### Interpretation Guide

| Correlation | Interpretation | Action |
|-------------|---------------|--------|
| |r| < 0.3 | Independent parameters | No concern |
| 0.3 < |r| < 0.5 | Mild tradeoff | Monitor; may not affect conclusions |
| |r| > 0.5 | Substantial tradeoff | Consider fixing one parameter or reparameterizing |
| |r| > 0.7 | Severe tradeoff | Parameters are likely non-identifiable together |

### Common Tradeoff Pairs

| Model | Parameters | Expected r | Source |
|-------|-----------|------------|--------|
| DDM | v and a | Positive; r ~ 0.3-0.6 | Ratcliff & Tuerlinckx, 2002 |
| DDM | a and Ter | Negative; r ~ -0.2 to -0.5 | Ratcliff & Tuerlinckx, 2002 |
| RL | alpha and beta | Negative; r ~ -0.3 to -0.7 | Daw, 2011 |
| ACT-R | s and tau | Negative; both affect retrieval probability | Anderson, 2007 |

---

## 4. Model Recovery Confusion Matrix

### Purpose

Determines whether competing models can be distinguished given your experimental design.

### What to Plot

- K x K matrix where K = number of candidate models
- Rows = generating model (true model)
- Columns = selected model (best-fitting model)
- Cell values = proportion of simulations where the column model was selected
- Color-code by proportion (darker = higher)
- Diagonal should be dominant (> 90% correct; Wagenmakers et al., 2004)

### Interpretation Guide

| Pattern | Interpretation |
|---------|---------------|
| Strong diagonal (> 90%) | Models are distinguishable |
| Off-diagonal > 20% for a pair | Those models are confusable; cannot be distinguished |
| One model dominates all rows | That model is too flexible (overfits); penalize complexity |
| Symmetric confusion | Models are genuinely similar in predictions |
| Asymmetric confusion | One model nests the other or has a complexity advantage |

---

## 5. Recovery as a Function of Sample Size

### Purpose

Determines the minimum number of trials needed for reliable parameter estimation.

### What to Plot

- X-axis: number of trials per simulated participant (e.g., 25, 50, 100, 200, 500)
- Y-axis: recovery metric (r, RMSE, or bias)
- One line per parameter
- Include horizontal reference line at r = 0.9 (good recovery threshold) or r = 0.8 (acceptable)

### Typical Sample Size Guidance

| Model Type | Minimum Trials | Source |
|------------|----------------|--------|
| DDM (3 parameters) | **100** trials per condition | Ratcliff & Tuerlinckx, 2002 |
| DDM (full, 7 parameters) | **200+** trials per condition | Ratcliff & Tuerlinckx, 2002 |
| Reinforcement learning (2 params) | **50-100** trials | Wilson & Collins, 2019 |
| ACT-R (3-5 parameters) | **100-200** trials | Heathcote et al., 2015 |

---

## 6. Objective Function Landscape

### Purpose

Visualizes the shape of the fitting objective around the true parameter values. Reveals flat regions, multiple minima, and ridges.

### 1D Landscape

- Fix all parameters at true values except one
- Vary the target parameter across its range
- Plot negative log-likelihood (or other objective) vs. parameter value
- The minimum should be near the true value with a clear, sharp valley

### 2D Landscape

- Fix all parameters except two
- Evaluate objective on a grid over the two parameters
- Plot as contour or heatmap
- Look for: single minimum (good), ridge/valley (tradeoff), multiple minima (non-convex)

---

## References

- Anderson, J. R. (2007). *How Can the Human Mind Occur in the Physical Universe?* Oxford University Press.
- Daw, N. D. (2011). Trial-by-trial data analysis using computational models. In *Decision Making, Affect, and Learning*. Oxford University Press.
- Heathcote, A., Brown, S. D., & Wagenmakers, E.-J. (2015). An introduction to good practices in cognitive modeling. Springer.
- Ratcliff, R., & Tuerlinckx, F. (2002). Estimating parameters of the diffusion model. *Psychonomic Bulletin & Review*, 9(3), 438-481.
- Wagenmakers, E.-J., et al. (2004). Assessing model mimicry using the parametric bootstrap. *Journal of Mathematical Psychology*, 48(1), 28-50.
- Wilson, R. C., & Collins, A. G. (2019). Ten simple rules for the computational modeling of behavioral data. *eLife*, 8, e49547.
