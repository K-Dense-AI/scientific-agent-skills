# Quality Control for fMRI Preprocessing

This reference document details the quality control (QC) metrics, thresholds, visual inspection procedures, and exclusion criteria for fMRI preprocessing. It supplements the core decision logic in `SKILL.md`.

---

## Overview: Why QC Matters

Preprocessing errors and poor-quality data propagate silently through the analysis pipeline. A subject with excessive motion can drive a spurious group-level activation. A failed normalization can mislocate activations by centimeters. Systematic QC at each preprocessing step is not optional — it is a prerequisite for valid fMRI results.

---

## Quantitative QC Metrics

### Framewise Displacement (FD)

FD quantifies instantaneous head motion as the sum of absolute values of the six rigid-body motion parameter derivatives, with rotations converted to millimeters on a **50 mm radius** sphere (Power et al., 2012).

**Calculation:**

```
FD(t) = |Δdx(t)| + |Δdy(t)| + |Δdz(t)| + |Δα(t)| + |Δβ(t)| + |Δγ(t)|
```

where Δdx, Δdy, Δdz are translation derivatives in mm, and Δα, Δβ, Δγ are rotation derivatives converted to mm (rotation in radians × 50 mm).

**Thresholds:**

| Context | FD Threshold | Action | Source |
|---|---|---|---|
| Task fMRI: volume flagging | > **0.5 mm** | Flag as spike; model as indicator regressor | Power et al., 2012 |
| Resting-state: volume censoring | > **0.2 mm** | Censor volume + 1 back + 2 forward | Power et al., 2014 |
| Subject exclusion (task) | Mean FD > **0.5 mm** OR > 20% volumes above threshold | Exclude subject from analysis | Power et al., 2012 |
| Subject exclusion (resting-state) | Mean FD > **0.2 mm** OR < **5 minutes** clean data remaining after scrubbing | Exclude subject | Power et al., 2014 |
| Intermediate threshold | > **0.3 mm** | Commonly used compromise | Siegel et al., 2014 |

**Domain insight**: The 0.2 mm vs. 0.5 mm choice is not arbitrary — it reflects the differential sensitivity of analyses to motion. Resting-state connectivity is more susceptible to motion artifacts than task activation because: (1) connectivity measures are sensitive to frame-to-frame signal changes, and (2) motion produces distance-dependent artifacts that mimic connectivity patterns (Power et al., 2012).

### DVARS (Derivative of RMS Variance over Voxels)

DVARS measures the rate of change of BOLD signal across the entire brain from one volume to the next (Power et al., 2012).

**Calculation:**

```
DVARS(t) = sqrt(mean((BOLD(t) - BOLD(t-1))^2))
```

where the mean is taken over all brain voxels.

**Thresholds:**

| Metric | Threshold | Action | Source |
|---|---|---|---|
| Standardized DVARS | > **1.5** (default fMRIPrep) | Flag volume | Nichols, 2017 (standardized DVARS) |
| Raw DVARS spike | Outlier detection (e.g., > median + 3.5 × MAD) | Flag volume | Afyouni & Nichols, 2018 |

**Domain insight**: DVARS and FD capture complementary information. FD detects motion from the realignment parameters (before correction), while DVARS detects the actual signal change in the data. A volume can have high FD but low DVARS (motion between frames that is well-corrected by realignment), or low FD but high DVARS (signal artifact not caused by rigid-body motion, such as a scanner spike or physiological artifact).

### Temporal Signal-to-Noise Ratio (tSNR)

tSNR is the voxel-wise mean signal divided by its standard deviation over time. It quantifies the stability of the time series and the ability to detect BOLD signal changes.

**Calculation:**

```
tSNR = mean(BOLD) / std(BOLD) (per voxel, over time)
```

**Expected Values and Thresholds:**

