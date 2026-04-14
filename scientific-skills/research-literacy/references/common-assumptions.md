# Common Statistical and Analytical Assumptions in Cognitive Science

This reference table covers the key assumptions, diagnostic checks, and remedies for statistical methods commonly used in cognitive science and neuroscience research. Every numerical parameter or recommendation includes a citation.

---

## Comparison Methods

### Independent-Samples t-Test

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Independence of observations | Design review: no nesting or clustering | Use mixed-effects model or clustered SE | (Scariano & Davenport, 1987) |
| Normality of sampling distribution | Shapiro-Wilk test; Q-Q plot; with N > **30** per group, CLT provides robustness | Use Welch's t-test (robust to non-normality with moderate N) or Mann-Whitney U | (Lumley et al., 2002) |
| Homogeneity of variance | Levene's test (p < .05 suggests violation) | Use Welch's t-test (does not assume equal variances) | (Delacre et al., 2017) |

**Recommendation**: Default to Welch's t-test rather than Student's t-test. Welch's test performs well even when assumptions are met and is strictly better when they are not (Delacre et al., 2017, *International Review of Social Psychology*, 30(1), 92-101).

### Paired-Samples t-Test

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Independence of difference scores | Design review: each participant contributes one difference score | Use mixed-effects model for repeated observations | (Judd et al., 2012) |
| Normality of difference scores | Shapiro-Wilk on difference scores; Q-Q plot | Use Wilcoxon signed-rank test or permutation test | (Zimmerman, 1997) |

### One-Way ANOVA

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Independence | Design review | Use mixed-effects model | (Kenny & Judd, 1986) |
| Normality within groups | Shapiro-Wilk per group; residual Q-Q plot | Welch's ANOVA or Kruskal-Wallis | (Lix et al., 1996) |
| Homogeneity of variance | Levene's test | Welch's ANOVA (does not assume equal variances) | (Delacre et al., 2019) |

### Repeated-Measures ANOVA

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Sphericity (equal variances of differences between all pairs of conditions) | Mauchly's test of sphericity | Apply Greenhouse-Geisser correction (epsilon < **0.75**) or Huynh-Feldt correction (epsilon >= **0.75**) | (Girden, 1992; Oberfeld & Franke, 2013) |
| Normality | Shapiro-Wilk on residuals | Robust ANOVA (e.g., trimmed means) or permutation test | (Keselman et al., 2003) |
| No carryover/order effects | Counterbalancing check; test for order effects | Include order as a factor or use Latin square design | (Keppel & Wickens, 2004) |

**Note**: The Greenhouse-Geisser epsilon ranges from **1/(k-1)** (maximum violation) to **1.0** (perfect sphericity), where k is the number of conditions (Greenhouse & Geisser, 1959, *Psychometrika*, 24(2), 95-112).

---

## Association and Regression Methods

### Pearson Correlation

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Linear relationship | Scatterplot inspection | Use Spearman rank correlation or polynomial regression | (Anscombe, 1973) |
| Bivariate normality | Shapiro-Wilk on each variable; Mardia's test | Use Spearman or Kendall correlation | (Puth et al., 2014) |
| No extreme outliers | Scatterplot; Cook's distance > **4/N** flags influential points | Use robust correlation (e.g., percentage-bend, Winsorized) | (Wilcox, 2012) |
| Independence | Design review | Use multilevel correlation for clustered data | (Bland & Altman, 1995) |

