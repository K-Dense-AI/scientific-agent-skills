# ERP Preprocessing Pipeline

Detailed parameter recommendations for each step of the ERP preprocessing pipeline. All numerical values include citations to their source.

---

## Step 1: Data Import and Initial Inspection

### Actions

- Load raw continuous EEG data
- Visually inspect for gross artifacts (e.g., amplifier saturation, large-scale drift, periods of flat-line data)
- Note any channels that appear consistently noisy across the recording
- Verify event markers/triggers align with experimental design

### Parameters

| Parameter | Recommendation | Source |
|-----------|---------------|--------|
| Sampling rate verification | Confirm >= **250 Hz** for typical ERP work; **512 Hz** or **1024 Hz** common for modern systems | Luck, 2014, Ch. 5 |
| Data format | Use lossless formats (e.g., .fif, .set, .bdf); avoid lossy compression | Best practice (expert consensus) |

### Decision Points

- If sampling rate > **512 Hz** and you do not need high temporal precision (e.g., brainstem responses), downsample to **256 Hz** or **512 Hz** after anti-aliasing filter to reduce computational load (Luck, 2014, Ch. 5)

---

## Step 2: Filtering

### High-Pass Filter

| Parameter | Recommendation | Source |
|-----------|---------------|--------|
| Default cutoff | **0.1 Hz** | Luck, 2014, Ch. 5; Tanner et al., 2015 |
| Alternative cutoff | **0.01 Hz** when studying slow components (CNV, P3, LPC) or when filter distortion is a concern | Tanner et al., 2015 |
| Aggressive cutoff | **0.5 Hz** only for ICA decomposition step (apply to a copy of the data, not the final data); improves ICA quality | Winkler et al., 2015 |
| Filter type | **FIR** (finite impulse response), zero-phase (non-causal) | Widmann et al., 2015 |
| Filter order / transition bandwidth | Hamming window FIR; transition bandwidth **1 Hz** for cutoffs >= 1 Hz, or **2x the cutoff frequency** for lower cutoffs | Widmann et al., 2015 |

**Why 0.1 Hz and not higher?** High-pass cutoffs above **0.1 Hz** can:
- Introduce artifactual effects that mimic ERP components (Tanner et al., 2015)
- Distort the latency and amplitude of slow ERP components such as N400 and P300 (Widmann & Schroger, 2012)
- Create apparent baseline differences that do not exist in the unfiltered data (Tanner et al., 2015)

**Why 0.1 Hz and not lower?** Very low cutoffs (e.g., **0.01 Hz**) allow more low-frequency drift, which can:
- Increase baseline variability across epochs
- Reduce signal-to-noise ratio for faster components (P1, N1)
- The **0.1 Hz** value represents a balance between these competing concerns (Luck, 2014, Ch. 5)

### Low-Pass Filter

| Parameter | Recommendation | Source |
|-----------|---------------|--------|
| Default cutoff | **30 Hz** | Luck, 2014, Ch. 5 |
| Alternative cutoff | **40 Hz** when studying components with fast temporal dynamics (e.g., brainstem responses, high-frequency oscillations) | Keil et al., 2014 |
| Conservative cutoff | **20 Hz** acceptable for broad, slow components (N400, P300, LPC) when high-frequency noise is problematic | Kappenman & Luck, 2010 |
| Filter type | **FIR**, zero-phase (same as high-pass) | Widmann et al., 2015 |

**Rationale**: ERP components are primarily composed of frequencies below **30 Hz**. The low-pass filter removes high-frequency noise (muscle artifact, line noise residuals) without removing signal (Luck, 2014, Ch. 5).

### Notch Filter

| Parameter | Recommendation | Source |
|-----------|---------------|--------|
| Line noise frequency | **50 Hz** (Europe, Asia, most of world) or **60 Hz** (Americas, Japan at 60Hz regions) | Regional electrical standards |
| When to use | Only if line noise is present after bandpass filtering | Luck, 2014, Ch. 5; Widmann et al., 2015 |
| Preferred alternative | A low-pass at **30 Hz** typically removes line noise, making notch filter unnecessary | Luck, 2014, Ch. 5 |
| If needed | Use narrow notch (bandwidth **1-2 Hz**) to minimize spectral distortion | Widmann et al., 2015 |

