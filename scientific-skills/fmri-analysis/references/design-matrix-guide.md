# Design Matrix Construction Guide

## Overview

The design matrix is the core of the fMRI GLM. Each column represents a regressor (expected signal component or confound), and each row corresponds to one acquired volume (time point). Correct construction is essential: errors in the design matrix directly produce incorrect statistical results.

This reference expands on the design matrix topics introduced in `../SKILL.md`.

## Experimental Design Types

### Block Designs

In a block design, stimuli of the same condition are presented in sustained epochs (typically **15-30 seconds**; Poldrack et al., 2011, Ch. 3).

**Advantages:**
- Maximum detection power for sustained activations (Liu et al., 2001)
- Simple GLM specification: one boxcar regressor per condition, convolved with HRF
- Robust to HRF misspecification because the sustained signal is easily detected

**Disadvantages:**
- Cannot estimate HRF shape (hemodynamic responses overlap and saturate)
- Cannot separate individual trial types within a block
- Susceptible to habituation, anticipation, and strategy effects

**Design matrix specification:**
- One regressor per block condition: onset = block start, duration = block length (e.g., 20 s)
- Convolved with the chosen HRF model
- Recommended block duration: **15-30 seconds** (shorter blocks sacrifice power; longer blocks increase habituation; Poldrack et al., 2011, Ch. 3)

### Event-Related Designs

In an event-related design, individual trials are modeled as brief events (typical duration **0.5-4 seconds**; Dale, 1999).

**Advantages:**
- Can estimate HRF shape via deconvolution or FIR models
- Can separate individual trial types (e.g., correct vs. incorrect trials)
- Can randomize trial order, reducing anticipation effects
- Can jitter inter-trial intervals for optimal statistical efficiency

**Disadvantages:**
- Lower detection power per unit time compared to block designs (Liu et al., 2001)
- Requires more trials for stable estimation
- More sensitive to HRF model specification

**Design matrix specification:**
- One regressor per condition: onset times for each trial, duration = stimulus presentation time (or 0 for impulse events)
- Convolved with the chosen HRF model

### Mixed (Hybrid) Designs

Combine block and event-related elements. For example, blocks of a task with individual trial onsets modeled within each block (Petersen & Dubis, 2012).

**Design matrix specification:**
- Separate sustained (block) and transient (event) regressors
- The sustained regressor models the tonic state; the transient regressor models trial-by-trial variation within that state

## Optimal Inter-Stimulus Interval (ISI)

The spacing between events critically affects statistical efficiency.

### Fixed vs. Jittered ISI

| Design | Efficiency for Detection | Efficiency for Estimation | Source |
|---|---|---|---|
| Fixed ISI (long, > 12 s) | Moderate | High (individual HRFs separable) | Buckner et al., 1996 |
| Fixed ISI (short, 2-4 s) | Low (responses overlap predictably) | Low (cannot deconvolve) | Dale, 1999 |
| Jittered ISI (random, mean 4-8 s) | High | Moderate to High | Dale, 1999 |
| Jittered ISI with null events | Highest | High | Friston et al., 1999 |

**Key result**: For jittered designs, efficiency improves monotonically with decreasing mean ISI. Jittered designs can be **>10x more efficient** than fixed ISI designs with the same mean interval (Dale, 1999).

### Practical ISI Recommendations

- **Minimum mean ISI**: **2 seconds** to allow hemodynamic responses to partially separate (Dale, 1999)
- **Include null events**: Insert **20-33%** null trials (fixation-only periods) distributed randomly throughout the experiment. This provides baseline estimation and temporal jitter (Friston et al., 1999; Josephs & Henson, 1999)
- **ISI distribution**: Sample ISIs from a truncated exponential or uniform distribution. The exponential distribution provides more short ISIs (higher efficiency) while including occasional long ISIs (better HRF estimation) (Hagberg et al., 2001)
- **Minimum ISI**: At least **2 seconds** even for jittered designs to avoid severe nonlinear saturation of the hemodynamic response (Glover, 1999)
- **Maximum ISI**: Keep below half the high-pass filter cutoff period to avoid signal attenuation

### Design Optimization Tools

- **optseq2** (FreeSurfer): Optimizes event ordering and null event placement for maximum efficiency (Dale, 1999)
- **NeuroDesign** (Python): Genetic algorithm-based optimization for detection and estimation efficiency (Durnez et al., 2017)
- **fMRI Power**: Power calculations for fMRI designs (Mumford & Nichols, 2008)

## Design Efficiency Calculation

Design efficiency quantifies how well a given design matrix allows estimation of the effects of interest.

### Detection Efficiency

For a contrast vector **c** and design matrix **X**, the efficiency of detecting the contrast is:

```
efficiency = 1 / trace(c' * (X'X)^(-1) * c)
```

