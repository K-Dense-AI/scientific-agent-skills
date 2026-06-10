# Statistical Approaches for ERP Analysis

This reference covers the major statistical methods used in ERP research, including amplitude measurement choices, time window and ROI selection strategies, traditional parametric approaches, and mass univariate / permutation-based methods.

---

## 1. Amplitude Measurement Methods

### Mean Amplitude

| Property | Details | Source |
|----------|---------|--------|
| **Definition** | Average voltage across all time points within the measurement window | Luck, 2014, Ch. 9 |
| **When to use** | Broad components without a sharp peak (N400, P300, LPC, CNV) | Luck, 2014, Ch. 9 |
| **Advantages** | Robust to noise; not biased by trial count; does not require a clear peak | Luck, 2014, Ch. 9 |
| **Disadvantages** | Sensitive to window width; can include non-component activity if the window is too wide | Luck, 2014, Ch. 9 |
| **Recommendation** | **Default choice** for most ERP analyses | Luck, 2014, Ch. 9 |

### Peak Amplitude

| Property | Details | Source |
|----------|---------|--------|
| **Definition** | Maximum (or minimum for negative components) voltage within the measurement window | Luck, 2014, Ch. 9 |
| **When to use** | Sharp, well-defined peaks (P1, N1, N170) | Luck, 2014, Ch. 9 |
| **Advantages** | Intuitive; captures the maximum expression of a component | Luck, 2014, Ch. 9 |
| **Disadvantages** | Biased by noise (noisy data = artificially large peaks); biased by trial count (fewer trials = more noise = larger apparent peak); requires a clear peak to be meaningful | Luck, 2014, Ch. 9 |
| **Bias correction** | Use **local peak** (search within window then average surrounding **+/-25 ms**) rather than absolute maximum | Luck, 2014, Ch. 9 |

### Peak Latency

| Property | Details | Source |
|----------|---------|--------|
| **Definition** | Time point of the maximum (or minimum) voltage within the measurement window | Luck, 2014, Ch. 9 |
| **When to use** | When processing speed is the variable of interest | Luck, 2014, Ch. 9 |
| **Disadvantages** | Very sensitive to noise; a secondary peak or noise spike can shift the measured latency dramatically; **do not use** for components without a clear peak | Luck, 2014, Ch. 9 |
| **Preferred alternative** | **50% fractional area latency** (see below) | Kiesel et al., 2008 |

### 50% Fractional Area Latency

| Property | Details | Source |
|----------|---------|--------|
| **Definition** | The time point that divides the area under the component into two equal halves (50% of the total area on each side) | Kiesel et al., 2008 |
| **When to use** | Whenever latency is of interest; **preferred over peak latency** for nearly all components | Kiesel et al., 2008; Luck, 2014, Ch. 9 |
| **Advantages** | More robust to noise than peak latency; works even when the peak is broad or asymmetric; not biased by amplitude differences between conditions | Kiesel et al., 2008 |
| **Implementation** | Define the measurement window, rectify the waveform if needed, compute cumulative area, find the 50% crossing point | Kiesel et al., 2008 |

### Signed and Unsigned Area

| Property | Details | Source |
|----------|---------|--------|
| **Signed area** | Area between the waveform and zero (or baseline), counting positive and negative areas with their sign | Luck, 2014, Ch. 9 |
| **Unsigned area** | Absolute area regardless of polarity | Luck, 2014, Ch. 9 |
| **When to use** | Signed area: when the component's polarity is meaningful and consistent. Unsigned area: when the component may span both polarities | Luck, 2014, Ch. 9 |

### Decision Guide: Which Measure?

```
Does the component have a clear, sharp peak?
 |
 +-- YES (e.g., P1, N1, N170)
 | |
 | +-- Measuring amplitude? --> Peak amplitude (with local peak averaging)
 | +-- Measuring latency? --> 50% fractional area latency (preferred) or peak latency
 |
 +-- NO (e.g., N400, P300, LPC, CNV)
 |
 +-- Measuring amplitude? --> Mean amplitude (default)
 +-- Measuring latency? --> 50% fractional area latency
```