**Best practice**: If your low-pass filter is set at **30 Hz**, a notch filter at 50/60 Hz is redundant. Only apply a notch filter if your low-pass cutoff is above the line noise frequency (Luck, 2014, Ch. 5).

---

## Step 3: Re-Referencing

### Reference Scheme Options

| Scheme | When to Use | Advantages | Disadvantages | Source |
|--------|-------------|-----------|---------------|--------|
| **Average reference** | High-density arrays (>= 64 channels); most ERP studies | Approximates a neutral reference; widely accepted | Biased with low channel counts or poor coverage; affected by noisy channels | Luck, 2014, Ch. 5; Keil et al., 2014 |
| **Linked mastoids** (TP9/TP10 average) | Low-density arrays (32 channels or fewer); clinical EEG | Simple; good for temporal/parietal components | Not truly neutral; asymmetric mastoid potentials add noise; can reduce lateralized effects | Luck, 2014, Ch. 5 |
| **Single mastoid** | Legacy studies; comparability with older literature | Simple | Introduces hemispheric asymmetry artifact | Luck, 2014, Ch. 5 |
| **REST** (Reference Electrode Standardization Technique) | Source-level analyses; theoretical ideal | Approximates infinity reference; theoretically principled | Requires accurate head model; computationally expensive | Yao, 2001; Dong et al., 2017 |
| **CSD** (Current Source Density / Surface Laplacian) | When spatial resolution is more important than waveform shape; reducing volume conduction | Reference-free; sharpens topography | Attenuates deep sources; changes component morphology; not appropriate for all components | Kayser & Tenke, 2006 |

### Decision Logic

1. **Default recommendation**: Use **average reference** for studies with >= **64 channels** (Luck, 2014, Ch. 5)
2. For **32 channels or fewer**, average reference becomes unreliable; use **linked mastoids** (Luck, 2014, Ch. 5)
3. If studying **lateralized components** (N2pc, LRP, ELAN), avoid single mastoid reference as it distorts hemispheric asymmetries (Luck, 2014, Ch. 5)
4. Apply re-referencing **after bad channel interpolation** when using average reference, so that interpolated channels do not contaminate the reference signal (best practice; expert consensus)
5. If combining with ICA: re-reference **before** ICA, as ICA assumes a consistent reference (Luck, 2014, Ch. 5)

---

## Step 4: Bad Channel Identification and Interpolation

### Identification Criteria

| Criterion | Threshold | Source |
|-----------|-----------|--------|
| Flat-line duration | > **5 seconds** of zero variance | EEGLAB/clean_rawdata defaults (MNE-Python convention) |
| High-frequency noise (std) | > **3-5 standard deviations** above the mean of all channels | Keil et al., 2014 |
| Low correlation with neighbors | Correlation < **0.4** with surrounding channels (over sliding windows) | Bigdely-Shamlo et al., 2015 |
| Visual inspection | Persistent broadband noise, intermittent spiking | Luck, 2014, Ch. 5 |

### Interpolation Parameters

| Parameter | Recommendation | Source |
|-----------|---------------|--------|
| Method | **Spherical spline** interpolation | Perrin et al., 1989; standard in EEGLAB and MNE-Python |
| When to interpolate | After identifying bad channels but **before** average re-referencing | Luck, 2014, Ch. 5 |
| Maximum proportion | Interpolate no more than **10%** of total channels (e.g., <= 6 out of 64) | Keil et al., 2014 |
| If > 10% bad channels | Exclude the participant rather than interpolating excessively | Keil et al., 2014 |
| Bridged electrodes | Detect via electrical bridging analysis; interpolate or exclude (Alschuler et al., 2014) | Alschuler et al., 2014 |

### Decision Points

- **Interpolate early**: Interpolate before ICA so that ICA decomposition operates on a complete, well-conditioned data matrix
- **Document everything**: Record which channels were interpolated and why (Keil et al., 2014)
- If a channel is bad for only part of the recording, consider marking those segments rather than interpolating the entire channel

---

## Step 5: ICA-Based Artifact Correction

### ICA Parameters

