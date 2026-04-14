# MCMC Diagnostics and Model Checking Checklist

This reference provides a step-by-step diagnostic protocol for Bayesian cognitive models fitted with MCMC (Stan/PyMC). Every threshold is cited. Follow this checklist in order before reporting any posterior results.

---

## Phase 1: Pre-Fitting Checks

### 1.1 Prior Predictive Check

Before fitting the model to data, verify that the priors produce plausible simulated data.

- [ ] Sample 500-1000 parameter sets from the prior distributions
- [ ] Simulate datasets from the generative model using each parameter set
- [ ] Verify simulated data falls within the plausible range for the domain
- [ ] Document the prior predictive check results

See `prior-selection-guide.md` for the full prior predictive checking procedure and domain-specific plausibility criteria.

### 1.2 Computational Setup

- [ ] Run a minimum of **4 chains** (Vehtari et al., 2021)
- [ ] Set warmup/burn-in to at least **1000 iterations** per chain (Stan default; adjust upward for complex models)
- [ ] Set sampling iterations to at least **1000 per chain** (total post-warmup draws >= 4000)
- [ ] For Stan: set `adapt_delta` to at least **0.8** (default); increase to **0.95-0.99** if divergent transitions occur (Stan Reference Manual)
- [ ] For Stan: set `max_treedepth` to **10** (default); increase to **12-15** if tree depth saturation warnings appear
- [ ] Record software version, random seed, and all sampler settings for reproducibility

---

## Phase 2: Convergence Diagnostics

Run these checks on every parameter in the model, including derived quantities and hyperparameters. A single failing parameter means the model has not converged.

### 2.1 R-hat (Split R-hat, Rank-Normalized)

**Threshold: R-hat < 1.01 for all parameters** (Vehtari et al., 2021)

| R-hat Value | Interpretation | Action |
|-------------|---------------|--------|
| < 1.01 | Chains have converged | Proceed |
| 1.01 - 1.05 | Possible convergence issue | Investigate; run longer chains; check trace plots |
| 1.05 - 1.1 | Likely convergence failure | Do not report results; diagnose the problem |
| > 1.1 | Definite convergence failure | Do not report results; model needs reparameterization or longer run |

**What R-hat measures**: The ratio of between-chain variance to within-chain variance after splitting each chain in half. The improved rank-normalized version (Vehtari et al., 2021) also detects problems in the tails of the distribution that traditional R-hat misses.

**Common causes of high R-hat**:
- Insufficient warmup/sampling iterations
- Multimodality in the posterior (multiple modes that chains get stuck in)
- Label switching in mixture models
- Near-non-identifiability creating ridges in the posterior
- Poor initial values causing chains to explore different regions

**Fixes**:
1. Run longer chains (double iterations)
2. Check for multimodality via trace plots
3. For mixture models, impose ordering constraints to prevent label switching (e.g., mu_1 < mu_2) (Stephens, 2000)
4. Reparameterize: switch centered to non-centered (or vice versa)
5. Use more informative priors to reduce posterior ambiguity

### 2.2 Effective Sample Size (ESS)

**Threshold: Bulk-ESS > 400 AND Tail-ESS > 400** (Vehtari et al., 2021)

The 400 threshold assumes 4 chains (approximately 100 effective samples per chain).

| ESS Type | What It Measures | Minimum | Source |
|----------|-----------------|---------|--------|
| **Bulk-ESS** | Effective samples for estimating the posterior mean/median (center of distribution) | **> 400** | Vehtari et al., 2021 |
| **Tail-ESS** | Effective samples for estimating tail quantiles (credible interval endpoints) | **> 400** | Vehtari et al., 2021 |

**Why two ESS measures?** A chain can mix well in the bulk of the distribution but poorly in the tails, or vice versa. Reporting only one ESS can mask problems with credible interval estimation. Tail-ESS is the minimum of the ESS for the 5th and 95th percentile quantiles (Vehtari et al., 2021).

**ESS vs. total draws ratio**: If ESS/total_draws < 0.1, there is substantial autocorrelation. This is not necessarily a problem if absolute ESS exceeds 400, but very low ratios (< 0.01) suggest the sampler is struggling.

**Common causes of low ESS**:
- High autocorrelation from poor parameterization (centered hierarchical when non-centered is needed)
- Near-non-identifiability creating slow exploration
- Multimodality causing chains to remain in modes for extended periods
- Step size too large or too small (diagnosed via tree depth)

**Fixes**:
1. Reparameterize (non-centered parameterization for hierarchical models)
2. Run more iterations
3. Thin chains as a last resort (increases ESS per stored sample but wastes computation)
4. For Stan: check that `adapt_delta` is not too high (> 0.99 slows down sampling without benefit for well-specified models)