---

## 2. Time Window and ROI Selection

### Strategy 1: A Priori Selection (Preferred)

| Property | Details | Source |
|----------|---------|--------|
| **Approach** | Select time window and electrode ROI based on prior literature **before** looking at your data | Luck & Gaspelin, 2017 |
| **Example** | "Based on Kutas & Federmeier (2011), we defined the N400 time window as 300-500 ms at electrodes Cz, CPz, Pz, C3, C4, CP3, CP4, P3, P4" | Standard practice |
| **Advantages** | Eliminates double-dipping; fully pre-specifiable in a pre-registration | Luck & Gaspelin, 2017 |
| **Disadvantages** | May miss the true peak if your paradigm differs from the literature; may include time points where the component is not active | Luck & Gaspelin, 2017 |
| **When to use** | When studying a well-characterized component with established windows from prior work | Luck & Gaspelin, 2017 |

### Strategy 2: Collapsed Localizer

| Property | Details | Source |
|----------|---------|--------|
| **Approach** | Average across **all conditions** (collapsing the factor of interest) to identify the component's peak latency and scalp distribution; then measure differences **between conditions** within that window | Luck & Gaspelin, 2017 |
| **Example** | Average all word types to find the N400 peak timing and location, then test semantic congruity differences within that window | Luck & Gaspelin, 2017 |
| **Advantages** | Data-informed but avoids double-dipping (the localizer is orthogonal to the contrast of interest) | Luck & Gaspelin, 2017 |
| **Disadvantages** | Assumes the component peaks at the same time for all conditions (may not hold if latency varies across conditions) | Luck & Gaspelin, 2017 |
| **When to use** | When a priori windows are uncertain or when working with a less-studied paradigm | Luck & Gaspelin, 2017 |

### Strategy 3: Data-Driven (Mass Univariate)

| Property | Details | Source |
|----------|---------|--------|
| **Approach** | Test every time point and electrode, using permutation-based correction for multiple comparisons | Maris & Oostenveld, 2007; Groppe et al., 2011 |
| **Advantages** | No need to pre-select window or ROI; discovers effects wherever they occur | Maris & Oostenveld, 2007 |
| **Disadvantages** | Lower power for specific, targeted hypotheses; cannot spatiotemporally localize effects (for cluster-based tests) | Maris & Oostenveld, 2007 |
| **When to use** | Exploratory analyses; effects with unknown timing/distribution; supplementing a priori analyses | Groppe et al., 2011 |

### The Double-Dipping Problem

**Never** select time windows or electrodes by examining the difference between conditions, then test that same difference in the selected window. This is circular analysis (Kriegeskorte et al., 2009) and inflates Type I error rates well above the nominal alpha level (Luck & Gaspelin, 2017).

**Acceptable**:
- A priori windows from prior studies
- Collapsed localizer (averaged across all conditions)
- Independent localizer (from a separate task or separate participants)
- Mass univariate with proper correction

**Not acceptable**:
- Choosing the window where the difference between conditions is largest
- Choosing electrodes where the effect is strongest
- "Adjusting" a priori windows after seeing the data to better capture the observed effect

---

## 3. Traditional Parametric Approaches

### Repeated-Measures ANOVA

The most common traditional approach for ERP analysis.

| Property | Details | Source |
|----------|---------|--------|
| **Typical design** | Condition (2+) x Electrode Region (anterior/posterior, or left/midline/right) x Hemisphere (left/right) | Luck, 2014, Ch. 10 |
| **Dependent variable** | Mean amplitude (or peak amplitude) extracted from a defined time window and ROI | Luck, 2014, Ch. 9 |
| **Sphericity correction** | Use Greenhouse-Geisser correction when epsilon < **0.75**; Huynh-Feldt when epsilon >= **0.75** (Luck, 2014, Ch. 10) | Luck, 2014, Ch. 10 |
| **Effect size** | Report **partial eta-squared** (eta_p^2) for ANOVA effects; **Cohen's d** for follow-up t-tests | Keil et al., 2014 |
| **Topographic factors** | Including electrode as a factor tests whether the effect varies across the scalp (interaction), but main effects of electrode are usually not meaningful | Luck, 2014, Ch. 10 |