| Parameter | Recommendation | Source |
|-----------|---------------|--------|
| Algorithm | **Extended Infomax** (default in EEGLAB) or **PICARD** (faster, used in MNE-Python) | Makeig et al., 1996; Ablin et al., 2018 |
| Number of components | **n_components = n_channels - n_interpolated** (rank-reduced data) or use PCA pre-reduction to **95-99% variance explained** | Luck, 2014, Ch. 5; MNE-Python convention |
| High-pass for ICA | Apply **1 Hz** high-pass on a copy of data for ICA decomposition, then apply the resulting ICA weights to the **0.1 Hz** filtered data | Winkler et al., 2015 |
| Minimum data length | At least **k * n_components^2** data points, where k >= **20** (i.e., for 64 components, need >= 81,920 points = ~160 s at 512 Hz) | Onton & Makeig, 2006 |

### Component Classification

| Artifact Type | Key Identification Features | Source |
|---------------|---------------------------|--------|
| **Eye blinks** | Large frontal positivity (Fp1/Fp2); time course matches blink pattern; topography: frontal bilateral | Luck, 2014, Ch. 5; Chaumon et al., 2015 |
| **Horizontal saccades** | Frontal dipolar topography (F7 vs F8); step-like time course | Luck, 2014, Ch. 5 |
| **Cardiac artifact** | Regular periodic signal (~1 Hz); frontal/temporal topography; sharp QRS morphology | Luck, 2014, Ch. 5 |
| **Muscle artifact** | High-frequency broadband noise; peripheral/temporal electrodes; spectrum dominated by > 20 Hz | McMenamin et al., 2010 |
| **Channel noise** | Activity localized to single electrode; irregular time course | Chaumon et al., 2015 |

### Automated Classification Tools

| Tool | Method | Source |
|------|--------|--------|
| **ICLabel** | Deep learning classifier; outputs probability for 7 categories | Pion-Tonachini et al., 2019 |
| **ADJUST** | Feature-based heuristic rules | Mognon et al., 2011 |
| **MARA** | Machine learning on 6 features | Winkler et al., 2011 |
| **iclabel threshold** | Remove components with brain probability < **0.5** and any non-brain probability > **0.8** | Pion-Tonachini et al., 2019; common usage threshold |

### Decision Points

- **Conservative approach**: Remove only components that are clearly artifactual (eye blinks, eye movements, cardiac). When uncertain, keep the component (Luck, 2014, Ch. 5)
- **Typical removal**: **1-3 components** for eye blinks/movements; **0-1** for cardiac (Chaumon et al., 2015)
- If removing > **5-6 components**, reconsider data quality or ICA parameters
- **Document**: Report the number of components removed and their classification (Keil et al., 2014)

---

## Step 6: Epoching and Baseline Correction

### Epoching Parameters

| Parameter | Recommendation | Source |
|-----------|---------------|--------|
| Default epoch window | **-200 ms to 800 ms** relative to stimulus onset | Luck, 2014, Ch. 5 |
| Extended window | **-200 ms to 1000 ms** or longer for slow components (P3, N400, P600, LPC) | Luck, 2014, Ch. 5 |
| Pre-stimulus window | **-500 ms to stimulus** when studying pre-stimulus activity (CNV, alpha desynchronization) | Expert consensus |
| Response-locked epochs | **-500 ms to 500 ms** relative to response for ERN/Pe analysis | Luck, 2014, Ch. 5 |

### Baseline Correction

| Parameter | Recommendation | Source |
|-----------|---------------|--------|
| Default baseline window | **-200 ms to 0 ms** (pre-stimulus) | Luck, 2014, Ch. 5 |
| Extended baseline | **-500 ms to -200 ms** when early post-stimulus activity may contaminate the standard window | Expert consensus |
| Whole-epoch baseline | **Entire epoch mean** subtracted; used in some regression-based approaches | Smith & Kutas, 2015 |
| No baseline correction | When using linear detrending or high-pass filter as alternative (controversial) | Alday, 2019 |

### Considerations

- Baseline correction assumes that the pre-stimulus period contains no systematic condition differences. If your design involves cue-target paradigms where cue-related activity extends into the baseline, consider:
 - Using an earlier baseline window (e.g., **-500 ms to -300 ms**; Luck, 2014, Ch. 5)
 - Using a pre-cue baseline
 - Using regression-based baseline correction (Alday, 2019)
