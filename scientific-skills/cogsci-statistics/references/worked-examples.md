# Simulation-Based Power Analysis: Worked Examples

## Overview

This reference provides worked examples of simulation-based power analysis for common neuroimaging study designs, expanding on the methodology described in `../SKILL.md`.

## Example 1: Within-Subject Task Activation (fMRI)

### Scenario

A researcher plans to study the neural correlates of cognitive control using a Stroop task. The primary analysis is a whole-brain within-subject contrast (incongruent > congruent). Pilot data from N=12 subjects are available.

### Step 1: Extract Effect Size from Pilot

From the pilot group-level t-map (incongruent > congruent):
- Peak voxel in dorsal ACC: t(11) = 4.2, Cohen's d = 4.2 / sqrt(12) = **1.21**
- Peak voxel in left dlPFC: t(11) = 3.5, Cohen's d = 3.5 / sqrt(12) = **1.01**
- Mean d across ACC ROI: **0.85**

### Step 2: Apply Conservative Deflation

Small pilot (N=12), so apply 50% deflation (Button et al., 2013):
- Conservative ACC d estimate: 0.85 * 0.50 = **0.43**
- Conservative dlPFC d estimate: 1.01 * 0.50 = **0.51**

### Step 3: ROI-Based Power (Quick Estimate)

Using G*Power for a one-sample t-test (two-tailed):
- d = 0.43, alpha = 0.05, power = 0.80
- Required N = **35**
- Add 15% attrition: Final planned N = **41**

### Step 4: Simulation-Based Power (Full Analysis)

Using fMRIpower or custom simulation:
1. Use pilot residuals to estimate noise characteristics
2. Simulate 2,000 group maps at each candidate N (10, 15, 20, 25, 30, 35, 40, 50)
3. Apply cluster-based correction (CDT p < 0.001, cluster p < 0.05 FWE)
4. Count proportion of simulations with a significant cluster in the ACC/dlPFC region

### Expected Power Curve

| N | Power (ROI) | Power (Whole-Brain Cluster) |
|---|---|---|
| 15 | 38% | 22% |
| 20 | 52% | 35% |
| 25 | 65% | 48% |
| 30 | 76% | 60% |
| 35 | 84% | 70% |
| 40 | 90% | 78% |
| 50 | 96% | 88% |

**Decision**: Target N = 40 (with 15% attrition buffer, recruit 46 participants).

Values are illustrative based on typical parameters from Mumford & Nichols (2008).

## Example 2: Between-Group Comparison (Patients vs. Controls)

### Scenario

A researcher plans to compare amygdala reactivity to emotional faces between patients with social anxiety disorder and healthy controls. Published studies report d = 0.6-0.8 for amygdala group differences.

### Step 1: Effect Size Estimate

Using the meta-analytic estimate (conservative):
- Published meta-analytic d = 0.7 (Etkin & Wager, 2007)
- Apply 25% deflation: d = 0.7 * 0.75 = **0.53**

### Step 2: ROI-Based Power

Using G*Power for an independent samples t-test (two-tailed):
- d = 0.53, alpha = 0.05, power = 0.80
- Required N per group = **58**
- Add 15% attrition: Final planned N = **67 per group**

### Step 3: Sensitivity Analysis

At the planned N = 58 per group, what is the minimum detectable effect?
- Minimum detectable d (80% power, alpha = 0.05) = **0.53**

If the true effect is only d = 0.3 (plausible for clinical samples):
- Power at N = 58 per group = **33%** (inadequate)
- Required N for d = 0.3 at 80% power = **176 per group**

**Conclusion**: If the effect could be as small as d = 0.3, a much larger sample or multi-site study is needed.

## Example 3: Brain-Behavior Correlation

### Scenario

A researcher wants to correlate trait anxiety scores with amygdala connectivity strength during an emotion task.

### Step 1: Effect Size Estimate

Brain-behavior correlations are typically small (Marek et al., 2022):
- Expected r = 0.2-0.3 (optimistic for a single ROI)
- Conservative estimate: r = 0.15

### Step 2: ROI-Based Power

For a Pearson correlation test:
- r = 0.15, alpha = 0.05, power = 0.80
- Required N = **346**

For a more optimistic r = 0.25:
- Required N = **123**

### Step 3: Whole-Brain Considerations

If searching for brain-behavior correlations across the whole brain:
- Marek et al. (2022) showed that N > 2,000 is needed for replicable whole-brain brain-behavior associations
- This is far beyond the budget of most single-site studies
- **Recommendation**: Use a priori ROIs or join large-scale consortia (ABCD, HCP, UK Biobank)

## Example 4: ERP Study Power Analysis

### Scenario

A researcher plans to study the N400 effect (semantically anomalous > expected) in patients with schizophrenia vs. controls.

### Step 1: Effect Size Estimate