| Context | Typical tSNR | Minimum Acceptable | Source |
|---|---|---|---|
| Standard 3T, 3 mm voxels | **80-150** in gray matter | ~40 | Murphy et al., 2007; Triantafyllou et al., 2005 |
| Standard 3T, 2 mm voxels | **50-100** in gray matter | ~40 | Triantafyllou et al., 2005 |
| High-resolution (< 1.5 mm) | **30-60** in gray matter | ~30 | Triantafyllou et al., 2005 |
| Orbitofrontal / temporal (susceptibility) | **20-50** | Region-dependent | Expected lower due to signal dropout |

**Domain insight**: There is no single hard threshold for tSNR because it depends heavily on acquisition parameters (voxel size, TR, field strength, coil, multiband acceleration). The best practice is to compare tSNR across subjects within the same study and flag outliers (> 2 SD below the group mean). A whole-brain average tSNR below **40** at 3T with standard resolution warrants investigation.

**Spatial variation is expected**: tSNR is naturally lower near air-tissue interfaces (orbitofrontal cortex, temporal poles) and higher in occipital cortex and deep white matter. This is normal and does not indicate a problem unless the overall pattern is unusual.

---

## Visual QC Checklist

### Step-by-Step Visual Inspection

Each of the following checks should be performed for every subject. In large studies (N > 50), inspect all subjects automatically flagged by quantitative metrics plus a random sample of at least 10-20% of the remaining subjects.

#### 1. Brain Extraction (Skull-Stripping)

**What to look for:**
- [ ] Brain mask includes all gray and white matter
- [ ] No brain tissue is excluded (especially inferior temporal, orbitofrontal, cerebellum)
- [ ] No non-brain tissue is included (eyes, sinuses, skull, dura)

**Common failures:**
- Aggressive skull-stripping clips inferior temporal lobes or cerebellum
- Conservative skull-stripping includes dura or eye orbits
- Lesions or atrophy cause incorrect mask boundaries (especially in clinical populations)

#### 2. Motion Parameters

**What to look for:**
- [ ] No sudden jumps > 1 mm or 1 degree in translation/rotation traces
- [ ] Total displacement range < 3 mm translation and < 2 degrees rotation
- [ ] FD time series: proportion of spikes above threshold is acceptable
- [ ] No drift pattern suggesting slow, uncorrected subject movement (e.g., subject slowly sinking in scanner)

**Quantitative flags:**

| Metric | Good | Marginal | Exclude |
|---|---|---|---|
| Mean FD | < 0.2 mm | 0.2-0.5 mm | > 0.5 mm |
| Max FD | < 1.0 mm | 1.0-3.0 mm | > 5.0 mm |
| % Volumes with FD > 0.5 mm | < 5% | 5-20% | > 20% |
| Max absolute translation | < 2 mm | 2-3 mm | > voxel size |

#### 3. Coregistration (EPI to T1)

**What to look for:**
- [ ] White matter/gray matter boundaries in T1 align with boundaries in EPI
- [ ] Ventricle boundaries match
- [ ] Cortical ribbon in EPI overlaps cortical ribbon in T1
- [ ] No systematic shift in any direction

**Inspection method**: Overlay the EPI edge map on the T1 (or vice versa) and toggle between them. Use a checkerboard view or contour overlay.

#### 4. Spatial Normalization (to Template)

**What to look for:**
- [ ] Central sulcus aligns between subject and template
- [ ] Sylvian fissure matches
- [ ] Ventricle size and shape are reasonable (not over-shrunk or over-expanded)
- [ ] Subcortical structures (caudate, putamen, thalamus) overlap with template
- [ ] Cerebellum is correctly positioned
- [ ] No warping artifacts (crumpling, stretching) at brain edges

**Common failures:**
- Subjects with large ventricles (aging, hydrocephalus) may over-warp
- Subjects with lesions or tumors may fail normalization in affected regions
- Young children or infants require age-appropriate templates (not adult MNI)

#### 5. Distortion Correction

**What to look for:**
- [ ] Frontal pole is not compressed or stretched
- [ ] Temporal poles are not displaced
- [ ] Compare EPI overlay on T1 before and after distortion correction
- [ ] Symmetry is restored (left-right symmetry in EPI matches T1)

#### 6. Smoothing Verification