### Linear Regression (OLS)

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Linearity | Residual vs. fitted plot (should show no pattern) | Add polynomial terms, use GAM, or transform variables | (Fox, 2015) |
| Normality of residuals | Q-Q plot of residuals; Shapiro-Wilk | Use robust standard errors (HC3 recommended) or bootstrap | (Long & Ervin, 2000) |
| Homoscedasticity | Residual vs. fitted plot; Breusch-Pagan test | Use heteroscedasticity-consistent SE (HC3); weighted least squares | (Hayes & Cai, 2007) |
| Independence of residuals | Durbin-Watson test for temporal autocorrelation (values near **2.0** indicate no autocorrelation; < **1.5** or > **2.5** are concerning) | Use GLS or include autoregressive terms | (Durbin & Watson, 1951) |
| No multicollinearity | Variance Inflation Factor: VIF > **5** is concerning, VIF > **10** is severe | Remove or combine correlated predictors; use ridge regression or PCA | (Alin, 2010) |
| No influential outliers | Cook's distance > **4/N**; leverage > **2(p+1)/N** | Investigate outliers; use robust regression (M-estimation) | (Cook, 1977) |

### Logistic Regression

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Binary or ordinal outcome | Data inspection | Use appropriate link function (multinomial, ordinal) | (Agresti, 2002) |
| Linearity of logit | Box-Tidwell test; plot log-odds vs. continuous predictors | Add polynomial terms or categorize predictor | (Hosmer et al., 2013) |
| No multicollinearity | VIF > **5** is concerning | Same as linear regression | (Alin, 2010) |
| Sufficient events per predictor | Minimum **10** events per predictor variable (relaxed from older rule of **20**) | Reduce predictors; use penalized regression (Firth) | (Vittinghoff & McCulloch, 2007) |
| Independence | Design review | Use GEE or mixed-effects logistic regression | (Zeger & Liang, 1986) |

---

## Mixed-Effects (Multilevel) Models

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Conditional normality of residuals | Q-Q plots of level-1 and level-2 residuals | Use robust mixed models or generalized linear mixed models | (Schielzeth et al., 2020) |
| Correct random effects structure | Likelihood ratio tests; check for singular fit (boundary estimates at zero) | Simplify random structure: remove correlations first, then random slopes | (Barr et al., 2013) |
| Linearity (for continuous predictors) | Residual plots; component-plus-residual plots | Add splines or polynomial terms | (Bates et al., 2015) |
| Homoscedasticity of residuals | Plot residuals vs. fitted; residuals per group | Model heterogeneous variances (e.g., `weights` in `nlme`) | (Pinheiro & Bates, 2000) |
| No complete separation | Check for infinite coefficient estimates | Use penalized estimation or Bayesian priors | (Gelman et al., 2008) |

**Guidance on random effects**: Start with the maximal random effects structure justified by the design (Barr et al., 2013, *Journal of Memory and Language*, 68(3), 255-278). If the model fails to converge or produces singular fits, simplify by removing correlation parameters first, then the smallest variance components. Document each simplification step.

---

## Categorical Data Methods

### Chi-Square Test of Independence

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Expected cell frequencies >= **5** | Compute expected counts from marginals | Use Fisher's exact test (for 2x2) or Monte Carlo simulation | (Agresti, 2002) |
| Independence of observations | Each participant contributes to only one cell | Use McNemar's test (paired data) or GEE | (Siegel & Castellan, 1988) |
| Random sampling | Study design review | Acknowledge limitation | (Agresti, 2002) |

### Fisher's Exact Test

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Fixed marginals (conservative) | By design | Use mid-p correction for less conservative inference | (Lydersen et al., 2009) |
| Independence | Design review | Use exact conditional tests for matched data | (Agresti, 2002) |

---

## Time-Series and Neuroimaging Methods

### EEG/ERP Cluster-Based Permutation Tests

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Exchangeability under H0 (observations are interchangeable across conditions under the null) | Design must permit valid permutation: within-subjects designs permute condition labels within participants | Restrict permutations to valid exchanges; stratified permutation for between-subjects designs | (Maris & Oostenveld, 2007) |
| Sufficient number of permutations | With N participants, maximum **2^N** permutations for paired designs | Use Monte Carlo approximation with >= **1000** permutations (>= **5000** for publication) | (Ernst, 2004; Phipson & Smyth, 2010) |
| Cluster-forming threshold is appropriate | Sensitivity analysis: vary the threshold (e.g., p < **0.05**, **0.01**, **0.001** uncorrected) | Report results across multiple thresholds; note that test controls FWER for clusters, not individual time points | (Sassenhagen & Draschkow, 2019) |

