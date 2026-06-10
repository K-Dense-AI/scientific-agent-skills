# Common Statistical Analyses in Cognitive Science

This file provides concrete analysis recipes for typical cognitive science designs. Each recipe specifies: when to use it, the model specification, code patterns (R and/or Python), what to report, and common pitfalls.

---

## Recipe 1: Between-Subjects Factorial Design

### When to Use
- Two or more groups (e.g., patient vs. control, training vs. no-training)
- Dependent variable is continuous (RT, accuracy rate, questionnaire score)
- Each participant contributes one observation per cell (or an aggregated mean)

### Model Specification
- Factorial ANOVA (Type III sums of squares for unbalanced designs; Langsrud, 2003)
- Follow up with planned contrasts or post-hoc comparisons

### R Code Pattern

```r
library(afex)
library(emmeans)

# Type III ANOVA via afex (handles unbalanced designs correctly)
model <- aov_ez(id = "subject", dv = "RT_mean",
 between = c("group", "condition"), data = d)
summary(model) # provides partial eta-squared automatically

# Planned contrasts
emm <- emmeans(model, ~ group | condition)
contrast(emm, method = "pairwise", adjust = "holm")

# Effect sizes for pairwise comparisons
eff_size(emm, sigma = sigma(model$lm), edf = df.residual(model$lm))
```

### What to Report
- F-statistic, df (numerator, denominator), exact p-value
- Partial eta-squared with **90% CI** (not 95%; see Steiger, 2004)
- Post-hoc: estimated marginal means, mean difference, CI, Cohen's d
- Sample size per cell