### 2.3 Divergent Transitions

**Threshold: 0 divergent transitions** (Betancourt, 2017)

- [ ] Check for divergent transitions in sampler output
- [ ] If any divergences occurred, do NOT trust the posterior

**What divergent transitions mean**: The Hamiltonian Monte Carlo sampler encountered regions of the posterior with very high curvature that it could not faithfully traverse. This means the posterior samples may not represent the true posterior distribution (Betancourt, 2017).

| Number of Divergences | Interpretation | Action |
|-----------------------|---------------|--------|
| 0 | No detected geometry problems | Proceed |
| 1-10 | Mild geometry issue; posterior may be biased in problematic region | Investigate; try remediation |
| 10-100 | Serious geometry problem | Do not trust results; must fix |
| > 100 | Severe model/parameterization problem | Rethink model specification |

**Common causes**:
- **Funnel geometry** in centered hierarchical models (the most common cause in cognitive modeling)
- Highly correlated parameters creating narrow valleys
- Priors that conflict with the likelihood, creating sharp posterior ridges
- Boundaries or constraints creating discontinuities

**Fixes** (in order of preference):
1. **Non-centered parameterization**: Transform `theta_j ~ Normal(mu, sigma)` to `theta_j = mu + sigma * eta_j` where `eta_j ~ Normal(0, 1)` (Betancourt & Girolami, 2015)
2. **Increase adapt_delta**: Set to 0.95, then 0.99 if needed. This reduces the step size, allowing the sampler to navigate difficult geometry at the cost of slower sampling (Stan Reference Manual)
3. **Reparameterize correlated parameters**: Use Cholesky decompositions for multivariate priors; consider QR decomposition for regression predictors
4. **Tighten priors**: More informative priors can smooth posterior geometry
5. **Simplify the model**: If divergences persist after all fixes, the model may be too complex for the data

**Where divergences occur**: In Stan, you can extract which iterations diverged and plot the parameter values at those iterations. If divergences cluster in a specific region of parameter space (e.g., near sigma = 0 in a hierarchical model), this confirms the funnel geometry diagnosis.

### 2.4 Energy Diagnostics (E-BFMI)

**Threshold: E-BFMI > 0.3** (Betancourt, 2017)

The Energy Bayesian Fraction of Missing Information measures how well the HMC momentum can explore the posterior.

| E-BFMI Value | Interpretation | Action |
|--------------|---------------|--------|
| > 0.3 | Adequate exploration | Proceed |
| 0.2 - 0.3 | Marginal; may miss some posterior mass | Investigate; consider reparameterization |
| < 0.2 | Poor exploration; posterior may be biased | Reparameterize; increase adapt_delta |

**Common causes of low E-BFMI**:
- Heavy-tailed posterior that HMC cannot efficiently explore
- Posterior with very different scales across parameters
- Funnel geometry (often co-occurs with divergent transitions)

**Fix**: Reparameterize to make the posterior geometry more uniform; standardize parameter scales.

### 2.5 Tree Depth Saturation

**Threshold: < 1% of transitions hitting max_treedepth** (Stan Reference Manual)

When the NUTS sampler hits the maximum tree depth, it terminates the trajectory early, potentially reducing sampling efficiency.

- [ ] Check fraction of transitions that hit max_treedepth
- [ ] If > 1% saturate, increase max_treedepth by 2-3 (e.g., from 10 to 12 or 13)

**Note**: Tree depth saturation does not bias the posterior (unlike divergences), but it reduces ESS per unit time. The only cost of increasing max_treedepth is computational time (each additional depth level doubles the maximum number of leapfrog steps).

---

## Phase 3: Visual Diagnostics

Even when numerical diagnostics pass, visual inspection can reveal subtle problems.

### 3.1 Trace Plots

- [ ] All chains should be well-mixed (indistinguishable "fuzzy caterpillar" appearance)
- [ ] No chain should be stuck in a different region from others
- [ ] No long-term trends (drift) in any chain
- [ ] No periodic patterns (indicates strong autocorrelation)

**What to look for**:
- **Good mixing**: Chains overlap completely and look like noise
- **Poor mixing**: Chains show slow wandering, long excursions, or different levels
- **Label switching**: Chains periodically swap between two or more values (common in mixture models)
- **Stationarity violation**: Chain mean or variance changes over time

### 3.2 Rank Plots (Recommended)

- [ ] Generate rank histogram plots (available in ArviZ and bayesplot)
- [ ] Uniform rank histograms indicate good mixing across chains
- [ ] Non-uniform patterns indicate convergence problems

Rank plots are more informative than traditional trace plots for detecting subtle mixing problems (Vehtari et al., 2021).

### 3.3 Pairwise Posterior Scatter Plots