**Important caveat**: Cluster-based permutation tests control the family-wise error rate for the existence of a cluster, but do not provide precise spatial or temporal localization of the effect. Do not interpret cluster boundaries as onset/offset times (Sassenhagen & Draschkow, 2019, *Psychophysiology*, 56(6), e13335).

### fMRI General Linear Model (GLM)

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Gaussian distributed noise | Residual normality plots per voxel (spot-check) | Use nonparametric permutation testing | (Nichols & Holmes, 2002) |
| Correct hemodynamic response function (HRF) | Compare canonical HRF fits with flexible models (FIR, FLOBS) | Use FIR basis set or add temporal/dispersion derivatives | (Lindquist et al., 2009) |
| Temporal stationarity | Check for scanner drift, motion spikes | Include high-pass filter (cutoff typically **1/128 Hz**, i.e., **128 s**; SPM default) and motion regressors | (Friston et al., 2000) |
| Temporal autocorrelation | Inspect residual autocorrelation function; Durbin-Watson statistic | Apply AR(1) prewhitening (SPM) or FILM prewhitening (FSL) | (Woolrich et al., 2001) |
| No excessive head motion | Compute framewise displacement (FD); threshold typically **0.5 mm** for task fMRI (Power et al., 2012) | Scrub high-motion volumes or include FD as nuisance regressor; exclude participants with > **20%** scrubbed volumes | (Power et al., 2012, *NeuroImage*, 59(3), 2142-2154) |
| Correct multiple comparisons | Track number of voxels/ROIs tested | Use cluster-level FWE (with cluster-forming threshold p < **0.001** uncorrected; Eklund et al., 2016), voxel-level FWE, or FDR | (Eklund et al., 2016, *PNAS*, 113(28), 7900-7905) |

**Critical note on cluster-forming thresholds**: Using a lenient cluster-forming threshold (e.g., p < **0.01** uncorrected) inflates false positive rates to as high as **70%** for cluster-level inference. A threshold of p < **0.001** uncorrected is recommended (Eklund et al., 2016).

### fMRI Functional Connectivity

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Stationarity of connectivity | Sliding-window analysis; test for time-varying connectivity | Use dynamic connectivity methods (DCC, sliding window with appropriate window length >= **30 s**) | (Hutchison et al., 2013) |
| No motion confound | Check FD-FC correlation: correlation between framewise displacement and functional connectivity | Use GSR, CompCor, ICA-AROMA, or scrubbing | (Power et al., 2012) |
| Appropriate parcellation | Compare results across atlases | Report results with multiple parcellation schemes | (Eickhoff et al., 2018) |

---

## Multivariate Pattern Analysis (MVPA) / Decoding

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Independent training and test sets (no double dipping) | Verify cross-validation scheme: training and test data must be fully independent | Use leave-one-run-out CV for fMRI; never use the same data for feature selection and testing | (Kriegeskorte et al., 2009) |
| Sufficient number of cross-validation folds | With k runs, use k-fold leave-one-run-out | If few runs, use leave-one-trial-out with caution (temporal autocorrelation risk) | (Varoquaux et al., 2017) |
| Appropriate chance level | Theoretical chance for balanced classes = **1/k** for k classes; but empirical chance may differ with imbalanced classes | Use permutation-based null distribution (>= **1000** permutations) rather than theoretical chance | (Combrisson & Jerbi, 2015) |
| No information leakage across folds | Check preprocessing pipeline: any step using statistics from the full dataset before splitting leaks information | Apply all data-dependent preprocessing (e.g., feature selection, normalization) within each fold | (Kriegeskorte et al., 2009, *Nature Neuroscience*, 12, 535-540) |