- Epoch length should include enough pre-stimulus time for baseline and enough post-stimulus time to capture the component of interest, plus buffer for filter edge artifacts (~**3 cycles of the high-pass cutoff**, i.e., ~100 ms for a 0.1 Hz filter is negligible, but ~600 ms for a 0.5 Hz filter; Luck, 2014, Ch. 5)

---

## Step 7: Epoch Rejection (Post-ICA)

### Amplitude-Based Rejection

| Parameter | Recommendation | Source |
|-----------|---------------|--------|
| Peak-to-peak threshold | **100 uV** within a sliding **200 ms** window | Luck, 2014 |
| Simple voltage threshold | **+/-75 uV** to **+/-100 uV** | Luck, 2014; Keil et al., 2014 |
| Step function (saccade detection) | **80 uV** step within **200 ms** window at HEOG channels | Luck, 2014, Ch. 5 |
| Flatline detection | < **0.5 uV** range within **100 ms** window | MNE-Python defaults |

### Rejection Rates

| Metric | Acceptable Range | Source |
|--------|-----------------|--------|
| Overall rejection rate | **< 25%** of epochs | Keil et al., 2014 |
| Minimum retained trials per condition | **>= 30** trials | Boudewyn et al., 2018 |
| Ideal retained trials per condition | **>= 40-50** trials for stable ERP estimates | Luck, 2014, Ch. 9 |
| If rejection rate > 30% | Recheck preprocessing parameters, ICA quality, or data quality | Keil et al., 2014 |

### Decision Logic

1. After ICA correction, most eye artifacts should already be removed
2. Apply amplitude-based rejection to catch remaining artifacts (muscle, movement, residual)
3. If rejection rate is too high:
 - First, check if ICA adequately removed eye artifacts
 - Then, consider slightly relaxing thresholds (e.g., **+/-125 uV**) if data quality is generally good (Luck, 2014)
 - Finally, if many epochs are contaminated, the participant may need to be excluded
4. Check for differential rejection rates across conditions -- imbalance > **20%** between conditions is concerning (Luck & Gaspelin, 2017)

---

## Processing Order: The Multiverse Problem

Different preprocessing choices can lead to different results. Lonedo et al. (2020) demonstrated that varying common preprocessing decisions produces a "multiverse" of possible outcomes. Key decision points with the largest impact:

### High-Impact Decisions

| Decision | Options | Impact | Source |
|----------|---------|--------|--------|
| High-pass cutoff | 0.01 Hz vs 0.1 Hz vs 0.5 Hz | Can create or eliminate slow component effects | Tanner et al., 2015 |
| Reference scheme | Average vs mastoids vs REST | Changes component topography and amplitude | Luck, 2014, Ch. 5 |
| ICA vs no ICA | ICA correction vs epoch rejection only | ICA preserves more trials; rejection may be more conservative | Luck, 2014, Ch. 5 |
| Baseline window | -200 to 0 vs -100 to 0 vs no baseline | Affects amplitude estimates for all components | Luck, 2014, Ch. 5 |
| Artifact threshold | 75 uV vs 100 uV vs 150 uV | Strictness-trial count tradeoff | Luck, 2014 |

### Recommendations for Robustness

1. **Pre-register** your exact preprocessing pipeline before data collection (Keil et al., 2014)
2. If exploratory, run **2-3 pipeline variants** and report whether results are consistent (Lonedo et al., 2020)
3. Use established, published pipelines (e.g., MADE pipeline: Debnath et al., 2020; HAPPE: Gabard-Durnam et al., 2018) rather than inventing your own
4. Report all preprocessing parameters in sufficient detail for replication (Keil et al., 2014)

---

## References

