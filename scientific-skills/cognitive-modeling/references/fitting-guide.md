# DDM Parameter Fitting Guide

A complete workflow for fitting drift-diffusion models to behavioral data, from data preparation through model comparison and diagnostics. All numerical recommendations cite their sources.

---

## Table of Contents

1. [Data Preparation](#1-data-preparation)
2. [Model Selection](#2-model-selection)
3. [Fitting Methods](#3-fitting-methods)
4. [Fitting Tools](#4-fitting-tools)
5. [Model Comparison](#5-model-comparison)
6. [Parameter Recovery](#6-parameter-recovery)
7. [Posterior Predictive Checks](#7-posterior-predictive-checks)
8. [Common Pitfalls and Solutions](#8-common-pitfalls-and-solutions)

---

## 1. Data Preparation

### 1.1 Minimum Trial Requirements

| Model Variant | Minimum Trials per Condition | Recommended Trials | Source |
|---------------|------------------------------|--------------------|--------|
| EZ-diffusion | **20** | **40+** | Wagenmakers et al., 2007, simulation results |
| Classic DDM (4 parameters) | **40** | **100+** | Ratcliff & Childers, 2015, Table 2 |
| Full DDM (7 parameters) | **200** | **500+** | Ratcliff & Childers, 2015, Table 4 |
| HDDM (hierarchical) | **40** per participant | **100+** per participant | Wiecki et al., 2013 |

**Critical**: These are per-condition minimums. If you have 3 experimental conditions and want to fit separate drift rates per condition, you need the listed trial count in EACH condition.

### 1.2 Required Data Format

Each trial must include:
- **Response**: Which alternative was chosen (coded as upper/lower boundary or 0/1)
- **RT**: Reaction time in seconds
- **Accuracy**: Correct (1) or error (0)
- **Condition**: Experimental condition label

Optional but recommended:
- **Participant ID**: For hierarchical models
- **Trial number**: For detecting practice/fatigue effects

### 1.3 RT Distribution Characteristics to Check

Before fitting, verify your data has the expected RT distribution properties:

1. **Right-skewed distribution**: RT distributions should be positively skewed. If not, data may contain task noncompliance (Luce, 1986).
2. **Leading edge > 0**: The minimum RT should be plausible for the task (typically > **150 ms** for simple tasks; Ratcliff, 1993). Minimum RT estimates non-decision time.
3. **Error RT relationship**: Check whether error RTs are faster or slower than correct RTs — this constrains which model variant is appropriate (see model-variants.md, Section 2).

### 1.4 RT Outlier Treatment

RT outliers contaminate parameter estimates and must be handled before fitting.

#### Absolute Cutoffs

| Cutoff | Value | Rationale | Source |
|--------|-------|-----------|--------|
| Lower bound | **200 ms** | Below this, responses cannot reflect the decision process (too fast for stimulus encoding) | Ratcliff, 1993; Ratcliff & Tuerlinckx, 2002 |
| Upper bound (standard) | **3000 ms** | Likely reflects attention lapses or distraction for typical speeded tasks | Ratcliff & Tuerlinckx, 2002 |
| Upper bound (extended) | **5000 ms** | For more complex tasks (e.g., lexical decision with low-frequency words) | Ratcliff et al., 2004 |

#### Relative Cutoffs (Alternative Approach)

- Remove RTs > **3 SDs** above the participant's mean (per condition) — common in the literature but less principled than absolute cutoffs (Ratcliff, 1993)
- Note: SD-based cutoffs are problematic because the SD is inflated by the very outliers you are trying to remove

#### Recommended Approach

1. Apply absolute lower cutoff of **200 ms** (Ratcliff & Tuerlinckx, 2002)
2. Apply absolute upper cutoff of **3000 ms** for standard speeded tasks, **5000 ms** for tasks with known slow responses (Ratcliff & Tuerlinckx, 2002; Ratcliff et al., 2004)
3. Report the proportion of trials removed — should typically be < **5%** of all trials (if higher, investigate task design or participant compliance; Ratcliff & Tuerlinckx, 2002)
4. Alternative to hard cutoffs: use a **contaminant process** model that explicitly estimates the proportion of contaminant trials (Ratcliff & Tuerlinckx, 2002, Section 3.4; Hurvich & Tsai, 1989)

### 1.5 Speed-Accuracy Tradeoff Assessment

Before fitting, check for speed-accuracy tradeoff confounds:

- If participants were not given explicit speed-accuracy instructions, check whether there is a natural tradeoff (faster participants making more errors)
- If speed-accuracy emphasis was manipulated, this should be modeled by allowing boundary separation (a) to vary across speed/accuracy conditions (Ratcliff & McKoon, 2008)
- Red flag: if a condition has very high accuracy (> **97%**) with very fast RTs, the condition may be too easy for DDM — the model fits poorly when accuracy is near ceiling (Ratcliff & McKoon, 2008)

### 1.6 Accuracy Rates

- DDM is most informative when accuracy is in the range of **70-95%** (Ratcliff & McKoon, 2008)
- At ceiling accuracy (> **97%**), there are too few errors to constrain the model — consider using EZ-diffusion which does not require error RT information (Wagenmakers et al., 2007)
- At floor accuracy (< **55%**), participants may not be performing the task — data quality is suspect

---

## 2. Model Selection

### 2.1 Which Parameters Should Vary Across Conditions?

The core modeling decision: which DDM parameters are allowed to differ between experimental conditions, and which are fixed across conditions?

#### Common Constraint Patterns

| Manipulation Type | Typically Varies | Typically Fixed | Source |
|-------------------|-----------------|-----------------|--------|
| Stimulus difficulty (e.g., coherence, contrast) | v (drift rate) | a, t0, z | Ratcliff & McKoon, 2008 |
| Speed-accuracy emphasis | a (boundary separation) | v, t0, z | Ratcliff & McKoon, 2008 |
| Stimulus degradation (e.g., masking, blur) | t0 (non-decision time), possibly v | a, z | Ratcliff & McKoon, 2008 |
| Prior probability / cue validity | z (starting point) | v, a, t0 | Ratcliff & McKoon, 2008; Voss et al., 2004 |
| Response modality | t0 (non-decision time) | v, a, z | Ratcliff & McKoon, 2008 |

#### Strategy: Start Simple, Add Complexity

1. Start with the simplest model: only v varies across conditions (all other parameters fixed)
2. Add condition-dependent parameters one at a time based on theoretical motivation
3. Compare models using BIC/AIC/DIC (see Section 5)
4. Prefer the model that achieves adequate fit with fewer free parameters

### 2.2 How Many Free Parameters Can Your Data Support?

Rule of thumb: you need at least **10 trials per free parameter** per condition as a bare minimum, and **30+ trials per parameter** is preferred (Voss et al., 2013).

Example: Fitting a 4-parameter DDM with 2 conditions where v varies (5 total free parameters: v1, v2, a, t0, z) requires at minimum **50 trials per condition** (10 per parameter), and ideally **150+**.

---

## 3. Fitting Methods

### 3.1 Maximum Likelihood Estimation (MLE)

**How it works**: Find parameter values that maximize the probability of observing the data. The likelihood is computed from the first-passage time distribution of the diffusion process (Navarro & Fuss, 2009).

| Aspect | Details |
|--------|---------|
| **Software** | fast-dm (Voss & Voss, 2007), PyDDM (Shinn et al., 2020) |
| **Strengths** | Statistically efficient with large samples; well-understood asymptotic properties |
| **Weaknesses** | Requires large trial counts for stable estimates; sensitive to outliers; likelihood can be numerically unstable for extreme parameters |
| **Min trials** | **100+** per condition for reliable estimates (Ratcliff & Tuerlinckx, 2002) |
| **Model comparison** | AIC, BIC |

### 3.2 Chi-Square Fitting

**How it works**: Bin RTs into quantiles (e.g., .1, .3, .5, .7, .9 quantiles for correct and error RTs), compute predicted proportions from the model, minimize chi-square discrepancy between observed and predicted bin proportions (Ratcliff & Tuerlinckx, 2002).

| Aspect | Details |
|--------|---------|
| **Software** | fast-dm (Voss & Voss, 2007), custom implementations |
| **Strengths** | More robust than MLE with moderate trial counts; less sensitive to extreme individual RTs; well-established in the DDM literature |
| **Weaknesses** | Requires choice of quantile bins; less statistically efficient than MLE; discards some distributional information through binning |
| **Min trials** | **40+** per condition (Ratcliff & Tuerlinckx, 2002) |
| **Model comparison** | Chi-square goodness of fit; AIC/BIC with pseudo-likelihood |

**Recommended quantiles**: **.1, .3, .5, .7, .9** for both correct and error RT distributions (Ratcliff & McKoon, 2008). This gives 5 bins x 2 response types = 10 data points per condition to fit.

### 3.3 Quantile Maximum Probability (QMP)

**How it works**: Hybrid of quantile-based and likelihood approaches. Compute quantile bins as in chi-square fitting, but maximize the multinomial likelihood of the bin counts (Heathcote et al., 2002).

| Aspect | Details |
|--------|---------|
| **Software** | DMAT (Vandekerckhove & Tuerlinckx, 2008) |
| **Strengths** | More robust to outliers than MLE; more efficient than chi-square; handles unequal trial counts well |
| **Weaknesses** | Less widely used; fewer software implementations |
| **Min trials** | **40+** per condition (Heathcote et al., 2002) |
| **Model comparison** | AIC, BIC |

### 3.4 Bayesian Estimation (MCMC)

**How it works**: Place prior distributions on parameters, use Markov Chain Monte Carlo (MCMC) to sample from the posterior distribution (Wiecki et al., 2013; Vandekerckhove et al., 2011).

| Aspect | Details |
|--------|---------|
| **Software** | HDDM (Wiecki et al., 2013), JAGS/Stan custom implementations |
| **Strengths** | Full posterior distributions; hierarchical modeling; handles small samples via regularization; principled model comparison (Bayes factors, DIC, WAIC) |
| **Weaknesses** | Computationally expensive; requires convergence diagnostics; prior sensitivity; MCMC can be slow for complex models |
| **Min trials** | **40+** per condition per person (with hierarchical model; Wiecki et al., 2013) |
| **Model comparison** | DIC (Spiegelhalter et al., 2002), WAIC (Watanabe, 2010), Bayes factors |

### 3.5 Fitting Method Comparison

| Method | Best For | Min Trials | Outlier Robustness | Uncertainty Quantification |
|--------|----------|------------|--------------------|-----------------------------|
| MLE | Large datasets, individual-level fitting | **100+** | Low | Asymptotic SEs only |
| Chi-square | Moderate datasets, classic DDM applications | **40+** | Moderate | Limited |
| QMP | Moderate datasets, robustness desired | **40+** | High | Limited |
| Bayesian | Group studies, small-moderate samples, hierarchical models | **40+** (hierarchical) | Moderate (depends on priors) | Full posteriors |

**Recommendation**: For most cognitive science applications with **40-200 trials per condition** and a group of participants, hierarchical Bayesian estimation (HDDM) is the recommended approach due to its regularization benefits and natural uncertainty quantification (Wiecki et al., 2013; Vandekerckhove et al., 2011).

---

## 4. Fitting Tools

### 4.1 fast-dm (Voss & Voss, 2007)

| Feature | Details |
|---------|---------|
| **Language** | C (standalone executable) |
| **Methods** | MLE, chi-square, Kolmogorov-Smirnov |
| **Models** | Classic DDM, full DDM (with trial-to-trial variability) |
| **Strengths** | Very fast; well-validated; supports multiple fitting methods; mature and widely cited |
| **Limitations** | Command-line only; no hierarchical modeling; limited flexibility for custom models |
| **URL** | https://www.psychologie.uni-heidelberg.de/ae/meth/fast-dm/ |
| **Reference** | Voss, A., & Voss, J. (2007). Fast-dm: A free program for efficient diffusion model analysis. *Behavior Research Methods*, 39(4), 767–775. |

**Input format**: Text file with one trial per line: RT (in seconds), response (0 or 1), condition.

### 4.2 HDDM (Wiecki et al., 2013)

| Feature | Details |
|---------|---------|
| **Language** | Python |
| **Methods** | Bayesian estimation via MCMC (DE-MCMC or No-U-Turn Sampler) |
| **Models** | Classic DDM, full DDM, stimulus-coding, accuracy-coding, regression models |
| **Strengths** | Hierarchical modeling; full posterior distributions; regression on parameters (link neural/physiological data to DDM parameters); well-documented |
| **Limitations** | Slow for large datasets; requires MCMC convergence diagnostics; Python 3 compatibility varies by version |
| **URL** | https://github.com/hddm-devs/hddm |
| **Reference** | Wiecki, T. V., Sofer, I., & Frank, M. J. (2013). HDDM: Hierarchical Bayesian estimation of the drift-diffusion model in Python. *Frontiers in Neuroinformatics*, 7, 14. |

**Key usage notes**:
- Run at least **3 chains** with **5000+ samples** each, discarding the first **1000 as burn-in** (Wiecki et al., 2013, recommended practice)
- Check R-hat < **1.1** for all parameters (Gelman & Rubin, 1992)
- Use `hddm.utils.post_pred_gen()` for posterior predictive checks

### 4.3 EZ-Diffusion (Wagenmakers et al., 2007)

| Feature | Details |
|---------|---------|
| **Language** | Closed-form equations (implementable in any language: R, Python, Excel, MATLAB) |
| **Methods** | Direct computation from summary statistics |
| **Models** | Simplified DDM (v, a, t0 only; z = a/2 assumed) |
| **Strengths** | No fitting needed; instant computation; excellent for exploratory analysis and large-scale individual differences |
| **Limitations** | Cannot estimate starting point bias or variability parameters; does not use error RT information |
| **Reference** | Wagenmakers, E.-J., van der Maas, H. L. J., & Grasman, R. P. P. P. (2007). An EZ-diffusion model for response time and accuracy. *Psychonomic Bulletin & Review*, 14(1), 3–22. |

**Equations** (with s = 0.1; Wagenmakers et al., 2007, Equations 1-3):

```
# Given: Pc (proportion correct), VRT (variance of correct RTs), MRT (mean correct RT)

# Step 1: Compute drift rate
L = logit(Pc) # L = ln(Pc / (1 - Pc))
sign_v = sign(Pc - 0.5)
x = L * (L * Pc^2 - L * Pc + Pc - 0.5) / VRT
v = sign_v * s * x^(1/4) # s = 0.1

# Step 2: Compute boundary separation
a = s^2 * L / v

# Step 3: Compute non-decision time
y = -v * a / s^2
MDT = (a / (2*v)) * (1 - exp(y)) / (1 + exp(y))
t0 = MRT - MDT
```

### 4.4 PyDDM (Shinn et al., 2020)

| Feature | Details |
|---------|---------|
| **Language** | Python |
| **Methods** | MLE via numerical solution of Fokker-Planck equation |
| **Models** | Highly flexible: custom drift, noise, bound, overlay functions |
| **Strengths** | Maximum flexibility; supports collapsing bounds, leaky integration, custom noise; good documentation and tutorials |
| **Limitations** | Slower than fast-dm for standard models; requires more programming expertise; no built-in hierarchical modeling |
| **URL** | https://pyddm.readthedocs.io/ |
| **Reference** | Shinn, M., Lam, N. H., & Murray, J. D. (2020). A flexible framework for simulating and fitting generalized drift-diffusion models. *eLife*, 9, e56938. |

### 4.5 Additional Tools

| Tool | Language | Key Feature | Reference |
|------|----------|-------------|-----------|
| **DMAT** | MATLAB | Multi-model fitting, QMP method | Vandekerckhove & Tuerlinckx, 2008 |
| **rtdists** (R) | R | RT distribution functions for DDM and LBA | Singmann et al., 2016 |
| **DMC** (Dynamic Models of Choice) | R | LBA and DDM fitting with comprehensive diagnostics | Heathcote et al., 2019 |
| **Stan** | Stan/R/Python | Custom Bayesian models; maximum flexibility | Carpenter et al., 2017 |

### 4.6 Tool Selection Guide

```
What is your primary need?
├── Quick analysis, few trials → EZ-diffusion (any language)
├── Standard DDM, fast fitting → fast-dm
├── Hierarchical / Bayesian → HDDM
├── Custom model (collapsing bounds, etc.) → PyDDM
├── LBA or multi-accumulator → DMC (R) or rtdists (R)
└── Full Bayesian flexibility → Stan
```

---

## 5. Model Comparison

### 5.1 Information Criteria

| Criterion | Formula | Best For | Interpretation | Source |
|-----------|---------|----------|----------------|--------|
| AIC | -2 ln(L) + 2k | Prediction; large samples | Lower is better; penalizes complexity linearly | Akaike, 1974 |
| BIC | -2 ln(L) + k ln(n) | Model selection; penalizes complexity more than AIC | Lower is better; stronger complexity penalty with large n | Schwarz, 1978 |
| DIC | Bayesian analogue of AIC | Bayesian models | Lower is better; uses effective number of parameters | Spiegelhalter et al., 2002 |
| WAIC | Bayesian; fully uses posterior | Bayesian models; preferred over DIC | Lower is better; more stable than DIC | Watanabe, 2010 |

where L = likelihood, k = number of free parameters, n = number of observations.

**Recommendation**: Use BIC for frequentist DDM fits (penalizes overfitting more than AIC; Schwarz, 1978). Use WAIC for Bayesian HDDM fits (more stable than DIC; Watanabe, 2010).

### 5.2 Delta Rules of Thumb

| Delta | Interpretation | Source |
|-------|----------------|--------|
| delta BIC < 2 | Negligible difference | Raftery, 1995 |
| delta BIC 2-6 | Positive evidence for better model | Raftery, 1995 |
| delta BIC 6-10 | Strong evidence | Raftery, 1995 |
| delta BIC > 10 | Very strong evidence | Raftery, 1995 |

**Note**: These guidelines were developed by Raftery (1995) for BIC specifically. Similar scales exist for AIC (Burnham & Anderson, 2002), but direct comparison requires the same criterion.

### 5.3 Model Comparison Strategy

1. **Define candidate models**: List all theoretically motivated models (e.g., v varies vs. v and a vary across conditions)
2. **Fit all models** to the same data with the same method
3. **Compute information criterion** (BIC or WAIC) for each model
4. **Compute summed/group BIC**: Sum individual BIC values across participants (Stephan et al., 2009)
5. **Check fit quality**: The winning model should also provide adequate absolute fit (see Section 7)
6. **Sensitivity analysis**: Check whether the winning model is consistent across fitting methods (e.g., MLE and Bayesian give similar conclusions)

### 5.4 Nested Model Testing

For nested models (e.g., classic DDM nested within full DDM), you can also use:

- **Likelihood ratio test**: chi-square = -2 × (ln L_simple - ln L_complex), df = difference in parameters. Valid for MLE with large samples (Ratcliff & Tuerlinckx, 2002).
- **Bayes factor**: Ratio of marginal likelihoods. Interpretation: BF > **3** is "moderate evidence," BF > **10** is "strong evidence" (Kass & Raftery, 1995).

---

## 6. Parameter Recovery

### 6.1 Why Parameter Recovery Is Essential

Parameter recovery verifies that your fitting pipeline (data structure, fitting method, software settings) can accurately estimate parameters from simulated data with known ground truth. Without this validation, your empirical results may be uninterpretable (Heathcote et al., 2015; White et al., 2018).

### 6.2 Parameter Recovery Procedure

1. **Choose plausible generating parameters**: Use values from the literature or from a preliminary fit to your data
 - v: **0.5, 1.0, 2.0, 3.0** (spanning easy to hard conditions; Ratcliff & McKoon, 2008)
 - a: **0.8, 1.2, 1.6, 2.0** (spanning liberal to conservative criteria)
 - t0: **0.2, 0.3, 0.4, 0.5** (spanning fast to slow encoding)
 - z: **a/2** (unbiased) or **0.4a, 0.6a** (biased)

2. **Simulate datasets**: For each parameter combination, simulate **100+ datasets** with the same trial count and condition structure as your empirical data (White et al., 2018)

3. **Fit the model** to each simulated dataset using the exact same pipeline as for real data

4. **Evaluate recovery**:
 - **Correlation**: r between true and recovered parameters should be > **0.8** (White et al., 2018, benchmark)
 - **Bias**: Mean (recovered - true) should be near 0
 - **Coverage**: 95% CIs should contain the true value approximately **95%** of the time
 - **Scatter plots**: Plot true vs. recovered for each parameter

### 6.3 What to Do If Recovery Fails

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| Recovered parameters are biased | Too few trials | Increase trial count or simplify the model |
| Wide recovery variability | Too few trials or too many free parameters | Reduce free parameters; use HDDM for regularization |
| sv, sz, st0 poorly recovered | These parameters require the most data | Fix variability parameters you do not need; use > **200 trials per condition** (Ratcliff & Childers, 2015) |
| Correlations between recovered parameters | Trade-offs between parameters (e.g., a and t0) | Reparameterize or fix one parameter; check identifiability |
| t0 recovered as negative | Model misspecification or outlier contamination | Check RT cutoffs; verify lower RT bound > estimated t0 |

### 6.4 Selective Influence Validation

A stronger form of recovery: simulate data where only ONE parameter changes across conditions. Verify that the fitting pipeline correctly identifies which parameter changed (Ratcliff & McKoon, 2008; White et al., 2018).

Example: Simulate two conditions that differ only in drift rate (v1 = 1.0, v2 = 2.0, all other parameters shared). After fitting, verify that only v differs significantly across conditions.

---

## 7. Posterior Predictive Checks

### 7.1 Purpose

Even if a model wins by BIC/WAIC, it might fit the data poorly in absolute terms. Posterior predictive checks compare the model's predictions to the observed data to verify adequate fit (Gelman et al., 2013; Ratcliff & McKoon, 2008).

### 7.2 RT Quantile Comparison

The standard visualization in the DDM literature (Ratcliff & McKoon, 2008, Figure 2):

1. **Compute observed RT quantiles**: Calculate the .1, .3, .5, .7, .9 quantiles of correct and error RT distributions for each condition
2. **Simulate from the model**: Using fitted parameters, generate many simulated datasets (e.g., **500 simulations**; Wiecki et al., 2013)
3. **Compute predicted quantiles**: From the simulated data
4. **Plot**: Observed quantiles (points) vs. predicted quantiles (lines or confidence bands)
5. **Evaluate**: Predicted quantiles should fall close to observed. Systematic deviations indicate model misfit.

### 7.3 What to Look For

| Pattern | Interpretation | Action |
|---------|----------------|--------|
| Good fit across all quantiles and conditions | Model is adequate | Proceed with interpretation |
| Poor fit to slow RT tail (.9 quantile) | Contaminant slow responses or model cannot capture slow decisions | Add contaminant process; check for attention lapses; consider collapsing bounds |
| Poor fit to fast RT leading edge (.1 quantile) | Non-decision time misspecified | Allow t0 variability (st0) |
| Poor fit to error RTs specifically | Model cannot capture error RT pattern | Add trial-to-trial variability in drift rate (sv) or starting point (sz) |
| Predicted accuracy does not match observed | Drift rate or boundary misestimated | Check for speed-accuracy tradeoff confounds; reconsider constraint pattern |

### 7.4 Quantitative Fit Statistics

- **Chi-square goodness of fit**: Compare observed vs. predicted quantile bin counts. Non-significant chi-square indicates adequate fit (Ratcliff & McKoon, 2008).
- **Posterior predictive p-values**: For Bayesian models, compute the proportion of posterior predictions that fall within the observed data range. Values near **0.5** indicate good fit; values near 0 or 1 indicate misfit (Gelman et al., 2013).

---

## 8. Common Pitfalls and Solutions

### 8.1 Data-Related Pitfalls

#### Pitfall 1: Not Removing Fast Guesses

**Problem**: RTs < **200 ms** likely reflect anticipatory responses or button-press errors, not the decision process (Ratcliff, 1993).

**Solution**: Remove RTs below **200 ms** before fitting. If removing a large proportion (> **5%**), investigate task design or participant compliance (Ratcliff & Tuerlinckx, 2002).

#### Pitfall 2: Including Attention Lapses

**Problem**: Very slow RTs (> **3000-5000 ms**) likely reflect attention lapses, not the diffusion process. These distort the slow tail of the RT distribution and inflate non-decision time or drift rate variability estimates (Ratcliff & Tuerlinckx, 2002).

**Solution**: Apply an upper RT cutoff of **3000 ms** for standard tasks or **5000 ms** for complex tasks (Ratcliff & Tuerlinckx, 2002; Ratcliff et al., 2004). Alternatively, include a contaminant process in the model (see Pitfall 7).

#### Pitfall 3: Ceiling or Floor Accuracy

**Problem**: When accuracy is near ceiling (> **97%**) or floor (< **55%**), there are too few errors (or correct responses) to constrain the model. The DDM jointly models correct and error RT distributions; without sufficient data in both, parameter estimates are unreliable (Ratcliff & McKoon, 2008).

**Solution**: For ceiling accuracy, use EZ-diffusion (which only requires correct RT statistics; Wagenmakers et al., 2007). For floor accuracy, investigate whether participants are performing the task at all.

### 8.2 Model Specification Pitfalls

#### Pitfall 4: Fitting Too Many Parameters

**Problem**: With 7 free parameters (full DDM), moderate trial counts produce unstable estimates. Trial-to-trial variability parameters (sv, sz, st0) are particularly difficult to estimate and can trade off with each other (Boehm et al., 2018).

**Solution**: Follow the guideline: approximately **10 trials per free parameter** as a minimum, **30+ preferred** (Voss et al., 2013). With < **200 trials per condition**, consider fixing variability parameters. Priority order for fixing: sz first, then st0, keep sv if possible (Ratcliff & Childers, 2015; Boehm et al., 2018).

#### Pitfall 5: Wrong Parameter Constraints Across Conditions

**Problem**: Allowing too many parameters to vary across conditions overfits; constraining too many masks real effects.

**Solution**: Let theory guide which parameters vary. Use the table in Section 2.1. Start simple, add complexity based on model comparison. Critical: speed-accuracy instructions should affect a, NOT v (Ratcliff & McKoon, 2008). Stimulus difficulty should affect v, NOT a.

#### Pitfall 6: Ignoring Response Coding

**Problem**: DDMs require coding responses as "upper boundary" vs. "lower boundary." Incorrect coding (e.g., coding by response key rather than by stimulus-response mapping) produces nonsensical drift rate estimates.

**Solution**: Two coding schemes:
- **Stimulus coding**: Upper boundary = response to stimulus A, lower boundary = response to stimulus B. Drift rate sign indicates which stimulus was presented. Standard for perceptual discrimination tasks (Ratcliff & McKoon, 2008).
- **Accuracy coding**: Upper boundary = correct response, lower boundary = error. Drift rate is always positive. Standard in HDDM (Wiecki et al., 2013).

Choose one scheme and be consistent. HDDM default is accuracy coding.

### 8.3 Fitting and Evaluation Pitfalls

#### Pitfall 7: Not Modeling Contaminant Processes

**Problem**: Even after RT cutoffs, some trials may reflect processes other than the decision (e.g., accidental key presses, motor errors). These contaminate parameter estimates (Ratcliff & Tuerlinckx, 2002).

**Solution**: Include a contaminant process in the model. The standard approach adds a uniform distribution over the RT range with probability p_contaminant (typically **1-5%** of trials; Ratcliff & Tuerlinckx, 2002, Section 3.4). Available in fast-dm and HDDM.

#### Pitfall 8: Not Running Multiple Starting Points (MLE)

**Problem**: The DDM likelihood surface can have local optima. A single optimization run may converge to a local minimum rather than the global MLE (Voss et al., 2013).

**Solution**: Run the optimizer from **5-10 different starting points** and select the result with the highest likelihood (Voss et al., 2013). fast-dm does this automatically.

#### Pitfall 9: Ignoring MCMC Convergence (Bayesian)

**Problem**: MCMC chains that have not converged produce unreliable posterior estimates. Common with complex models or poor priors.

**Solution**:
- Run at least **3 independent chains** (Wiecki et al., 2013)
- Check R-hat < **1.1** for ALL parameters (Gelman & Rubin, 1992)
- Verify effective sample size > **200** (Wiecki et al., 2013)
- Visually inspect trace plots for mixing
- Increase burn-in or total samples if convergence is poor

#### Pitfall 10: Skipping Parameter Recovery

**Problem**: Without parameter recovery validation, you cannot know whether your pipeline produces reliable estimates for your specific data structure (Heathcote et al., 2015; White et al., 2018).

**Solution**: Always run parameter recovery before interpreting empirical results. Simulate data with known parameters using YOUR exact pipeline (same trial counts, same conditions, same fitting method, same software). This is a mandatory validation step, not optional (White et al., 2018).

---

## Complete Fitting Workflow Checklist

```
[ ] 1. DATA PREPARATION
 [ ] Format data: RT (seconds), response, accuracy, condition, participant
 [ ] Apply RT cutoffs: remove < 200 ms and > 3000-5000 ms
 [ ] Report proportion of trials removed (should be < 5%)
 [ ] Check RT distributions: right-skewed? Plausible leading edge?
 [ ] Check accuracy: 70-95% range for DDM applicability?
 [ ] Check error RT pattern: faster or slower than correct RTs?

[ ] 2. MODEL SELECTION
 [ ] Define candidate models (which parameters vary across conditions?)
 [ ] Verify trial count supports the number of free parameters
 [ ] Choose model variant (EZ, classic, full, hierarchical)

[ ] 3. PARAMETER RECOVERY
 [ ] Select generating parameters (use literature or preliminary fits)
 [ ] Simulate 100+ datasets with your empirical data structure
 [ ] Fit all simulated datasets with your exact pipeline
 [ ] Verify: r > 0.8, minimal bias, adequate coverage

[ ] 4. FIT EMPIRICAL DATA
 [ ] Fit all candidate models
 [ ] For MLE: use 5-10 starting points
 [ ] For Bayesian: run 3+ chains, 5000+ samples, 1000+ burn-in

[ ] 5. CONVERGENCE CHECK
 [ ] MLE: verify optimizer converged (check gradient, Hessian)
 [ ] Bayesian: R-hat < 1.1, effective n > 200, good trace plots

[ ] 6. MODEL COMPARISON
 [ ] Compute BIC (frequentist) or WAIC/DIC (Bayesian)
 [ ] Select winning model
 [ ] Verify winning model also has adequate absolute fit

[ ] 7. POSTERIOR PREDICTIVE CHECK
 [ ] Simulate from fitted model (500+ datasets)
 [ ] Compare predicted vs. observed RT quantiles (.1, .3, .5, .7, .9)
 [ ] Check correct and error RT distributions separately
 [ ] Check predicted vs. observed accuracy

[ ] 8. REPORT RESULTS
 [ ] Report all parameter estimates with uncertainty (SEs or CIs)
 [ ] Report model comparison statistics (BIC/WAIC)
 [ ] Include posterior predictive check figures
 [ ] Report RT cutoffs, trial counts, and proportion removed
 [ ] Report parameter recovery results
```

---

## References

- Akaike, H. (1974). A new look at the statistical model identification. *IEEE Transactions on Automatic Control*, 19(6), 716–723.
- Boehm, U., Annis, J., Frank, M. J., Hawkins, G. E., Heathcote, A., Kellen, D., ... & Wagenmakers, E.-J. (2018). Estimating across-trial variability parameters of the diffusion decision model: Expert advice and recommendations. *Journal of Mathematical Psychology*, 87, 46–75.
- Burnham, K. P., & Anderson, D. R. (2002). *Model selection and multimodel inference: A practical information-theoretic approach* (2nd ed.). Springer.
- Carpenter, B., Gelman, A., Hoffman, M. D., Lee, D., Goodrich, B., Betancourt, M., ... & Riddell, A. (2017). Stan: A probabilistic programming language. *Journal of Statistical Software*, 76(1), 1–32.
- Gelman, A., Carlin, J. B., Stern, H. S., Dunson, D. B., Vehtari, A., & Rubin, D. B. (2013). *Bayesian data analysis* (3rd ed.). CRC Press.
- Gelman, A., & Rubin, D. B. (1992). Inference from iterative simulation using multiple sequences. *Statistical Science*, 7(4), 457–472.
- Heathcote, A., Brown, S., & Mewhort, D. J. K. (2002). Quantile maximum probability as a method for response time distributions. *Psychonomic Bulletin & Review*, 9(2), 394–401.
- Heathcote, A., Brown, S. D., & Wagenmakers, E.-J. (2015). An introduction to good practices in cognitive modeling. In B. U. Forstmann & E.-J. Wagenmakers (Eds.), *An introduction to model-based cognitive neuroscience*. Springer.
- Heathcote, A., Lin, Y., Reynolds, A., Strickland, L., Gretton, M., & Matzke, D. (2019). Dynamic models of choice. *Behavior Research Methods*, 51(2), 961–985.
- Kass, R. E., & Raftery, A. E. (1995). Bayes factors. *Journal of the American Statistical Association*, 90(430), 773–795.
- Luce, R. D. (1986). *Response times: Their role in inferring elementary mental organization*. Oxford University Press.
- Matzke, D., & Wagenmakers, E.-J. (2009). Psychological interpretation of the ex-Gaussian and shifted Wald parameters: A diffusion model analysis. *Psychonomic Bulletin & Review*, 16(5), 798–817.
- Navarro, D. J., & Fuss, I. G. (2009). Fast and accurate calculations for first-passage times in Wiener diffusion models. *Journal of Mathematical Psychology*, 53(4), 222–230.
- Raftery, A. E. (1995). Bayesian model selection in social research. *Sociological Methodology*, 25, 111–163.
- Ratcliff, R. (1993). Methods for dealing with reaction time outliers. *Psychological Bulletin*, 114(3), 510–532.
- Ratcliff, R., & Childers, R. (2015). Individual differences and fitting methods for the two-choice diffusion model of decision making. *Decision*, 2(4), 237–279.
- Ratcliff, R., Gomez, P., & McKoon, G. (2004). A diffusion model account of the lexical decision task. *Psychological Review*, 111(1), 159–182.
- Ratcliff, R., & McKoon, G. (2008). The diffusion decision model: Theory and data for two-choice decision tasks. *Neural Computation*, 20(4), 873–922.
- Ratcliff, R., & Tuerlinckx, F. (2002). Estimating parameters of the diffusion model: Approaches to dealing with contaminant reaction times and parameter variability. *Psychonomic Bulletin & Review*, 9(3), 438–481.
- Schwarz, G. (1978). Estimating the dimension of a model. *The Annals of Statistics*, 6(2), 461–464.
- Shinn, M., Lam, N. H., & Murray, J. D. (2020). A flexible framework for simulating and fitting generalized drift-diffusion models. *eLife*, 9, e56938.
- Singmann, H., Brown, S., Gretton, M., & Heathcote, A. (2016). rtdists: Response time distributions. R package.
- Spiegelhalter, D. J., Best, N. G., Carlin, B. P., & van der Linde, A. (2002). Bayesian measures of model complexity and fit. *Journal of the Royal Statistical Society: Series B*, 64(4), 583–639.
- Stephan, K. E., Penny, W. D., Daunizeau, J., Moran, R. J., & Friston, K. J. (2009). Bayesian model selection for group studies. *NeuroImage*, 46(4), 1004–1017.
- Vandekerckhove, J., & Tuerlinckx, F. (2008). Fitting and testing the diffusion model using DMAT. *Behavior Research Methods*, 40(2), 571–582.
- Vandekerckhove, J., Tuerlinckx, F., & Lee, M. D. (2011). Hierarchical diffusion models for two-choice response times. *Psychological Methods*, 16(1), 44–62.
- Voss, A., Nagler, M., & Lerche, V. (2013). Diffusion models in experimental psychology: A practical introduction. *Experimental Psychology*, 60(6), 385–402.
- Voss, A., & Voss, J. (2007). Fast-dm: A free program for efficient diffusion model analysis. *Behavior Research Methods*, 39(4), 767–775.
- Wagenmakers, E.-J., van der Maas, H. L. J., & Grasman, R. P. P. P. (2007). An EZ-diffusion model for response time and accuracy. *Psychonomic Bulletin & Review*, 14(1), 3–22.
- Watanabe, S. (2010). Asymptotic equivalence of Bayes cross validation and widely applicable information criterion in singular learning theory. *Journal of Machine Learning Research*, 11, 3571–3594.
- White, C. N., Servant, M., & Logan, G. D. (2018). Testing the validity of conflict drift-diffusion models for use in estimating cognitive processes: A parameter-recovery study. *Psychonomic Bulletin & Review*, 25(1), 286–301.
- Wiecki, T. V., Sofer, I., & Frank, M. J. (2013). HDDM: Hierarchical Bayesian estimation of the drift-diffusion model in Python. *Frontiers in Neuroinformatics*, 7, 14.