---

## Representational Similarity Analysis (RSA)

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Appropriate distance metric | Compare Euclidean, correlation distance, Mahalanobis (cross-validated) | Use crossnobis (cross-validated Mahalanobis) to reduce noise bias | (Walther et al., 2016) |
| Independence of RDM entries | RDM entries are not independent (they share conditions) | Use permutation test or bootstrap on conditions (not RDM cells) for inference | (Nili et al., 2014) |
| Model RDMs are meaningful | Correlate model RDMs with each other to check redundancy | Use partial correlation or variance partitioning for correlated models | (Nili et al., 2014, *PLOS Computational Biology*, 10(11), e1003553) |

---

## Bayesian Analysis

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Prior specification is appropriate | Prior predictive check: simulate data from priors and verify plausibility | Report results under multiple priors (sensitivity analysis); use weakly informative priors as default | (Schad et al., 2021) |
| Model is correctly specified | Posterior predictive check: compare observed data to data simulated from the posterior | Revise model specification; consider model comparison (LOO-CV, WAIC) | (Gelman et al., 2013) |
| MCMC convergence (for sampling-based methods) | R-hat < **1.01** for all parameters; effective sample size > **400** per chain; trace plots show mixing | Increase iterations; reparameterize model; use non-centered parameterization for hierarchical models | (Vehtari et al., 2021) |
| No divergent transitions (HMC/NUTS) | Check sampler diagnostics: **0** divergences is the target | Increase `adapt_delta` (e.g., to **0.95** or **0.99**); reparameterize | (Betancourt, 2017) |

**Interpreting Bayes factors**: BF10 > **3** provides moderate evidence for H1; BF10 > **10** provides strong evidence (Jeffreys, 1961, *Theory of Probability*, 3rd ed.). BF01 > **3** provides moderate evidence for H0. Values between **1/3** and **3** are inconclusive (Dienes, 2014, *Frontiers in Psychology*, 5, 781).

---

## Factor Analysis and Dimensionality Reduction

### Exploratory Factor Analysis (EFA)

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Sufficient sample size | Kaiser-Meyer-Olkin (KMO) >= **0.60**; minimum N:p ratio of **5:1** (better: **10:1**) | Collect more data; reduce number of variables | (Mundfrom et al., 2005) |
| Adequate correlations | Bartlett's test of sphericity (p < .05); KMO >= **0.60** | If variables are uncorrelated, factor analysis is not appropriate | (Tabachnick & Fidell, 2013) |
| Multivariate normality (for ML estimation) | Mardia's test | Use principal axis factoring (does not assume normality) | (Fabrigar et al., 1999) |
| Correct number of factors | Parallel analysis (preferred); scree plot; eigenvalues > **1** rule (unreliable alone) | Use parallel analysis as primary criterion; compare multiple methods | (Horn, 1965; Velicer et al., 2000) |

### Independent Component Analysis (ICA)

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Statistical independence of sources | ICA assumes non-Gaussian independent sources; check by mutual information | If sources are Gaussian, ICA cannot separate them (use PCA instead) | (Hyvarinen & Oja, 2000) |
| Correct number of components | Dimensionality estimation (e.g., MDL, BIC, PCA eigenvalue spectrum) | Use information-theoretic criteria; for fMRI, MELODIC automatic estimation or fixed dimensionality with justification | (Li et al., 2007) |
| Linear mixing | Assumed by standard ICA | Use kernel ICA or nonlinear ICA variants | (Hyvarinen & Oja, 2000, *Neural Networks*, 13(4-5), 411-430) |

---

## Survival / Time-to-Event Analysis

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Proportional hazards (Cox model) | Schoenfeld residuals test; log-log survival plot (parallel lines = OK) | Use stratified Cox model, time-varying coefficients, or accelerated failure time model | (Grambsch & Therneau, 1994) |
| Non-informative censoring | Design review: is dropout related to the outcome? | Use joint models or sensitivity analyses for informative censoring | (Leung et al., 1997) |
| Correct functional form (continuous predictors) | Martingale residual plots | Use splines or categorize predictor | (Therneau & Grambsch, 2000) |