Higher values indicate more statistical power for detecting the contrast (Dale, 1999; Liu et al., 2001).

### Detection vs. Estimation Trade-off

- **Detection power**: Ability to detect whether an effect exists (e.g., is this region activated?). Maximized by block designs and rapid event-related designs with jittered ISI (Liu et al., 2001)
- **Estimation efficiency**: Ability to accurately estimate the shape of the HRF. Maximized by designs with long ISIs or well-jittered rapid designs (Liu et al., 2001)
- These are inherently in tension: optimizing for one reduces the other. Choose based on your primary research question

## Parametric Modulators

Parametric modulators allow continuous trial-by-trial variables (e.g., reaction time, stimulus intensity, subjective rating) to modulate the expected BOLD response.

### Implementation

1. Create a standard onset regressor for the condition (convolved with HRF)
2. Create an additional regressor with the same onsets but amplitude scaled by the parametric variable (mean-centered)
3. Both regressors are convolved with the HRF
4. The parametric regressor captures variance linearly related to the modulating variable, after removing the main effect of the condition

### Practical Considerations

- **Mean-center the parametric variable** to make the unmodulated and modulated regressors more orthogonal (Mumford et al., 2015)
- **Orthogonalization**: Some software (SPM) automatically orthogonalizes parametric modulators with respect to the main condition regressor. This means the main regressor captures all shared variance, and the parametric regressor captures only the residual. Be aware of this behavior -- it can affect interpretation (Mumford et al., 2015)
- **Order of entry matters in SPM**: When multiple parametric modulators are entered, later ones are orthogonalized with respect to earlier ones (unless serial orthogonalization is turned off). In FSL and AFNI, regressors are not orthogonalized by default (Mumford et al., 2015)
- **Polynomial expansion**: For nonlinear relationships, include quadratic (and occasionally cubic) terms as additional parametric modulators

### Common Parametric Modulators in Cognitive Neuroscience

| Modulator | Domain | Interpretation | Source |
|---|---|---|---|
| Reaction time | Decision-making | Regions whose activity scales with decision difficulty | Grinband et al., 2008 |
| Prediction error | Reinforcement learning | Regions encoding reward prediction error signals | O'Doherty et al., 2003 |
| Stimulus intensity | Perception | Regions with graded response to stimulus strength | Buchel et al., 1998 |
| Memory confidence | Memory | Regions tracking retrieval strength | Kim & Cabeza, 2007 |
| Working memory load | Executive function | Regions sensitive to cognitive demand | Braver et al., 1997 |

## Temporal Derivatives

### What They Model

Adding a temporal derivative to the canonical HRF allows the model to capture small shifts (+/- approximately **1 second**) in the peak latency of the hemodynamic response (Friston et al., 1998; Henson et al., 2002).

The dispersion derivative additionally captures variations in the width (duration) of the response.

### Contrast Specification with Derivatives

**Critical domain knowledge**: When using temporal and dispersion derivatives, standard t-contrasts should weight only the canonical HRF regressor. The derivative regressors serve as nuisance parameters that soak up variance from timing variability, improving the fit of the canonical regressor.

```
Example with canonical + temporal derivative + dispersion derivative:
Condition A regressors: [A_canonical, A_temporal_deriv, A_dispersion_deriv]
Condition B regressors: [B_canonical, B_temporal_deriv, B_dispersion_deriv]

t-contrast (A > B): [1 0 0 -1 0 0 ...]
F-contrast (any response to A): [[1 0 0 ...], [0 1 0 ...], [0 0 1 ...]]
```

The F-test across all three basis functions tests whether there is any hemodynamic response to the condition, regardless of its exact shape (Calhoun et al., 2004).

### When to Add Derivatives

- **Always consider temporal derivatives** when: analyzing data from clinical populations, pediatric/elderly subjects, or when comparing groups that may differ in neurovascular coupling (Handwerker et al., 2004)
- **Do not add derivatives** when: you have very few trials per condition (< 20), as the additional parameters reduce degrees of freedom without compensating benefit

## Confound Regressor Details

### fMRIPrep Confound Outputs

When using fMRIPrep (Esteban et al., 2019), the confounds TSV file contains many potential regressors. A recommended selection strategy:

**Minimal model** (task fMRI with low motion):
- 6 motion parameters
- aCompCor: top 5 WM + CSF components

**Standard model** (recommended default):
- 24 motion parameters (Friston model)
- aCompCor: top 5 WM + CSF components
- High-motion spike regressors (FD > 0.5 mm)

**Aggressive model** (high motion or connectivity analysis):
- 24 motion parameters (Friston model)
- aCompCor: top 5 WM + CSF components
- Spike regressors (FD > 0.2 mm)
- Cosine regressors for high-pass filtering (provided by fMRIPrep)