**What to look for:**
- [ ] Smoothing kernel appears appropriate (no excessive blurring or visible voxel edges)
- [ ] Brain edges are smooth but not eroded
- [ ] For MVPA: verify that NO smoothing was applied

---

## Carpet Plots (Gray Plots)

Carpet plots (Power, 2017) display the entire BOLD time series as a 2D image (voxels x time), with signal intensity as color. They are the single most informative QC visualization.

**How to read a carpet plot:**

| Feature | Appearance | Interpretation |
|---|---|---|
| Vertical striations (columns) | Bright or dark bands spanning many voxels | Motion artifact or global signal change at that time point |
| Horizontal bands | Persistent bright/dark rows | Consistently noisy voxels (e.g., edge voxels, vessels) |
| Smooth, featureless appearance | Uniform gray with no obvious structure | Good quality data (after preprocessing) |
| Structured patterns after denoising | Remaining bands or stripes | Incomplete confound removal |

**Tools for generating carpet plots:**
- fMRIPrep: Included in the visual report for every subject
- MRIQC: Included in the individual report
- Nilearn: `nilearn.plotting.plot_carpet()`
- Custom: Plot the 2D matrix of voxels (rows) x time points (columns)

---

## Automated QC Tools

### MRIQC (Esteban et al., 2017)

MRIQC extracts image quality metrics (IQMs) from structural and functional MRI data and generates visual reports.

**Key functional IQMs:**

| Metric | Description | What It Detects |
|---|---|---|
| **tSNR** | Temporal signal-to-noise ratio (median across brain) | Overall time series stability |
| **FD mean** | Mean framewise displacement | Average motion |
| **FD num** | Number of FD outliers | Number of motion spikes |
| **DVARS std** | Standardized DVARS mean | Average signal change rate |
| **GCOR** | Global correlation | Residual global signal; high values suggest motion contamination |
| **AOR** | AFNI outlier ratio | Proportion of outlier voxels per volume |
| **AQI** | AFNI quality index | Overall quality measure |
| **EFC** | Entropy focus criterion | Ghost artifacts; lower is better |
| **FBER** | Foreground-to-background energy ratio | Signal leakage outside brain mask |
| **GSR x/y** | Ghost-to-signal ratio (x and y) | EPI ghosting artifacts |

**Usage:**

```bash
# Run MRIQC on a BIDS dataset
mriqc bids_dir output_dir participant --participant-label 01
mriqc bids_dir output_dir group # generates group-level summary
```

**Domain insight**: MRIQC does not make accept/reject decisions for you. Its classifier has ~76% accuracy on unseen sites (Esteban et al., 2017). Use the IQMs as part of a multi-metric evaluation, not as a sole exclusion criterion.

### fMRIPrep Visual Reports

fMRIPrep generates comprehensive HTML reports for each subject, including:

- Brain mask overlay on T1 and EPI
- Coregistration overlay (EPI edges on T1)
- Normalization overlay (subject T1 on MNI template)
- Confound correlation matrix
- Carpet plot with FD, DVARS, and confound time series
- CompCor variance explained plots

**Inspection protocol**: For every subject, open the fMRIPrep HTML report and check:
1. Anatomical: brain mask, tissue segmentation, surface reconstruction
2. Functional: coregistration, normalization, susceptibility distortion correction
3. Confounds: carpet plot, FD/DVARS traces, correlation with confounds

---

## Exclusion Criteria by Analysis Type

### Task fMRI Exclusion Criteria

| Criterion | Threshold | Rationale | Source |
|---|---|---|---|
| Mean FD | > **0.5 mm** | Excessive overall motion | Power et al., 2012 |
| Max absolute motion | > **voxel size** (e.g., > 3 mm for 3 mm voxels) | Single large movement invalidates rigid-body correction | Poldrack et al., 2011 |
| % Volumes flagged (FD > 0.5 mm) | > **20%** of total volumes | Insufficient clean data for stable estimation | Common convention |
| Visual QC failure | Failed normalization, coregistration, or brain extraction | Invalid spatial mapping | Always required |
| tSNR (whole-brain median) | > 2 SD below group mean | Unusually noisy data | Within-study comparison |

