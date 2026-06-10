# EEG Preprocessing Parameter Lookup Tables

## Overview

This reference provides detailed parameter tables for each preprocessing step described in `../SKILL.md`, organized by analysis type and EEG system.

## Filter Parameters by Analysis Type

### High-Pass Filter

| Analysis Type | Cutoff (Hz) | Transition BW (Hz) | Filter Order (at 256 Hz) | Source |
|---|---|---|---|---|
| ERP (standard) | 0.1 | 0.1-0.2 | 3300-6600 | Luck, 2014; Widmann et al., 2015 |
| ERP (for ICA training) | 1.0 | 1.0-2.0 | 330-660 | Winkler et al., 2015 |
| Time-frequency | 0.1 | 0.1-0.2 | 3300-6600 | Cohen, 2014 |
| Slow cortical potentials | 0.01 | 0.01-0.02 | 33,000-66,000 | Luck, 2014 |
| Resting-state (alpha/beta) | 0.5 | 0.5-1.0 | 660-1320 | Cohen, 2014 |

### Low-Pass Filter

| Analysis Type | Cutoff (Hz) | Transition BW (Hz) | Source |
|---|---|---|---|
| ERP (publication figures) | 20-30 | 5-10 | Luck, 2014 |
| ERP (analysis) | 30-40 | 5-10 | Luck, 2014 |
| Alpha/beta oscillations | 100 | 10-20 | Cohen, 2014 |
| Gamma oscillations | 150-200 | 20-40 | Cohen, 2014 |
| General purpose | 100 | 10-20 | Widmann et al., 2015 |

### Anti-Aliasing Filter (Before Downsampling)

| Original Rate (Hz) | Target Rate (Hz) | Required Low-Pass (Hz) | Source |
|---|---|---|---|
| 1000 | 256 | < 128 (Nyquist of target) | Widmann et al., 2015 |
| 1000 | 512 | < 256 | Widmann et al., 2015 |
| 2048 | 256 | < 128 | Widmann et al., 2015 |

**Rule**: Before downsampling, apply a low-pass filter at **< 0.5 x target sampling rate** to prevent aliasing (Widmann et al., 2015).

## Re-Referencing by System and Analysis

| EEG System | Channels | Recommended Reference | Alternative | Source |
|---|---|---|---|---|
| BioSemi ActiveTwo | 64/128/256 | Average reference | Linked mastoids | Dien, 1998 |
| Brain Products actiCHamp | 32/64/128 | Average (if >= 64) or linked mastoids | Cz | Luck, 2014 |
| Neuroscan Synamps | 32/64/128 | Average (if >= 64) or linked mastoids | -- | Luck, 2014 |
| ANT Neuro eego | 32/64 | Average (if 64) or linked mastoids | -- | Dien, 1998 |
| Emotiv EPOC (14 ch) | 14 | **Linked mastoids only** | Common mode reference | Luck, 2014 |
| Muse (4 ch) | 4 | **No re-referencing possible** | System reference only | -- |

### Reference Selection for Specific Analyses

| Analysis Type | Best Reference | Rationale | Source |
|---|---|---|---|
| Scalp topography mapping | Average reference (>= 64 ch) | Provides neutral reference for topographic maps | Dien, 1998 |
| Source localization | Average reference | Required by many inverse solvers | Michel et al., 2004 |
| Single-channel ERP (e.g., Fz, Pz) | Linked mastoids | Maximizes signal at vertex electrodes | Luck, 2014 |
| Lateralized ERPs (N2pc, LRP) | Average reference or linked mastoids | Either works; must be consistent across studies | Luck, 2014 |
| Auditory ERP (MMN) | Nose reference or average | Nose captures full MMN polarity reversal | Naatanen et al., 2007 |

## ICA Parameters by System

| System | Channels | Recommended Components | Minimum Data Length | Source |
|---|---|---|---|---|
| 32-channel | 32 | 32 (or reduce if < 20 min data) | ~13 min at 256 Hz | Onton & Makeig, 2006 |
| 64-channel | 64 | 64 (or reduce via PCA to ~40) | ~53 min at 256 Hz | Onton & Makeig, 2006 |
| 128-channel | 128 | Reduce via PCA to **60-80** | ~47-82 min at 256 Hz | Onton & Makeig, 2006 |
| 256-channel | 256 | Reduce via PCA to **80-100** | ~82-128 min at 256 Hz | Onton & Makeig, 2006 |

**Data length rule**: Minimum data points = **20 x n_components^2** (Onton & Makeig, 2006). For 64 components at 256 Hz: 20 * 64^2 / 256 = **320 seconds** (~5.3 minutes). More data always improves decomposition quality; **15+ minutes** is recommended for 64 channels.