**Cognitive science application**: Survival analysis is used in psycholinguistics for response time modeling and in clinical neuropsychology for time-to-event outcomes (e.g., time to conversion from MCI to dementia). In RT analysis, the proportional hazards assumption means the ratio of "finishing rates" is constant over time, which may not hold if experimental conditions affect fast and slow responses differently (Baayen & Milin, 2010).

---

## Signal Detection Theory (SDT)

| Assumption | How to Check | What to Do If Violated | Citation |
|---|---|---|---|
| Equal-variance Gaussian distributions | Compare z(hit rate) vs. z(false alarm rate) across criteria; ROC slope = **1.0** indicates equal variance | Use unequal-variance SDT (estimate separate d' and sigma ratio) | (Macmillan & Creelman, 2005) |
| Independence of trials | Design review; check for sequential dependencies | Use GLMMs with trial-level data and autoregressive terms | (DeCarlo, 1998) |
| No response bias confound | Check criterion (c) separately from sensitivity (d') | Report both d' and c (or beta); criterion shifts do not invalidate d' under SDT assumptions | (Macmillan & Creelman, 2005, *Detection Theory: A User's Guide*, 2nd ed.) |
| Sufficient trial counts | Minimum **20** trials per condition for stable d' estimates; **50+** preferred | Increase trial count; use hierarchical SDT for low trial counts | (Hautus, 1995) |

---

## Multiple Comparisons Reference

| Method | Controls | When to Use | Key Parameter | Citation |
|---|---|---|---|---|
| Bonferroni | Family-wise error rate (FWER) | Few planned comparisons; need strict control | alpha / N comparisons | (Dunn, 1961) |
| Holm-Bonferroni | FWER | Same as Bonferroni but uniformly more powerful | Step-down procedure | (Holm, 1979) |
| Benjamini-Hochberg | False discovery rate (FDR) | Many comparisons; some false positives acceptable | q-value threshold (typically **0.05**) | (Benjamini & Hochberg, 1995) |
| Cluster permutation | FWER (cluster-level) | High-dimensional EEG/MEG data | Cluster-forming threshold; N permutations | (Maris & Oostenveld, 2007) |
| Threshold-free cluster enhancement (TFCE) | FWER | fMRI, EEG; avoids arbitrary cluster-forming threshold | H and E parameters (defaults: H = **2**, E = **0.5** for fMRI) | (Smith & Nichols, 2009) |
| Tukey HSD | FWER (all pairwise) | All pairwise comparisons after ANOVA | Studentized range distribution | (Tukey, 1949) |
| Permutation FWE | FWER (voxel or cluster) | fMRI whole-brain analysis; makes fewer assumptions | N permutations >= **5000** | (Nichols & Holmes, 2002) |

**Guidance**: Default to Holm-Bonferroni over Bonferroni (it is strictly more powerful with the same FWER control; Holm, 1979). Use FDR when testing many hypotheses where controlling the proportion of false discoveries is more relevant than controlling any single false positive. Use cluster-based or TFCE methods for spatiotemporal neuroimaging data.

---

## References

- Agresti, A. (2002). *Categorical data analysis* (2nd ed.). Wiley.
- Alin, A. (2010). Multicollinearity. *WIREs Computational Statistics*, 2(3), 370-374.
- Anscombe, F. J. (1973). Graphs in statistical analysis. *American Statistician*, 27(1), 17-21.
- Baayen, R. H., & Milin, P. (2010). Analyzing reaction times. *International Journal of Psychological Research*, 3(2), 12-28.
- Barr, D. J., Levy, R., Scheepers, C., & Tily, H. J. (2013). Random effects structure for confirmatory hypothesis testing: Keep it maximal. *Journal of Memory and Language*, 68(3), 255-278.
- Bates, D., Machler, M., Bolker, B., & Walker, S. (2015). Fitting linear mixed-effects models using lme4. *Journal of Statistical Software*, 67(1), 1-48.
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate. *Journal of the Royal Statistical Society: Series B*, 57(1), 289-300.
- Betancourt, M. (2017). A conceptual introduction to Hamiltonian Monte Carlo. *arXiv preprint*, arXiv:1701.02434.
- Bland, J. M., & Altman, D. G. (1995). Calculating correlation coefficients with repeated observations. *BMJ*, 310(6980), 633.
- Button, K. S., et al. (2013). Power failure: Why small sample size undermines the reliability of neuroscience. *Nature Reviews Neuroscience*, 14(5), 365-376.
- Combrisson, E., & Jerbi, K. (2015). Exceeding chance level by chance. *NeuroImage*, 118, 499-513.
- Cook, R. D. (1977). Detection of influential observations in linear regression. *Technometrics*, 19(1), 15-18.
- DeCarlo, L. T. (1998). Signal detection theory and generalized linear models. *Psychological Methods*, 3(2), 186-205.
- Delacre, M., Lakens, D., & Leys, C. (2017). Why psychologists should by default use Welch's t-test. *International Review of Social Psychology*, 30(1), 92-101.
- Delacre, M., Leys, C., Mora, Y. L., & Lakens, D. (2019). Taking parametric assumptions seriously. *PLoS ONE*, 14(4), e0220527.
- Dienes, Z. (2014). Using Bayes to get the most out of non-significant results. *Frontiers in Psychology*, 5, 781.
- Dunn, O. J. (1961). Multiple comparisons among means. *Journal of the American Statistical Association*, 56(293), 52-64.
- Durbin, J., & Watson, G. S. (1951). Testing for serial correlation in least squares regression. *Biometrika*, 38(1/2), 159-177.
- Eickhoff, S. B., et al. (2018). Imaging-based parcellations of the human brain. *Nature Reviews Neuroscience*, 19(11), 672-686.
- Eklund, A., Nichols, T. E., & Knutsson, H. (2016). Cluster failure: Why fMRI inferences for spatial extent have inflated false-positive rates. *PNAS*, 113(28), 7900-7905.
- Ernst, M. D. (2004). Permutation methods: A basis for exact inference. *Statistical Science*, 19(4), 676-685.
- Fabrigar, L. R., Wegener, D. T., MacCallum, R. C., & Strahan, E. J. (1999). Evaluating the use of exploratory factor analysis in psychological research. *Psychological Methods*, 4(3), 272-299.
- Fox, J. (2015). *Applied regression analysis and generalized linear models* (3rd ed.). Sage.
- Friston, K. J., et al. (2000). To smooth or not to smooth? Bias and efficiency in fMRI time-series analysis. *NeuroImage*, 12(2), 196-208.
- Gelman, A., et al. (2008). A weakly informative default prior distribution for logistic and other regression models. *Annals of Applied Statistics*, 2(4), 1360-1383.
- Gelman, A., et al. (2013). *Bayesian data analysis* (3rd ed.). Chapman and Hall/CRC.
- Girden, E. R. (1992). *ANOVA: Repeated measures*. Sage.
- Grambsch, P. M., & Therneau, T. M. (1994). Proportional hazards tests and diagnostics based on weighted residuals. *Biometrika*, 81(3), 515-526.
- Greenhouse, S. W., & Geisser, S. (1959). On methods in the analysis of profile data. *Psychometrika*, 24(2), 95-112.
- Hautus, M. J. (1995). Corrections for extreme proportions and their biasing effects on estimated values of d'. *Behavior Research Methods, Instruments, & Computers*, 27(1), 46-51.
- Hayes, A. F., & Cai, L. (2007). Using heteroscedasticity-consistent standard error estimators in OLS regression. *Behavior Research Methods*, 39(4), 709-722.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65-70.
- Horn, J. L. (1965). A rationale and test for the number of factors in factor analysis. *Psychometrika*, 30(2), 179-185.
- Hosmer, D. W., Lemeshow, S., & Sturdivant, R. X. (2013). *Applied logistic regression* (3rd ed.). Wiley.
- Hutchison, R. M., et al. (2013). Dynamic functional connectivity: Promise, issues, and interpretations. *NeuroImage*, 80, 360-378.
- Hyvarinen, A., & Oja, E. (2000). Independent component analysis: Algorithms and applications. *Neural Networks*, 13(4-5), 411-430.
- Jeffreys, H. (1961). *Theory of probability* (3rd ed.). Oxford University Press.
- Judd, C. M., Westfall, J., & Kenny, D. A. (2012). Treating stimuli as a random factor in social psychology. *Journal of Personality and Social Psychology*, 103(1), 54-69.
- Kenny, D. A., & Judd, C. M. (1986). Consequences of violating the independence assumption in analysis of variance. *Psychological Bulletin*, 99(3), 422-431.
- Keppel, G., & Wickens, T. D. (2004). *Design and analysis: A researcher's handbook* (4th ed.). Pearson.
- Keselman, H. J., Algina, J., & Kowalchuk, R. K. (2003). A comparison of data analysis strategies for testing omnibus effects in higher-order repeated measures designs. *Multivariate Behavioral Research*, 38(1), 1-30.
- Kriegeskorte, N., Simmons, W. K., Bellgowan, P. S. F., & Baker, C. I. (2009). Circular analysis in systems neuroscience: The dangers of double dipping. *Nature Neuroscience*, 12, 535-540.
- Leung, K. M., Elashoff, R. M., & Afifi, A. A. (1997). Censoring issues in survival analysis. *Annual Review of Public Health*, 18, 83-104.
- Li, Y. O., Adali, T., & Calhoun, V. D. (2007). Estimating the number of independent components for functional magnetic resonance imaging data. *Human Brain Mapping*, 28(11), 1251-1266.
- Lindquist, M. A., Meng Loh, J., Atlas, L. Y., & Wager, T. D. (2009). Modeling the hemodynamic response function in fMRI. *NeuroImage*, 45(1 Suppl), S187-S198.
- Lix, L. M., Keselman, J. C., & Keselman, H. J. (1996). Consequences of assumption violations revisited. *Review of Educational Research*, 66(4), 579-619.
- Long, J. S., & Ervin, L. H. (2000). Using heteroscedasticity consistent standard errors in the linear regression model. *American Statistician*, 54(3), 217-224.
- Lumley, T., Diehr, P., Emerson, S., & Chen, L. (2002). The importance of the normality assumption in large public health data sets. *Annual Review of Public Health*, 23, 151-169.
- Lydersen, S., Fagerland, M. W., & Laake, P. (2009). Recommended tests for association in 2x2 tables. *Statistics in Medicine*, 28(7), 1159-1175.
- Macmillan, N. A., & Creelman, C. D. (2005). *Detection theory: A user's guide* (2nd ed.). Erlbaum.
- Maris, E., & Oostenveld, R. (2007). Nonparametric statistical testing of EEG- and MEG-data. *Journal of Neuroscience Methods*, 164(1), 177-190.
- Mundfrom, D. J., Shaw, D. G., & Ke, T. L. (2005). Minimum sample size recommendations for conducting factor analyses. *International Journal of Testing*, 5(2), 159-168.
- Nichols, T. E., & Holmes, A. P. (2002). Nonparametric permutation tests for functional neuroimaging. *Human Brain Mapping*, 15(1), 1-25.
- Nili, H., et al. (2014). A toolbox for representational similarity analysis. *PLOS Computational Biology*, 10(11), e1003553.
- Oberfeld, D., & Franke, T. (2013). Evaluating the robustness of repeated measures analyses: The case of small sample sizes and nonnormal data. *Behavior Research Methods*, 45(3), 792-812.
- Phipson, B., & Smyth, G. K. (2010). Permutation P-values should never be zero. *Statistical Applications in Genetics and Molecular Biology*, 9(1), Article 39.
- Pinheiro, J. C., & Bates, D. M. (2000). *Mixed-effects models in S and S-PLUS*. Springer.
- Power, J. D., Barnes, K. A., Snyder, A. Z., Schlaggar, B. L., & Petersen, S. E. (2012). Spurious but systematic correlations in functional connectivity MRI networks arise from subject motion. *NeuroImage*, 59(3), 2142-2154.
- Puth, M. T., Neuhauser, M., & Ruxton, G. D. (2014). Effective use of Pearson's product-moment correlation coefficient. *Animal Behaviour*, 93, 183-189.
- Sassenhagen, J., & Draschkow, D. (2019). Cluster-based permutation tests of MEG/EEG data do not establish significance of effect latency or location. *Psychophysiology*, 56(6), e13335.
- Scariano, S. M., & Davenport, J. M. (1987). The effects of violations of independence assumptions in the one-way ANOVA. *American Statistician*, 41(2), 123-129.
- Schad, D. J., Betancourt, M., & Vasishth, S. (2021). Toward a principled Bayesian workflow in cognitive science. *Psychological Methods*, 26(1), 103-126.
- Schielzeth, H., et al. (2020). Robustness of linear mixed-effects models to violations of distributional assumptions. *Methods in Ecology and Evolution*, 11(9), 1141-1152.
- Siegel, S., & Castellan, N. J. (1988). *Nonparametric statistics for the behavioral sciences* (2nd ed.). McGraw-Hill.
- Smith, S. M., & Nichols, T. E. (2009). Threshold-free cluster enhancement. *NeuroImage*, 44(1), 83-98.
- Tabachnick, B. G., & Fidell, L. S. (2013). *Using multivariate statistics* (6th ed.). Pearson.
- Therneau, T. M., & Grambsch, P. M. (2000). *Modeling survival data*. Springer.
- Tukey, J. W. (1949). Comparing individual means in the analysis of variance. *Biometrics*, 5(2), 99-114.
- Varoquaux, G., et al. (2017). Assessing and tuning brain decoders: Cross-validation, caveats, and guidelines. *NeuroImage*, 145, 166-179.
- Vehtari, A., et al. (2021). Rank-normalization, folding, and localization: An improved R-hat for assessing convergence of MCMC. *Bayesian Analysis*, 16(2), 667-718.
- Velicer, W. F., Eaton, C. A., & Fava, J. L. (2000). Construct explication through factor or component analysis. In R. D. Goffin & E. Helmes (Eds.), *Problems and solutions in human assessment*. Kluwer.
- Vittinghoff, E., & McCulloch, C. E. (2007). Relaxing the rule of ten events per variable in logistic and Cox regression. *American Journal of Epidemiology*, 165(6), 710-718.
- Walther, A., et al. (2016). Reliability of dissimilarity measures for multi-voxel pattern analysis. *NeuroImage*, 137, 188-200.
- Wilcox, R. R. (2012). *Introduction to robust estimation and hypothesis testing* (3rd ed.). Academic Press.
- Woolrich, M. W., Ripley, B. D., Brady, J. M., & Smith, S. M. (2001). Temporal autocorrelation in univariate linear modeling of fMRI data. *NeuroImage*, 14(6), 1370-1386.
- Zeger, S. L., & Liang, K. Y. (1986). Longitudinal data analysis for discrete and continuous outcomes. *Biometrics*, 42(1), 121-130.
- Zimmerman, D. W. (1997). A note on interpretation of the paired-samples t test. *Journal of Educational and Behavioral Statistics*, 22(3), 349-360.