### Common Pitfalls
- Using Type I SS with unbalanced designs (inflates effects entered first in the model; Langsrud, 2003)
- Forgetting to check homogeneity of variance (Levene's test; use Welch ANOVA if violated)
- Reporting eta-squared instead of partial eta-squared for factorial designs (Richardson, 2011)

---

## Recipe 2: Within-Subjects Design with Continuous Predictor (LMM)

### When to Use
- Repeated measures over subjects (and potentially items)
- At least one continuous predictor (e.g., word frequency, stimulus duration, trial number)
- Trial-level analysis preferred (not condition means)

### Model Specification (Barr et al., 2013)

Fit the maximal random effects structure justified by the design:

```r
library(lme4)
library(lmerTest) # for p-values via Satterthwaite approximation

# Example: effect of word frequency (continuous) and condition (categorical)
# on RT in a lexical decision task
model <- lmer(log_RT ~ frequency_c * condition +
 (1 + frequency_c * condition | subject) +
 (1 + condition | item),
 data = d,
 control = lmerControl(optimizer = "bobyqa",
 optCtrl = list(maxfun = 20000)))

summary(model)
```

**Key decisions**:
- Center continuous predictors to reduce collinearity (Schielzeth, 2010)
- Use **Satterthwaite** or **Kenward-Roger** df approximation for p-values (Luke, 2017). Satterthwaite is the lmerTest default and is adequate for most cognitive science designs.
- If maximal model fails to converge, follow the simplification hierarchy in `../SKILL.md`

### Python Code Pattern

```python
import statsmodels.formula.api as smf

# Note: statsmodels MixedLM has limited random effects support
# For complex crossed random effects, use R (lme4) or pymer4
model = smf.mixedlm("log_RT ~ frequency_c * condition",
 data=d, groups=d["subject"],
 re_formula="~frequency_c * condition")
result = model.fit()
print(result.summary())
```

### What to Report
- Fixed effects: estimate (beta), SE, df, t-value, exact p-value
- Random effects: variance and SD for each random term
- Model specification (full formula including random effects)
- Optimizer used and convergence status
- Effect size: standardized beta or semi-partial R-squared (Rights & Sterba, 2019)

### Common Pitfalls
- Not centering continuous predictors (leads to uninterpretable intercepts and inflated collinearity)
- Using `anova()` on lmer objects without specifying `type = 3` (default is Type I)
- Ignoring singular fit warnings (indicates overparameterized random effects; simplify)
- Using Wald p-values from `summary()` without lmerTest loaded (Wald z-tests are anti-conservative for small samples)

---

## Recipe 3: Reaction Time Analysis

### When to Use
- Any experiment measuring response latency
- Need to handle the characteristic right-skewed, positive-only distribution of RT

### Step 1: Data Cleaning

```r
# RT outlier exclusion (Ratcliff, 1993; Whelan, 2008)
d <- d %>%
 filter(accuracy == 1) %>% # Only correct trials
 filter(RT >= 200) %>% # Remove anticipatory (< 200 ms; Ratcliff, 1993)
 group_by(subject, condition) %>%
 filter(RT <= mean(RT) + 3 * sd(RT), # Remove > 3 SD (Van Selst & Jolicoeur, 1994)
 RT >= mean(RT) - 3 * sd(RT)) %>%
 ungroup()

# Report: "X% of correct trials were excluded as RT outliers"
```

### Step 2: Model Fitting (Recommended: Gamma GLMM)

```r
library(lme4)

# Gamma GLMM with identity link (Lo & Andrews, 2015)
# Results are on the original ms scale
model <- glmer(RT ~ condition * group +
 (1 + condition | subject) + (1 | item),
 family = Gamma(link = "identity"),
 data = d,
 control = glmerControl(optimizer = "bobyqa",
 optCtrl = list(maxfun = 50000)))
summary(model)
```

**Alternative: Log-transform + LMM** (simpler, widely accepted):

```r
d$log_RT <- log(d$RT)
model <- lmer(log_RT ~ condition * group +
 (1 + condition | subject) + (1 | item),
 data = d)
```

### Python Code Pattern

```python
# Using pymer4 for R-like mixed models in Python
from pymer4.models import Lmer

model = Lmer("log_RT ~ condition * group + (1 + condition | subject) + (1 | item)",
 data=d)
model.fit()
print(model.summary())
```

### What to Report
- Outlier exclusion criteria and percentage excluded
- Model family and link function (if GLMM)
- Transform applied (if any)
- Fixed effects on appropriate scale
- Whether results are consistent across modeling approaches (robustness check)

### Common Pitfalls
- Analyzing mean RT without checking for speed-accuracy tradeoffs (check accuracy across conditions)
- Not excluding error trials before RT analysis (errors have different RT distributions; Ratcliff, 1993)
- Using raw RT with ANOVA (violates normality; Ratcliff, 1993)
- Forgetting that log-transformed effects are multiplicative, not additive (Lo & Andrews, 2015)

---

## Recipe 4: Accuracy / Binary Response Analysis

### When to Use
- Dependent variable is binary (correct/incorrect, yes/no, detected/missed)
- Trial-level analysis (not proportion correct averaged over subjects)

### Model Specification

```r
library(lme4)

# Logistic mixed-effects model (Jaeger, 2008)
model <- glmer(accuracy ~ condition * difficulty +
 (1 + condition * difficulty | subject) +
 (1 + condition | item),
 family = binomial(link = "logit"),
 data = d,
 control = glmerControl(optimizer = "bobyqa",
 optCtrl = list(maxfun = 50000)))

summary(model)

# Odds ratios (exponentiate coefficients)
exp(fixef(model))
exp(confint(model, method = "Wald"))
```

### Python Code Pattern

```python
import statsmodels.formula.api as smf

# GEE approach (accounts for within-subject clustering)
model = smf.gee("accuracy ~ condition * difficulty",
 groups="subject", family=sm.families.Binomial(),
 data=d)
result = model.fit()
```

### What to Report
- Log-odds (beta) with SE, z-value, p-value
- Odds ratios with 95% CI (exponentiated coefficients)
- Model specification and random effects structure
- If complete separation occurs, note it and consider Firth's penalized likelihood (Heinze & Schemper, 2002)

### Common Pitfalls
- Running ANOVA on proportion correct (violates normality, bounded at 0 and 1; Jaeger, 2008; Dixon, 2008)
- Using arcsine transform instead of logistic regression (arcsine is outdated; Warton & Hui, 2011)
- Ignoring complete or quasi-complete separation in logistic models (inflates SE to infinity)
- Not checking for ceiling/floor effects before analysis (if > **95%** accuracy, logistic models may be unstable)

---

## Recipe 5: EEG Cluster-Based Permutation Test

### When to Use
- Comparing ERP waveforms or time-frequency representations across conditions
- No strong a priori hypothesis about specific time windows or channels
- Want to control family-wise error across the full spatiotemporal data matrix

### Method (Maris & Oostenveld, 2007)

1. Compute test statistic (t or F) at each time-channel pair
2. Threshold at **p < 0.05** (uncorrected) to identify candidate clusters (Maris & Oostenveld, 2007, default)
3. Sum test statistics within each cluster to get cluster mass
4. Build null distribution by permuting condition labels **1000-5000** times (Maris & Oostenveld, 2007 recommend minimum 1000; 5000 for publication-quality results)
5. Compare observed cluster mass to null distribution
6. Reject cluster if it exceeds the **95th percentile** of null distribution (alpha = 0.05)

### Python Code Pattern (MNE-Python)

```python
import mne
from mne.stats import spatio_temporal_cluster_test

# For within-subjects comparison of two conditions
X = [condition_A_epochs, condition_B_epochs] # shape: (n_subjects, n_times, n_channels)

# Adjacency matrix for spatial clustering
adjacency, ch_names = mne.channels.find_ch_adjacency(epochs.info, ch_type='eeg')

# Cluster-based permutation test
T_obs, clusters, cluster_p_values, H0 = spatio_temporal_cluster_test(
 X,
 n_permutations=5000, # Maris & Oostenveld, 2007; minimum 1000
 threshold=None, # None = use default t-threshold
 tail=0, # Two-tailed
 adjacency=adjacency,
 n_jobs=-1
)

# Identify significant clusters
significant_clusters = [c for c, p in zip(clusters, cluster_p_values) if p < 0.05]
```

### R Code Pattern (permuco)

```r
library(permuco)

# Cluster-mass permutation test
result <- clusterlm(signal ~ condition + Error(subject / condition),
 data = eeg_data,
 np = 5000, # Number of permutations
 multcomp = "clustermass",
 threshold = qt(0.975, df = n_subjects - 1))
summary(result)
```

### What to Report
- Cluster-forming threshold
- Number of permutations
- For each significant cluster: time range, channels involved, cluster mass, cluster p-value
- Effect size within the cluster time window (Cohen's d)

### Common Pitfalls
- Interpreting cluster boundaries as precise spatiotemporal localization (clusters indicate EXISTENCE of an effect, not its exact boundaries; Maris & Oostenveld, 2007)
- Using too few permutations (< **1000**) -- p-values become imprecise (Ernst, 2004)
- Applying cluster tests to between-subjects designs without accounting for group structure
- Reporting "no significant clusters" as evidence of no effect (absence of evidence is not evidence of absence; use Bayesian alternatives for null support)

---

## Recipe 6: fMRI Whole-Brain Analysis

### When to Use
- Task-based fMRI with contrasts between conditions
- No strong a priori ROI (exploratory)

### Correction Approaches

| Method | When | Threshold | Source |
|--------|------|-----------|--------|
| Cluster-level FWE | Default for most task fMRI | Cluster-forming: **p < 0.001** (uncorrected); cluster-level: **p < 0.05** (FWE) | Eklund et al., 2016 |
| Voxel-level FWE | Conservative; when precise localization needed | **p < 0.05** (FWE) per voxel | Worsley et al., 1996 |
| Voxel-level FDR | When many true positives expected | **q < 0.05** | Genovese et al., 2002 |
| TFCE | Threshold-free alternative | Permutation-based, **p < 0.05** (FWER) | Smith & Nichols, 2009 |

### Code Pattern (nilearn + SPM-style)

```python
from nilearn.glm.second_level import SecondLevelModel
from nilearn.glm import threshold_stats_img

# Fit group-level model
second_level = SecondLevelModel()
second_level.fit(contrast_images, design_matrix=design)

z_map = second_level.compute_contrast(output_type='z_score')

# Cluster-level FWE correction
# cluster-forming threshold: z = 3.1 (~p < 0.001; Eklund et al., 2016)
thresholded_map, threshold = threshold_stats_img(
 z_map,
 alpha=0.05, # Cluster-level alpha
 height_control='fpr', # False positive rate for cluster forming
 cluster_threshold=10, # Minimum cluster size in voxels
 two_sided=True
)
```

### What to Report
- Software, version, and analysis pipeline
- Cluster-forming threshold (voxel-level p-value)
- Cluster-level correction method (FWE, FDR, TFCE)
- For each significant cluster: peak coordinates (MNI), cluster size (voxels and mm3), peak Z/T statistic, anatomical label
- Smoothing kernel FWHM (typically **6-8 mm** for single-subject, **8 mm** for group; Mikl et al., 2008)

### Common Pitfalls
- Using cluster-forming threshold of **p < 0.01** (inflates false positives to ~70%; Eklund et al., 2016)
- Not reporting unthresholded statistical maps (share on NeuroVault for transparency; Gorgolewski et al., 2015)
- Performing ROI analysis after seeing whole-brain results (double-dipping; Kriegeskorte et al., 2009)
- Using non-parametric methods with too few subjects (permutation tests require minimum **20** subjects for stable results; Winkler et al., 2014)

---

## Recipe 7: Correlation Analysis with Proper Inference

### When to Use
- Testing association between two continuous variables (e.g., behavioral measure and neural measure)
- Individual differences analysis

### Recommended Approach: Bootstrap CI

```r
library(boot)

# Bootstrap correlation with 10,000 resamples (Efron & Tibshirani, 1993)
boot_cor <- function(data, indices) {
 cor(data[indices, 1], data[indices, 2])
}

results <- boot(data = d[, c("measure1", "measure2")],
 statistic = boot_cor,
 R = 10000)

# 95% BCa CI (bias-corrected and accelerated; best bootstrap CI method)
boot.ci(results, type = "bca")
```

### Python Code Pattern

```python
import numpy as np
from scipy import stats

# Pearson correlation with bootstrap CI
r, p = stats.pearsonr(d['measure1'], d['measure2'])

# Bootstrap 95% CI (10,000 resamples; Efron & Tibshirani, 1993)
n_boot = 10000
boot_rs = np.array([
 np.corrcoef(
 np.random.choice(d['measure1'], size=len(d), replace=True),
 np.random.choice(d['measure2'], size=len(d), replace=True)
 )[0, 1] # Note: this is a naive bootstrap; use paired resampling below
 for _ in range(n_boot)
])

# Correct paired bootstrap (resample cases, not variables independently)
boot_rs = np.array([
 np.corrcoef(d.iloc[idx]['measure1'], d.iloc[idx]['measure2'])[0, 1]
 for idx in [np.random.choice(len(d), size=len(d), replace=True)
 for _ in range(n_boot)]
])

ci_lower, ci_upper = np.percentile(boot_rs, [2.5, 97.5])
```

### What to Report
- r value, exact p-value, 95% CI (bootstrap BCa preferred)
- Sample size
- Scatterplot with regression line and CI band
- Consider Spearman's rho if normality is violated or outliers are present

### Common Pitfalls
- Reporting only r and p without CI (a "significant" r = 0.30 at N = 50 has CI [0.02, 0.53]; Cumming, 2014)
- Not checking for influential observations (use Cook's distance; threshold > **4/N**; Cook, 1977)
- Correlating averaged neural measures with averaged behavioral measures without accounting for reliability (Vul et al., 2009)
- Computing brain-behavior correlations with N < **100** (likely underpowered; Marek et al., 2022)

---

## Recipe 8: Mediation Analysis

### When to Use
- Testing whether variable M mediates the effect of X on Y
- Common in cognitive science: does attention (M) mediate the effect of reward (X) on memory (Y)?

### Recommended Approach: Bootstrap Mediation (Preacher & Hayes, 2008)

Sobel's test assumes normality of the indirect effect, which is rarely met. Use bootstrap instead.

### R Code Pattern

```r
library(mediation)

# Step 1: Mediator model
med_model <- lm(M ~ X + covariates, data = d)

# Step 2: Outcome model
out_model <- lm(Y ~ X + M + covariates, data = d)

# Step 3: Bootstrap mediation (Preacher & Hayes, 2008)
med_result <- mediate(med_model, out_model,
 treat = "X", mediator = "M",
 boot = TRUE,
 sims = 5000) # 5000 bootstrap samples (Preacher & Hayes, 2008)
summary(med_result)
```

### Python Code Pattern

```python
# Using pingouin for simple mediation
import pingouin as pg

result = pg.mediation_analysis(data=d, x='X', m='M', y='Y',
 n_boot=5000, # Preacher & Hayes, 2008
 seed=42)
print(result)
```

### What to Report
- Path coefficients: a (X -> M), b (M -> Y), c (total X -> Y), c' (direct X -> Y)
- Indirect effect (a * b) with bootstrap 95% CI
- If CI for indirect effect excludes zero, mediation is supported
- Proportion mediated (indirect / total effect; but interpret with caution for small effects)
- Number of bootstrap samples

### Common Pitfalls
- Using Sobel's test instead of bootstrap (violates normality assumption; MacKinnon et al., 2004)
- Claiming causal mediation from cross-sectional data (mediation implies temporal ordering; Bullock et al., 2010)
- Not reporting the direct effect (c') alongside the indirect effect
- Ignoring that mediation with small samples (N < **100**) has very low power (Fritz & MacKinnon, 2007)

---

## References

- Barr, D. J., et al. (2013). Random effects structure for confirmatory hypothesis testing. *Journal of Memory and Language*, 68(3), 255-278.
- Bullock, J. G., Green, D. P., & Ha, S. E. (2010). Yes, but what's the mechanism? *Journal of Personality and Social Psychology*, 98(4), 550-558.
- Cook, R. D. (1977). Detection of influential observation in linear regression. *Technometrics*, 19(1), 15-18.
- Cumming, G. (2014). The new statistics. *Psychological Science*, 25(1), 7-29.
- Dixon, P. (2008). Models of accuracy in repeated-measures designs. *Journal of Memory and Language*, 59(4), 447-456.
- Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman and Hall.
- Eklund, A., et al. (2016). Cluster failure. *PNAS*, 113(28), 7900-7905.
- Ernst, M. D. (2004). Permutation methods: A basis for exact inference. *Statistical Science*, 19(4), 676-685.
- Fritz, M. S., & MacKinnon, D. P. (2007). Required sample size to detect the mediated effect. *Psychological Science*, 18(3), 233-239.
- Genovese, C. R., et al. (2002). Thresholding of statistical maps in functional neuroimaging using the false discovery rate. *NeuroImage*, 15(4), 870-878.
- Gorgolewski, K. J., et al. (2015). NeuroVault.org: A web-based repository for collecting and sharing unthresholded statistical maps. *Frontiers in Neuroinformatics*, 9, 8.
- Heinze, G., & Schemper, M. (2002). A solution to the problem of separation in logistic regression. *Statistics in Medicine*, 21(16), 2409-2419.
- Jaeger, T. F. (2008). Categorical data analysis. *Journal of Memory and Language*, 59(4), 434-446.
- Kriegeskorte, N., et al. (2009). Circular analysis in systems neuroscience. *Nature Neuroscience*, 12(5), 535-540.
- Langsrud, O. (2003). ANOVA for unbalanced data: Use Type II instead of Type III sums of squares. *Statistics and Computing*, 13(2), 163-167.
- Lo, S., & Andrews, S. (2015). To transform or not to transform. *Frontiers in Psychology*, 6, 1171.
- Luke, S. G. (2017). Evaluating significance in linear mixed-effects models in R. *Behavior Research Methods*, 49(4), 1494-1502.
- MacKinnon, D. P., et al. (2004). Confidence limits for the indirect effect. *Multivariate Behavioral Research*, 39(1), 99-128.
- Marek, S., et al. (2022). Reproducible brain-wide association studies require thousands of individuals. *Nature*, 603, 654-660.
- Maris, E., & Oostenveld, R. (2007). Nonparametric statistical testing of EEG- and MEG-data. *Journal of Neuroscience Methods*, 164(1), 177-190.
- Mikl, M., et al. (2008). Effects of spatial smoothing on fMRI group inferences. *Magnetic Resonance Imaging*, 26(4), 490-503.
- Preacher, K. J., & Hayes, A. F. (2008). Asymptotic and resampling strategies for assessing and comparing indirect effects. *Behavior Research Methods*, 40(3), 879-891.
- Ratcliff, R. (1993). Methods for dealing with reaction time outliers. *Psychological Bulletin*, 114(3), 510-532.
- Richardson, J. T. E. (2011). Eta squared and partial eta squared. *Educational Research Review*, 6(2), 135-147.
- Rights, J. D., & Sterba, S. K. (2019). Quantifying explained variance in multilevel models. *Journal of Educational and Behavioral Statistics*, 44(2), 223-263.
- Schielzeth, H. (2010). Simple means to improve the interpretability of regression coefficients. *Methods in Ecology and Evolution*, 1(2), 103-113.
- Smith, S. M., & Nichols, T. E. (2009). Threshold-free cluster enhancement. *NeuroImage*, 44(1), 83-98.
- Steiger, J. H. (2004). Beyond the F test: Effect size confidence intervals. *Psychological Methods*, 9(2), 164-182.
- Van Selst, M., & Jolicoeur, P. (1994). A solution to the effect of sample size on outlier elimination. *QJEP*, 47A(3), 631-650.
- Warton, D. I., & Hui, F. K. C. (2011). The arcsine is asinine. *Ecology*, 92(1), 3-10.
- Whelan, R. (2008). Effective analysis of reaction time data. *The Psychological Record*, 58(3), 475-482.
- Winkler, A. M., et al. (2014). Permutation inference for the general linear model. *NeuroImage*, 92, 381-397.
- Worsley, K. J., et al. (1996). A unified statistical approach. *Human Brain Mapping*, 4(1), 58-73.