**PCA reduction**: When you have more channels than warranted by data length, reduce dimensionality via PCA before ICA. Set the number of PCA components to `n_components = floor(sqrt(n_samples / 20))` (Onton & Makeig, 2006).

## ICLabel Classification Thresholds

### Conservative Approach (Minimize False Positives)

Remove components classified as:
- Brain: **Never remove** (regardless of probability)
- Eye: Remove if probability > **0.80**
- Muscle: Remove if probability > **0.90**
- Heart: Remove if probability > **0.90**
- Line noise: Remove if probability > **0.90**
- Channel noise: Remove if probability > **0.90**

### Liberal Approach (Maximize Artifact Removal)

Remove components classified as:
- Brain probability < **0.50** AND
- Any non-brain category probability > **0.30**

### Recommended Default (Balanced)

Remove components where:
- Eye probability > **0.80**, OR
- Muscle probability > **0.80**, OR
- Heart probability > **0.80**, OR
- Brain probability < **0.20**

Source: Pion-Tonachini et al. (2019), with practical thresholds based on community experience.

## ASR Parameter Recommendations

| Data Quality | Burst Criterion (SD) | Window Length (s) | Max Bad Channels | Source |
|---|---|---|---|---|
| Clean lab data (cooperative adults) | **20** (default) | 0.5 | 0.3 | Mullen et al., 2015 |
| Moderate artifacts (typical ERP study) | **15** | 0.5 | 0.3 | Chang et al., 2020 |
| Heavy artifacts (clinical populations, children) | **10-12** | 0.5 | 0.4 | Chang et al., 2020 |
| Mobile EEG / high motion | **10** | 1.0 | 0.4 | Mullen et al., 2015 |
| Real-time BCI applications | **20-25** | 0.5 | 0.3 | Mullen et al., 2015 |

**Warning**: Lower burst criterion values remove more data but may also remove genuine neural transients. Validate ASR cleaning by comparing ERP waveforms before and after ASR to ensure component morphology is preserved (Chang et al., 2020).

## Epoch Rejection Thresholds by Population

| Population | Peak-to-Peak Threshold (uV) | Absolute Threshold (uV) | Source |
|---|---|---|---|
| Healthy adults | 100-150 | +/- 75-100 | Luck, 2014 |
| Elderly adults | 150-200 | +/- 100-125 | Keil et al., 2014 |
| Children (6-12 years) | 150-200 | +/- 100-150 | Keil et al., 2014 |
| Infants | 200-250 | +/- 150-200 | Luck, 2014 |
| Clinical populations (epilepsy) | 200-300 | +/- 150-200 | Domain convention |

**Important**: These are starting points. Adjust thresholds based on the actual distribution of your data. Plot epoch amplitude histograms and set thresholds to capture the tail of the distribution (Luck, 2014).

## References

- Chang, C. Y., Hsu, S. H., Pion-Tonachini, L., & Jung, T. P. (2020). Evaluation of artifact subspace reconstruction. *IEEE Transactions on Biomedical Engineering*, 67(4), 1114-1121.
- Cohen, M. X. (2014). *Analyzing Neural Time Series Data*. MIT Press.
- Dien, J. (1998). Issues in the application of the average reference. *BRMIC*, 30(3), 449-457.
- Keil, A., Debener, S., Gratton, G., et al. (2014). Committee report: Publication guidelines for EEG and MEG. *Psychophysiology*, 51(1), 1-21.
- Luck, S. J. (2014). *An Introduction to the Event-Related Potential Technique* (2nd ed.). MIT Press.
- Michel, C. M., Murray, M. M., Lantz, G., et al. (2004). EEG source imaging. *Clinical Neurophysiology*, 115(10), 2195-2222.
- Mullen, T. R., Kothe, C. A. E., Chi, Y. M., et al. (2015). Real-time neuroimaging and cognitive monitoring using wearable dry EEG. *IEEE TBME*, 62(11), 2553-2567.
- Naatanen, R., Paavilainen, P., Rinne, T., & Alho, K. (2007). The mismatch negativity (MMN). *Clinical Neurophysiology*, 118(12), 2544-2590.
- Onton, J., & Makeig, S. (2006). Information-based modeling of event-related brain dynamics. *Progress in Brain Research*, 159, 99-120.
- Pion-Tonachini, L., Kreutz-Delgado, K., & Makeig, S. (2019). ICLabel. *NeuroImage*, 198, 181-197.
- Widmann, A., Schroger, E., & Maess, B. (2015). Digital filter design for electrophysiological data. *Journal of Neuroscience Methods*, 250, 34-46.
- Winkler, I., Debener, S., Muller, K. R., & Tangermann, M. (2015). On the influence of high-pass filtering on ICA-based artifact reduction. *Proceedings of EMBC*, 4101-4105.