- [ ] Check for strong posterior correlations between parameters
- [ ] Look for banana-shaped or ridge-shaped posteriors (indicate non-identifiability)
- [ ] Verify that no parameter pair shows a perfect linear trade-off

**Typical problematic correlations in cognitive models**:
- DDM: drift rate (v) and boundary separation (a) often negatively correlated when few conditions constrain them
- RL: learning rate (alpha) and inverse temperature (beta) are classically collinear (Daw, 2011)
- SDT: d' and c can correlate when hit/false alarm rates approach boundaries

---

## Phase 4: Posterior Predictive Checks

After confirming convergence, verify that the model can reproduce the observed data.

### 4.1 Basic Posterior Predictive Protocol

1. **Draw S = 500-1000 samples** from the posterior distribution
2. **For each posterior sample, simulate a complete dataset** with the same structure as the observed data
3. **Compute summary statistics** on each simulated dataset (same statistics you would report for the real data)
4. **Compare simulated vs. observed statistics** using overlaid distributions or difference plots

### 4.2 Domain-Specific Posterior Predictive Checks

#### For Reaction Time Models (DDM, LBA, etc.)

- [ ] **Mean RT by condition**: Simulated mean RT should bracket observed mean RT
- [ ] **RT quantiles (0.1, 0.3, 0.5, 0.7, 0.9) by condition**: The full distributional shape must be captured, not just the mean (Ratcliff & McKoon, 2008)
- [ ] **Accuracy by condition**: Simulated accuracy should bracket observed accuracy
- [ ] **Conditional Accuracy Functions (CAFs)**: Accuracy as a function of RT quantile bin; captures speed-accuracy tradeoff dynamics
- [ ] **RT distribution shape**: Overlay posterior predictive density on observed RT histogram; check right tail fit
- [ ] **Error RT distribution**: Often neglected; error RTs should be faster or slower than correct RTs depending on the model (Ratcliff & McKoon, 2008)

#### For Learning Models (RL, etc.)

- [ ] **Learning curves**: Simulated performance over trial blocks should match observed learning trajectory
- [ ] **Choice proportions by block**: Should bracket observed choice frequencies
- [ ] **Win-stay / lose-shift rates**: Captures local choice dynamics that aggregate statistics miss (Wilson & Collins, 2019)
- [ ] **Individual differences**: Simulated between-participant variability should match observed variability

#### For Signal Detection Models

- [ ] **Hit rate and false alarm rate**: Should bracket observed rates
- [ ] **ROC curve shape** (if multiple criteria/confidence levels available): Simulated ROC should match observed ROC
- [ ] **z-ROC linearity**: If assuming equal variance, z-ROC should be linear with slope near 1; deviations suggest unequal variance model (Macmillan & Creelman, 2005)

#### For Multinomial Processing Tree Models

- [ ] **Category response frequencies**: Simulated response frequencies should bracket observed frequencies for each response category
- [ ] **Pearson chi-square or G-squared**: Posterior predictive p-value for model fit (Klauer, 2010)

### 4.3 Quantitative Posterior Predictive Assessment

**Posterior predictive p-value**: For a test statistic T(y), compute:

```
p_B = Pr(T(y_rep) >= T(y_obs) | y_obs)
```

where y_rep is data simulated from the posterior predictive distribution (Gelman et al., 2013, Ch. 6).

| p_B Value | Interpretation |
|-----------|---------------|
| 0.05 - 0.95 | No evidence of misfit for this statistic |
| < 0.05 or > 0.95 | Model systematically under- or over-predicts this feature |
| < 0.01 or > 0.99 | Strong evidence of misfit; model is missing an important data feature |

**Caution**: Posterior predictive p-values are conservative (they tend toward 0.5) because the same data are used for fitting and checking. A p-value near 0.5 does not guarantee good fit; it only means the check did not detect misfit (Gelman et al., 2013, Ch. 6).

**Choose meaningful test statistics**: Select statistics that capture features your model claims to explain. For DDMs, check RT quantiles, not just the mean. For RL models, check block-by-block learning, not just overall accuracy.

---

## Phase 5: Sensitivity Analysis

### 5.1 Prior Sensitivity

- [ ] Re-fit the model with **at least 2 alternative prior specifications**:
 - One with wider (more diffuse) priors
 - One with narrower (more informative) priors
- [ ] Compare posterior means, credible intervals, and qualitative conclusions
- [ ] If conclusions change substantially, report this and collect more data or justify your preferred prior (Schad et al., 2021)

### 5.2 What to Vary