### Resting-State Connectivity Exclusion Criteria

| Criterion | Threshold | Rationale | Source |
|---|---|---|---|
| Mean FD | > **0.2 mm** | Connectivity is highly sensitive to motion | Power et al., 2014 |
| Remaining data after scrubbing (FD > 0.2 mm) | < **5 minutes** (150 volumes at TR=2s) | Insufficient data for reliable connectivity | Power et al., 2014; Van Dijk et al., 2010 |
| Max FD spike | > **5 mm** | May indicate scanner error or subject non-compliance | Power et al., 2014 |
| GCOR (global correlation) after denoising | Outlier (> 2 SD above group mean) | Residual global artifacts | Saad et al., 2013 |
| Visual QC failure | Same as task | Same as task | Always required |

### MVPA Exclusion Criteria

| Criterion | Threshold | Rationale | Source |
|---|---|---|---|
| Mean FD | > **0.5 mm** | Same as task; motion can create decodable patterns (Todd et al., 2013) | Todd et al., 2013 |
| Verify no smoothing applied | FWHM = 0 mm | Smoothing destroys spatial patterns | Misaki et al., 2013 |
| Max motion within run | > **1 voxel** | Pattern information degrades with large motion | Common convention |
| Visual QC failure | Same as task | Same as task | Always required |

---

## QC Reporting Checklist

Based on COBIDAS guidelines (Nichols et al., 2017) and best practices:

For every fMRI study, report the following QC information:

- [ ] Number of subjects excluded and reasons for exclusion
- [ ] Motion summary statistics: group mean FD, range of mean FD across subjects
- [ ] Number and percentage of censored/scrubbed volumes (if applicable)
- [ ] Minimum remaining data per subject after scrubbing
- [ ] tSNR summary (group mean and range)
- [ ] QC tool used (MRIQC version, fMRIPrep version)
- [ ] Visual QC procedure: who inspected, what was checked, any standardized rating scale used
- [ ] Any subjects with noted but non-excluded QC issues (e.g., slight normalization imperfection in non-target region)

---

## Motion-Connectivity Confound: Special Considerations for Resting-State

Head motion creates systematic biases in functional connectivity that are NOT fully removed by standard motion regression (Power et al., 2012; Satterthwaite et al., 2012):

1. **Short-distance correlations are inflated**: Motion increases apparent connectivity between nearby regions
2. **Long-distance correlations are reduced**: Motion decreases apparent connectivity between distant regions
3. **Network structure is distorted**: Default mode network appears more connected; attention networks appear less connected
4. **Group differences in motion mimic group differences in connectivity**: If patients move more than controls, motion artifacts masquerade as disease-related connectivity differences

### Recommended Mitigation Strategies

In order of increasing aggressiveness (Ciric et al., 2017):

| Strategy | Description | Effectiveness | Reference |
|---|---|---|---|
| 24-parameter motion regression | 6 motion + 6 derivatives + 12 squared terms | Moderate | Friston et al., 1996 |
| + aCompCor (5-6 components) | Add WM/CSF noise components | Good | Behzadi et al., 2007 |
| + Scrubbing (FD > 0.2 mm) | Censor high-motion volumes | Good | Power et al., 2014 |
| + Global signal regression | Regress whole-brain mean signal | Best motion removal, but introduces anticorrelations | Murphy & Fox, 2017 |
| ICA-AROMA | Automated ICA-based denoising | Good; preserves temporal DOF | Pruim et al., 2015 |

**Domain warning**: No single strategy perfectly eliminates motion confounds. The Ciric et al. (2017) benchmarking study compared 14 confound regression pipelines and found that the most effective strategies combined aggressive confound regression with scrubbing. However, all strategies involve trade-offs between motion removal and signal preservation.

### Verifying Motion Decontamination

After confound regression, check that the distance-dependence of connectivity is eliminated:

1. Compute QC-FC correlations: for each edge in the connectivity matrix, correlate the edge strength across subjects with the subjects' mean FD
2. **Expected result**: QC-FC correlations should be near zero (median |r| < 0.1) after adequate denoising
3. If significant QC-FC correlations persist, the denoising strategy is insufficient

---

## Key References

- Afyouni, S., & Nichols, T. E. (2018). Insight and inference for DVARS. *NeuroImage*, 172, 291-312.
- Behzadi, Y., Restom, K., Liau, J., & Liu, T. T. (2007). A component based noise correction method (CompCor). *NeuroImage*, 37(1), 90-101.
- Ciric, R., Wolf, D. H., Power, J. D., et al. (2017). Benchmarking of participant-level confound regression strategies. *NeuroImage*, 154, 174-187.
- Esteban, O., Birman, D., Schaer, M., et al. (2017). MRIQC: Advancing the automatic prediction of image quality in MRI from unseen sites. *PLoS ONE*, 12(9), e0184661.
- Friston, K. J., Williams, S., Howard, R., et al. (1996). Movement-related effects in fMRI time-series. *Magnetic Resonance in Medicine*, 35(3), 346-355.
- Misaki, M., Luh, W. M., & Bandettini, P. A. (2013). The effect of spatial smoothing on fMRI decoding. *NeuroImage*, 78, 13-22.
- Murphy, K., Bodurka, J., & Bandettini, P. A. (2007). How long to scan? The relationship between fMRI temporal signal to noise ratio and necessary scan duration. *NeuroImage*, 34(2), 565-574.
- Murphy, K., & Fox, M. D. (2017). Towards a consensus regarding global signal regression. *NeuroImage*, 154, 169-173.
- Nichols, T. E., Das, S., Eickhoff, S. B., et al. (2017). Best practices in data analysis and sharing in neuroimaging using MRI (COBIDAS). *Nature Neuroscience*, 20(3), 299-303.
- Poldrack, R. A., Mumford, J. A., & Nichols, T. E. (2011). *Handbook of Functional MRI Data Analysis*. Cambridge University Press.
- Power, J. D. (2017). A simple but useful way to assess fMRI scan qualities. *NeuroImage*, 154, 150-158.
- Power, J. D., Barnes, K. A., Snyder, A. Z., et al. (2012). Spurious but systematic correlations in functional connectivity MRI networks arise from subject motion. *NeuroImage*, 59(3), 2142-2154.
- Power, J. D., Mitra, A., Laumann, T. O., et al. (2014). Methods to detect, characterize, and remove motion artifact in resting state fMRI. *NeuroImage*, 84, 320-341.
- Pruim, R. H. R., Mennes, M., van Rooij, D., et al. (2015). ICA-AROMA: A robust ICA-based strategy for removing motion artifacts from fMRI data. *NeuroImage*, 112, 267-277.
- Saad, Z. S., Gotts, S. J., Murphy, K., et al. (2013). Trouble at rest: how correlation patterns and group differences become distorted after global signal regression. *Brain Connectivity*, 2(1), 25-32.
- Satterthwaite, T. D., Wolf, D. H., Loughead, J., et al. (2012). Impact of in-scanner head motion on multiple measures of functional connectivity. *NeuroImage*, 60(1), 623-632.
- Siegel, J. S., Power, J. D., Dubis, J. W., et al. (2014). Statistical improvements in functional magnetic resonance imaging analyses produced by censoring high-motion data points. *Human Brain Mapping*, 35(5), 1981-1996.
- Todd, M. T., Nystrom, L. E., & Cohen, J. D. (2013). Confounds in multivariate pattern analysis: Theory and rule representation case study. *NeuroImage*, 77, 157-165.
- Triantafyllou, C., Hoge, R. D., Krueger, G., et al. (2005). Comparison of physiological noise at 1.5 T, 3 T and 7 T and optimization of fMRI acquisition parameters. *NeuroImage*, 26(1), 243-250.
- Van Dijk, K. R. A., Sabuncu, M. R., & Buckner, R. L. (2012). The influence of head motion on intrinsic functional connectivity MRI. *NeuroImage*, 59(1), 431-438.