### Non-Steady-State Volumes

The first few volumes of each fMRI run may not have reached steady-state magnetization. These should be either:
- Excluded from the analysis (remove the first **3-5 volumes**, depending on the TR and flip angle; Poldrack et al., 2011, Ch. 2)
- Modeled with indicator regressors (one regressor per excluded volume)

fMRIPrep identifies these automatically and provides `non_steady_state_outlier_XX` columns in the confounds file.

## References

- Braver, T. S., Cohen, J. D., Nystrom, L. E., et al. (1997). A parametric study of prefrontal cortex involvement in human working memory. *NeuroImage*, 5(1), 49-62.
- Buchel, C., Holmes, A. P., Rees, G., & Friston, K. J. (1998). Characterizing stimulus-response functions using nonlinear regressors in parametric fMRI experiments. *NeuroImage*, 8(2), 140-148.
- Buckner, R. L., Bandettini, P. A., O'Craven, K. M., et al. (1996). Detection of cortical activation during averaged single trials of a cognitive task using functional magnetic resonance imaging. *PNAS*, 93(25), 14878-14883.
- Calhoun, V. D., Stevens, M. C., Pearlson, G. D., & Kiehl, K. A. (2004). fMRI analysis with the general linear model: Removal of latency-induced amplitude bias. *NeuroImage*, 22(1), 252-257.
- Dale, A. M. (1999). Optimal experimental design for event-related fMRI. *Human Brain Mapping*, 8(2-3), 109-114.
- Durnez, J., Blair, R., & Poldrack, R. A. (2017). NeuroDesign: Optimal experimental designs for task fMRI. *bioRxiv*, 119594.
- Esteban, O., Markiewicz, C. J., Blair, R. W., et al. (2019). fMRIPrep: A robust preprocessing pipeline for functional MRI. *Nature Methods*, 16(1), 111-116.
- Friston, K. J., Fletcher, P., Josephs, O., et al. (1998). Event-related fMRI: Characterizing differential responses. *NeuroImage*, 7(1), 30-40.
- Friston, K. J., Zarahn, E., Josephs, O., Henson, R. N. A., & Dale, A. M. (1999). Stochastic designs in event-related fMRI. *NeuroImage*, 10(5), 607-619.
- Glover, G. H. (1999). Deconvolution of impulse response in event-related BOLD fMRI. *NeuroImage*, 9(4), 416-429.
- Grinband, J., Wager, T. D., Lindquist, M., Ferrera, V. P., & Hirsch, J. (2008). Detection of time-varying signals in event-related fMRI designs. *NeuroImage*, 43(3), 509-520.
- Hagberg, G. E., Zito, G., Patria, F., & Sanes, J. N. (2001). Improved detection of event-related functional MRI signals using probability functions. *NeuroImage*, 14(5), 1193-1205.
- Handwerker, D. A., Ollinger, J. M., & D'Esposito, M. (2004). Variation of BOLD hemodynamic responses across subjects and brain regions and their effects on statistical analyses. *NeuroImage*, 21(4), 1639-1651.
- Henson, R. N. A., Price, C. J., Rugg, M. D., Turner, R., & Friston, K. J. (2002). Detecting latency differences in event-related BOLD responses. *NeuroImage*, 15(1), 83-97.
- Josephs, O., & Henson, R. N. A. (1999). Event-related functional magnetic resonance imaging: Modelling, inference and optimization. *Philosophical Transactions of the Royal Society B*, 354(1387), 1215-1228.
- Kim, H., & Cabeza, R. (2007). Trusting our memories: Dissociating the neural correlates of confidence in veridical versus illusory memories. *Journal of Neuroscience*, 27(45), 12190-12197.
- Liu, T. T., Frank, L. R., Wong, E. C., & Buxton, R. B. (2001). Detection power, estimation efficiency, and predictability in event-related fMRI. *NeuroImage*, 13(4), 759-773.
- Mumford, J. A., & Nichols, T. E. (2008). Power calculation for group fMRI studies accounting for arbitrary design and temporal autocorrelation. *NeuroImage*, 39(1), 261-268.
- Mumford, J. A., Poline, J. B., & Poldrack, R. A. (2015). Orthogonalization of regressors in fMRI models. *PLoS ONE*, 10(4), e0126255.
- O'Doherty, J. P., Dayan, P., Friston, K., Critchley, H., & Dolan, R. J. (2003). Temporal difference models and reward-related learning in the human brain. *Neuron*, 38(2), 329-337.
- Petersen, S. E., & Dubis, J. W. (2012). The mixed block/event-related design. *NeuroImage*, 62(2), 1177-1184.
- Poldrack, R. A., Mumford, J. A., & Nichols, T. E. (2011). *Handbook of Functional MRI Data Analysis*. Cambridge University Press.