| What to Vary | How | Concern If Results Change |
|-------------|-----|--------------------------|
| Prior SD on group means | Double and halve | Data may not be informative enough for this parameter |
| Prior on group-level SD | Try Half-Normal(0,0.5) vs Half-Normal(0,2) | Between-participant variance is poorly identified |
| Prior family | Try Normal vs. Student-t(3) for location parameters | Sensitivity to tail behavior |
| LKJ eta parameter | Try eta=1 vs eta=2 vs eta=4 | Correlation estimates driven by prior |
| Boundary-avoiding priors | Try Gamma vs. Lognormal for positive parameters | Choice of family matters for boundary behavior |

### 5.3 Reporting Sensitivity Results

In your manuscript, include a brief sensitivity analysis section:

- State which priors were varied and to what alternatives
- Report whether the main conclusions (direction and magnitude of key effects) are robust
- If conclusions are sensitive, acknowledge this as a limitation and specify what additional data or constraints could resolve the ambiguity

---

## Phase 6: Summary Diagnostic Table Template

For your manuscript or supplementary materials, report a table like:

| Parameter | R-hat | Bulk-ESS | Tail-ESS | Prior | Posterior Mean [95% CI] |
|-----------|-------|----------|----------|-------|------------------------|
| mu_v | 1.00 | 2847 | 2104 | Normal(0, 2) | 1.52 [0.98, 2.11] |
| sigma_v | 1.00 | 1523 | 1205 | Half-Normal(0, 1) | 0.61 [0.38, 0.92] |
| mu_a | 1.00 | 3102 | 2456 | Half-Normal(0, 1) | 1.14 [0.95, 1.35] |
| ... | ... | ... | ... | ... | ... |

Additional information to report:
- Number of divergent transitions: 0
- E-BFMI: all chains > 0.3
- Software: Stan 2.x / PyMC 5.x (specify version)
- Chains: 4, Warmup: 1000, Sampling: 2000, adapt_delta: 0.95

---

## Quick Reference: Diagnostic Decision Flowchart

```
1. Any divergent transitions?
 YES --> Fix parameterization (non-centered) or increase adapt_delta
 NO --> Continue

2. R-hat > 1.01 for any parameter?
 YES --> Run longer; check for multimodality; reparameterize
 NO --> Continue

3. Bulk-ESS or Tail-ESS < 400 for any parameter?
 YES --> Run longer; reparameterize; check autocorrelation
 NO --> Continue

4. E-BFMI < 0.3?
 YES --> Reparameterize; standardize parameter scales
 NO --> Continue

5. Tree depth saturation > 1%?
 YES --> Increase max_treedepth
 NO --> Continue

6. Visual checks pass (trace plots, rank plots, pair plots)?
 YES --> Proceed to posterior predictive checks
 NO --> Investigate identified issues

7. Posterior predictive checks pass?
 YES --> Proceed to sensitivity analysis and reporting
 NO --> Revise model; consider missing mechanisms or misspecified priors

8. Sensitivity analysis: conclusions robust to alternative priors?
 YES --> Report results with confidence
 NO --> Report sensitivity; acknowledge limitations; consider more data
```

---

## References

- Betancourt, M. (2017). A conceptual introduction to Hamiltonian Monte Carlo. *arXiv:1701.02434*.
- Betancourt, M., & Girolami, M. (2015). Hamiltonian Monte Carlo for hierarchical models. In *Current Trends in Bayesian Methodology with Applications*. Chapman and Hall/CRC.
- Daw, N. D. (2011). Trial-by-trial data analysis using computational models. In *Decision Making, Affect, and Learning*. Oxford University Press.
- Gelman, A., et al. (2013). *Bayesian Data Analysis* (3rd ed.). Chapman and Hall/CRC.
- Klauer, K. C. (2010). Hierarchical multinomial processing tree models: A latent-trait approach. *Psychometrika*, 75(1), 70-98.
- Macmillan, N. A., & Creelman, C. D. (2005). *Detection Theory: A User's Guide* (2nd ed.). Lawrence Erlbaum Associates.
- Ratcliff, R., & McKoon, G. (2008). The diffusion decision model: Theory and data for two-choice decision tasks. *Neural Computation*, 20(4), 873-922.
- Schad, D. J., Betancourt, M., & Vasishth, S. (2021). Toward a principled Bayesian workflow in cognitive science. *Psychological Methods*, 26(1), 103-126.
- Stephens, M. (2000). Dealing with label switching in mixture models. *Journal of the Royal Statistical Society: Series B*, 62(4), 795-809.
- Vehtari, A., Gelman, A., Simpson, D., Carpenter, B., & Burkner, P. C. (2021). Rank-normalization, folding, and localization: An improved R-hat for assessing convergence of MCMC. *Bayesian Analysis*, 16(2), 667-718.
- Wilson, R. C., & Collins, A. G. (2019). Ten simple rules for the computational modeling of behavioral data. *eLife*, 8, e49547.