### Considerations for Electrode Factors

- If including an **Anteriority** factor (frontal, central, parietal) and **Laterality** factor (left, midline, right), you are testing whether the **scalp distribution** of the effect varies across conditions (Luck, 2014, Ch. 10)
- A **Condition x Anteriority** interaction means the condition effect differs in size across anterior-to-posterior electrode sites -- this is topographic information, not additional evidence for the basic effect (Luck, 2014, Ch. 10)
- Normalize amplitudes (e.g., vector scaling; McCarthy & Wood, 1985) before testing topographic interactions to avoid confounding amplitude and distribution differences (Urbach & Kutas, 2002)

### Follow-Up Tests

| Test | When | Source |
|------|------|--------|
| Pairwise t-tests | After significant omnibus ANOVA | Standard |
| Planned contrasts | When specific condition comparisons are hypothesized a priori | Standard |
| Simple effects | When interactions are significant | Standard |
| Correction | Bonferroni or Holm-Bonferroni for multiple pairwise comparisons | Luck, 2014, Ch. 10 |

---

## 4. Mass Univariate Approaches

### Cluster-Based Permutation Test

The most widely used mass univariate approach for ERP/EEG data.

| Property | Details | Source |
|----------|---------|--------|
| **Core idea** | Test each time-electrode point; form clusters of contiguous significant points; compare observed cluster statistics to a null distribution from permuted data | Maris & Oostenveld, 2007 |
| **Cluster-forming threshold** | Typically **p < 0.05** (uncorrected) at each time-electrode point; some use **p < 0.01** for greater specificity | Maris & Oostenveld, 2007 |
| **Cluster statistic** | Sum of t-values (or F-values) within each cluster; tests whether clusters are larger than expected by chance | Maris & Oostenveld, 2007 |
| **Number of permutations** | **>= 1000** (minimum); **5000-10,000** recommended for stable p-values | Maris & Oostenveld, 2007; MNE-Python documentation |
| **Corrected alpha** | **0.05** (two-tailed: use **0.025** for each tail, or set tail parameter appropriately) | Maris & Oostenveld, 2007 |
| **Adjacency definition** | Spatial neighbors based on electrode positions (typically **4-6 nearest neighbors**); temporal neighbors are adjacent time points | Maris & Oostenveld, 2007 |
| **Implementation** | MNE-Python: `mne.stats.spatio_temporal_cluster_test`; FieldTrip: `ft_timelockstatistics` with `cfg.method = 'montecarlo'` | MNE-Python / FieldTrip documentation |

#### Strengths

- Controls family-wise error rate (FWER) across all time points and electrodes simultaneously (Maris & Oostenveld, 2007)
- No need to pre-select time windows or ROIs (Maris & Oostenveld, 2007)
- Works with any test statistic (t-test, F-test, correlation) (Maris & Oostenveld, 2007)
- Handles complex spatiotemporal correlation structure of EEG data naturally (Maris & Oostenveld, 2007)

#### Limitations and Common Misinterpretations

| Issue | Explanation | Source |
|-------|-------------|--------|
| **No spatial/temporal localization** | A significant cluster does NOT mean the effect is present at every time-electrode point within the cluster; the test is on the cluster as a whole | Maris & Oostenveld, 2007 |
| **Sensitive to cluster-forming threshold** | Different thresholds can yield different clusters; report your threshold and consider sensitivity analysis | Pernet et al., 2015 |
| **Not interpretable as absence of effect** | A non-significant cluster does NOT provide evidence that no effect exists at those time points (low power for distributed, weak effects) | Sassenhagen & Draschkow, 2019 |
| **Not for testing latency differences** | Cluster boundaries do NOT indicate when the effect starts/stops | Sassenhagen & Draschkow, 2019 |