- Within-subject N400 effect: d = 0.5-1.0 (Kutas & Federmeier, 2011)
- Between-group difference in N400: d = 0.4-0.6 (meta-analytic; Kiang et al., 2012)
- Conservative between-group estimate: d = 0.4

### Step 2: Trial Count Planning

- Minimum trials per condition: **30** post-rejection (Boudewyn et al., 2018)
- Expected rejection rate: 25% for patients (more artifacts)
- Required presented trials: 30 / 0.75 = **40 per condition**
- Design: 80 trials per condition (comfortable margin)

### Step 3: Subject-Level Power

Using G*Power for an independent samples t-test:
- d = 0.4, alpha = 0.05, power = 0.80
- Required N per group = **100**

For a within-subject N400 effect at d = 0.7:
- Required N = **19** per group (but this is only for the within-subject effect, not the group comparison)

**Recommendation**: For the between-group comparison at d = 0.4, plan for **50-60 per group** as a pragmatic compromise (acknowledging this provides only ~60% power). Consider multi-site collaboration for full 80% power.

## Simulation Code Template (Python/Nilearn)

### Pseudocode for fMRI Power Simulation

```
# Pseudocode -- not executable without actual data
# Illustrates the logic of simulation-based power analysis

import numpy as np
from nilearn import image

def simulate_power(pilot_effect_map, pilot_residual_std_map,
 smoothness_fwhm, candidate_Ns, n_simulations,
 correction_method, alpha, roi_mask):
 """
 Parameters:
 - pilot_effect_map: 3D array of estimated effect sizes (Cohen's d) at each voxel
 - pilot_residual_std_map: 3D array of estimated noise SD at each voxel
 - smoothness_fwhm: estimated spatial smoothness in mm
 - candidate_Ns: list of sample sizes to evaluate
 - n_simulations: number of simulations per N (recommend 1000-5000)
 - correction_method: 'cluster', 'fwe', 'fdr', or 'tfce'
 - alpha: significance level (typically 0.05)
 - roi_mask: binary mask for the target ROI

 Returns:
 - power_by_N: dict mapping N to power estimate
 """

 power_by_N = {}

 for N in candidate_Ns:
 detections = 0

 for sim in range(n_simulations):
 # Step 1: Generate N subject-level contrast maps
 # Each subject map = true_effect + noise
 # noise ~ N(0, residual_std / sqrt(n_trials))
 group_data = []
 for subj in range(N):
 noise = np.random.randn(*pilot_effect_map.shape)
 noise = smooth(noise, smoothness_fwhm)
 noise *= pilot_residual_std_map
 subj_map = pilot_effect_map + noise
 group_data.append(subj_map)

 # Step 2: Compute group t-map
 group_mean = np.mean(group_data, axis=0)
 group_se = np.std(group_data, axis=0) / np.sqrt(N)
 t_map = group_mean / group_se

 # Step 3: Apply multiple comparison correction
 sig_map = apply_correction(t_map, correction_method, alpha,
 smoothness_fwhm)

 # Step 4: Check if effect detected in ROI
 if np.any(sig_map[roi_mask > 0]):
 detections += 1

 power_by_N[N] = detections / n_simulations

 return power_by_N
```

**Note**: This pseudocode illustrates the logic. For actual implementation, use fMRIpower (Mumford & Nichols, 2008), NeuroPowerTools (Durnez et al., 2016), or nilearn/nipype simulation pipelines.

## References

- Boudewyn, M. A., Luck, S. J., Farrens, J. L., & Kappenman, E. S. (2018). How many trials does it take to get a significant ERP effect? *Psychophysiology*, 55(6), e13049.
- Button, K. S., Ioannidis, J. P. A., Mokrysz, C., et al. (2013). Power failure. *Nature Reviews Neuroscience*, 14(5), 365-376.
- Durnez, J., Degryse, J., Moerkerke, B., et al. (2016). Power and sample size calculations for fMRI studies based on the prevalence of active peaks. *bioRxiv*, 049429.
- Etkin, A., & Wager, T. D. (2007). Functional neuroimaging of anxiety: A meta-analysis. *American Journal of Psychiatry*, 164(10), 1476-1488.
- Kiang, M., Kutas, M., Light, G. A., & Braff, D. L. (2012). An event-related brain potential study of the N400 in schizophrenia. *Schizophrenia Research*, 137(1-3), 21-28.
- Kutas, M., & Federmeier, K. D. (2011). Thirty years and counting: Finding meaning in the N400. *Annual Review of Psychology*, 62, 621-647.
- Marek, S., Tervo-Clemmens, B., Calabro, F. J., et al. (2022). Reproducible brain-wide association studies require thousands of individuals. *Nature*, 603(7902), 654-660.
- Mumford, J. A., & Nichols, T. E. (2008). Power calculation for group fMRI studies. *NeuroImage*, 39(1), 261-268.