- Ablin, P., Cardoso, J. F., & Gramfort, A. (2018). Faster independent component analysis by preconditioning with Hessian approximations. *IEEE TSP*, 66(15), 4040-4049.
- Alday, P. M. (2019). How much baseline correction do we need in ERP research? *Brain Topography*, 32, 167-174.
- Alschuler, D. M., Tenke, C. E., Bruder, G. E., & Kayser, J. (2014). Identifying electrode bridging from electrical distance distributions. *Clinical Neurophysiology*, 125(3), 484-490.
- Bigdely-Shamlo, N., Mullen, T., Kothe, C., Su, K. M., & Robbins, K. A. (2015). The PREP pipeline. *Frontiers in Neuroinformatics*, 9, 16.
- Boudewyn, M. A., Luck, S. J., Farrens, J. L., & Kappenman, E. S. (2018). How many trials does it take to get a significant ERP effect? *Psychophysiology*, 55(6), e13049.
- Chaumon, M., Bishop, D. V., & Busch, N. A. (2015). A practical guide to the selection of independent components of the electroencephalogram for artifact correction. *Journal of Neuroscience Methods*, 250, 47-63.
- Debnath, R., Buzzell, G. A., Morales, S., Bowers, M. E., Leach, S. C., & Fox, N. A. (2020). The Maryland analysis of developmental EEG (MADE) pipeline. *Psychophysiology*, 57(6), e13580.
- Dong, L., Li, F., Liu, Q., Wen, X., Lai, Y., Xu, P., & Yao, D. (2017). MATLAB toolboxes for reference electrode standardization technique (REST). *Frontiers in Neuroscience*, 11, 601.
- Gabard-Durnam, L. J., et al. (2018). The Harvard Automated Processing Pipeline for EEG (HAPPE). *Frontiers in Neuroscience*, 12, 97.
- Kayser, J., & Tenke, C. E. (2006). Principal components analysis of Laplacian waveforms as a generic method for identifying ERP generator patterns. *Clinical Neurophysiology*, 117(2), 348-368.
- Keil, A., et al. (2014). Committee report: Publication guidelines for EEG and MEG. *Psychophysiology*, 51(1), 1-21.
- Lonedo, A., et al. (2020). The multiverse of ERP analysis pipelines. *NeuroImage*, 209, 116465.
- Luck, S. J. (2014). *An Introduction to the Event-Related Potential Technique* (2nd ed.). MIT Press.
- Makeig, S., Bell, A. J., Jung, T. P., & Sejnowski, T. J. (1996). Independent component analysis of electroencephalographic data. *NIPS*, 8, 145-151.
- McMenamin, B. W., Shackman, A. J., Maxwell, J. S., Bachhuber, D. R., Koppenhaver, A. M., Greischar, L. L., & Davidson, R. J. (2010). Validation of ICA-based myogenic artifact correction for scalp and source-localized EEG. *NeuroImage*, 49(3), 2416-2432.
- Mognon, A., Jovicich, J., Bruzzone, L., & Buiatti, M. (2011). ADJUST: An automatic EEG artifact detector based on the joint use of spatial and temporal features. *Psychophysiology*, 48(2), 229-240.
- Onton, J., & Makeig, S. (2006). Information-based modeling of event-related brain dynamics. *Progress in Brain Research*, 159, 99-120.
- Perrin, F., Pernier, J., Bertrand, O., & Echallier, J. F. (1989). Spherical splines for scalp potential and current density mapping. *Electroencephalography and Clinical Neurophysiology*, 72(2), 184-187.
- Pion-Tonachini, L., Kreutz-Delgado, K., & Makeig, S. (2019). ICLabel: An automated electroencephalographic independent component classifier. *NeuroImage*, 198, 181-197.
- Smith, N. J., & Kutas, M. (2015). Regression-based estimation of ERP waveforms. *Psychophysiology*, 52(2), 157-168.
- Tanner, D., Morgan-Short, K., & Luck, S. J. (2015). How inappropriate high-pass filters can produce artifactual effects. *Psychophysiology*, 52(8), 997-1009.
- Widmann, A., & Schroger, E. (2012). Filter effects and filter artifacts in the analysis of electrophysiological data. *Frontiers in Psychology*, 3, 233.
- Widmann, A., Schroger, E., & Maess, B. (2015). Digital filter design for electrophysiological data. *Journal of Neuroscience Methods*, 250, 34-46.
- Winkler, I., Debener, S., Muller, K. R., & Tangermann, M. (2015). On the influence of high-pass filtering on ICA-based artifact reduction in EEG-ERP. *Proceedings of the IEEE EMBC*, 4101-4105.
- Winkler, I., Haufe, S., & Tangermann, M. (2011). Automatic classification of artifactual ICA-components for artifact removal in EEG signals. *Behavioral and Brain Functions*, 7(1), 30.
- Yao, D. (2001). A method to standardize a reference of scalp EEG recordings to a point at infinity. *Physiological Measurement*, 22(4), 693-711.