### Threshold-Free Cluster Enhancement (TFCE)

| Property | Details | Source |
|----------|---------|--------|
| **Core idea** | Enhances each point's test statistic based on the support from neighboring significant points, without requiring a fixed cluster-forming threshold | Smith & Nichols, 2009 |
| **Advantage** | Avoids the arbitrary cluster-forming threshold choice | Smith & Nichols, 2009 |
| **Parameters** | H = **0.5**, E = **0.5** (defaults for 3D data from fMRI; may need adjustment for ERP data) | Smith & Nichols, 2009 |
| **Implementation** | MNE-Python: `mne.stats.spatio_temporal_cluster_test` with `threshold=dict(start=0, step=0.2)` | MNE-Python documentation |

### FDR Correction (False Discovery Rate)

| Property | Details | Source |
|----------|---------|--------|
| **Core idea** | Control the expected proportion of false positives among all rejected hypotheses (rather than FWER) | Benjamini & Hochberg, 1995 |
| **Method** | Benjamini-Hochberg (BH) procedure: rank p-values, compare to (rank/n) * q | Benjamini & Hochberg, 1995 |
| **Typical q-value** | **0.05** (controls FDR at 5%) | Benjamini & Hochberg, 1995 |
| **When to use** | When testing many individual time-electrode points without clustering; when spatial localization of the effect is desired | Groppe et al., 2011 |
| **Advantages** | More powerful than Bonferroni; provides point-by-point localization; no cluster-forming threshold needed | Groppe et al., 2011 |
| **Disadvantages** | Less powerful than cluster-based methods for spatially extended effects; does not leverage spatial correlation structure | Groppe et al., 2011 |
| **Implementation** | MNE-Python: `mne.stats.fdr_correction`; R: `p.adjust(method="BH")` | Standard implementations |

### Bonferroni and Holm-Bonferroni

| Property | Details | Source |
|----------|---------|--------|
| **Bonferroni** | Divide alpha by number of comparisons: corrected alpha = **0.05 / n_comparisons** | Standard |
| **Holm-Bonferroni** | Step-down procedure; more powerful than Bonferroni while maintaining FWER control | Holm, 1979 |
| **When to use** | Small number of planned comparisons (e.g., 3-5 pairwise t-tests after ANOVA); NOT recommended for hundreds of time-electrode tests | Luck, 2014, Ch. 10 |
| **Advantages** | Simple; controls FWER exactly | Standard |
| **Disadvantages** | Very conservative for large numbers of comparisons; does not leverage spatial/temporal correlation | Standard |

---

## 5. Choosing a Statistical Approach: Decision Framework

### Decision Tree

```
What is your research question?
 |
 +-- "Does condition A differ from condition B for a SPECIFIC component?"
 | |
 | +-- Do you have a priori time window and ROI?
 | |
 | +-- YES --> Extract mean amplitude; run repeated-measures ANOVA or paired t-test
 | +-- NO --> Use collapsed localizer to define window, then ANOVA
 |
 +-- "WHERE and WHEN does the effect occur?" (exploratory)
 | |
 | +-- Is spatial localization important?
 | |
 | +-- YES --> Mass univariate with FDR correction (Groppe et al., 2011)
 | +-- NO --> Cluster-based permutation test (Maris & Oostenveld, 2007)
 |
 +-- "Does my effect survive correction for multiple comparisons?"
 | |
 | +-- Few comparisons (< 10) --> Holm-Bonferroni
 | +-- Many comparisons (time x electrode) --> Cluster-based or FDR
 |
 +-- "Is the effect present at specific time points?" (latency question)
 |
 +-- Fractional area latency on individual participants
 +-- Do NOT use cluster boundaries to answer this question
```

### Method Comparison Summary

| Method | Controls | Power | Localization | Complexity | Best For |
|--------|----------|-------|-------------|------------|----------|
| ANOVA on a priori ROI | Type I (with correction) | High (focused) | Predefined | Low | Confirmatory, well-characterized components |
| Cluster permutation | FWER | High (for extended effects) | No (cluster-level only) | Medium | Whole-scalp exploratory analysis |
| TFCE | FWER | High | Better than cluster | Medium-High | Avoiding cluster-forming threshold |
| FDR (BH) | FDR | Medium | Yes (point-by-point) | Low | When spatial precision matters |
| Bonferroni | FWER | Low (if many tests) | Yes | Lowest | Few planned comparisons |

---

## 6. Reporting Standards

Based on Keil et al. (2014) and community best practices:

### For Traditional ANOVA

- Report exact F-values, degrees of freedom, p-values, and effect sizes (partial eta-squared)
- If Greenhouse-Geisser correction is applied, report the epsilon value and corrected p-value
- Report follow-up pairwise comparisons with correction method specified
- Report mean amplitudes and standard deviations (or standard errors) for each condition

### For Cluster-Based Permutation Tests

- Report the cluster-forming threshold (e.g., p < 0.05 uncorrected)
- Report the number of permutations (e.g., 5000)
- Report the cluster statistic (sum of t-values), cluster p-value, and the approximate spatial and temporal extent of the cluster
- **Do not** over-interpret cluster boundaries as precise onset/offset times
- Report effect sizes for the overall effect (e.g., Cohen's d at the peak time point)

### For FDR-Corrected Mass Univariate

- Report the q-level used (e.g., q = 0.05)
- Report the number of comparisons
- Report which time-electrode points survived correction
- Visualize corrected significance maps

### General Requirements

| Item | Details | Source |
|------|---------|--------|
| Effect sizes | **Always** report: partial eta-squared for ANOVA, Cohen's d for t-tests | Keil et al., 2014 |
| Exact p-values | Report exact values (e.g., p = 0.023), not just p < 0.05 | Keil et al., 2014 |
| Trial counts | Report number of accepted trials per condition per participant (mean and range) | Keil et al., 2014; Boudewyn et al., 2018 |
| Minimum trials | **>= 30** per condition per participant recommended for stable estimates | Boudewyn et al., 2018 |
| Software | Report the analysis software and version (e.g., "MNE-Python 1.6.0", "EEGLAB 2024.0") | Keil et al., 2014 |

---

## 7. Advanced Topics

### Regression-Based ERP (rERP)

| Property | Details | Source |
|----------|---------|--------|
| **Approach** | Fit a linear regression at each time point with continuous/categorical predictors, rather than averaging and comparing means | Smith & Kutas, 2015 |
| **Advantages** | Handles continuous predictors (e.g., word frequency); accounts for overlapping responses; handles unbalanced designs | Smith & Kutas, 2015 |
| **When to use** | Continuous experimental variables; rapid-presentation paradigms with overlap; naturalistic stimuli | Smith & Kutas, 2015 |
| **Implementation** | Unfold toolbox (MATLAB); MNE-Python with custom regression | Ehinger & Dimigen, 2019 |

### Linear Mixed Models (LMMs) for ERP

| Property | Details | Source |
|----------|---------|--------|
| **Approach** | Fit a linear mixed-effects model to single-trial amplitudes with random effects for participants (and optionally items) | Fromer et al., 2018 |
| **Advantages** | Handles unbalanced data; models individual differences; can include continuous predictors and covariates; no need to average first | Fromer et al., 2018 |
| **Disadvantages** | Computationally intensive for many time points; multiple comparison issue if applied at many time-electrode points | Fromer et al., 2018 |
| **Implementation** | R: `lme4::lmer()`; combine with cluster permutation for multiple comparison correction | Fromer et al., 2018 |

### Multivariate Pattern Analysis (MVPA) / Decoding

| Property | Details | Source |
|----------|---------|--------|
| **Approach** | Train a classifier (e.g., SVM, LDA) to distinguish conditions from multivariate EEG patterns at each time point | Grootswagers et al., 2017 |
| **Advantages** | Uses all electrodes simultaneously; sensitive to distributed patterns; temporal generalization reveals processing dynamics | King & Dehaene, 2014 |
| **Typical parameters** | Leave-one-out or **5-fold** cross-validation; **L2-regularized** linear SVM or LDA; **AUC** or accuracy as metric | Grootswagers et al., 2017 |
| **Statistical testing** | Test decoding accuracy against **chance (50%** for 2-class) using one-sample t-test or cluster permutation across time | Grootswagers et al., 2017 |

---

## References

- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate. *JRSS-B*, 57(1), 289-300.
- Boudewyn, M. A., et al. (2018). How many trials does it take to get a significant ERP effect? *Psychophysiology*, 55(6), e13049.
- Ehinger, B. V., & Dimigen, O. (2019). Unfold: An integrated toolbox for overlap correction, non-linear modeling, and regression-based EEG analysis. *PeerJ*, 7, e7838.
- Fromer, R., Maier, M., & Abdel Rahman, R. (2018). Group-level EEG-processing pipeline for flexible single trial-based analyses including linear mixed models. *Frontiers in Neuroscience*, 12, 48.
- Groppe, D. M., Urbach, T. P., & Kutas, M. (2011). Mass univariate analysis of event-related brain potentials/fields I. *Psychophysiology*, 48(12), 1711-1725.
- Grootswagers, T., Wardle, S. G., & Carlson, T. A. (2017). Decoding dynamic brain patterns from evoked responses. *Journal of Neuroscience*, 37(3), 691-702.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65-70.
- Keil, A., et al. (2014). Committee report: Publication guidelines for EEG and MEG. *Psychophysiology*, 51(1), 1-21.
- Kiesel, A., et al. (2008). Measurement of ERP latency differences. *Psychophysiology*, 45(4), 517-523.
- King, J. R., & Dehaene, S. (2014). Characterizing the dynamics of mental representations. *Trends in Cognitive Sciences*, 18(4), 203-210.
- Kriegeskorte, N., et al. (2009). Circular analysis in systems neuroscience. *Nature Neuroscience*, 12(5), 535-540.
- Luck, S. J. (2014). *An Introduction to the Event-Related Potential Technique* (2nd ed.). MIT Press.
- Luck, S. J., & Gaspelin, N. (2017). How to get statistically significant effects in any ERP experiment. *Psychophysiology*, 54(1), 146-157.
- Maris, E., & Oostenveld, R. (2007). Nonparametric statistical testing of EEG- and MEG-data. *JNM*, 164(1), 177-190.
- McCarthy, G., & Wood, C. C. (1985). Scalp distributions of event-related potentials: An ambiguity associated with analysis of variance models. *Electroencephalography and Clinical Neurophysiology*, 62(3), 203-208.
- Pernet, C. R., Latinus, M., Nichols, T. E., & Rousselet, G. A. (2015). Cluster-based computational methods for mass univariate analyses of event-related brain potentials/fields. *JNM*, 250, 85-93.
- Sassenhagen, J., & Draschkow, D. (2019). Cluster-based permutation tests of MEG/EEG data do not establish significance of effect latency or location. *Psychophysiology*, 56(6), e13335.
- Smith, N. J., & Kutas, M. (2015). Regression-based estimation of ERP waveforms. *Psychophysiology*, 52(2), 157-168.
- Smith, S. M., & Nichols, T. E. (2009). Threshold-free cluster enhancement. *NeuroImage*, 44(1), 83-98.
- Urbach, T. P., & Kutas, M. (2002). The intractability of scaling scalp distributions to infer neuroelectric sources. *Psychophysiology*, 39(6), 791-808.
