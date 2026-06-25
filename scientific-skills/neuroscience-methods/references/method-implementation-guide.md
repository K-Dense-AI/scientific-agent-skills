# Brain Connectivity Method Implementation Details

## Overview

This reference provides detailed implementation guidance for each connectivity method described in `../SKILL.md`.

## PPI Step-by-Step Implementation

### Standard PPI (SPM-style)

1. **Define seed ROI**: Use an independent functional localizer or anatomical atlas to define the seed region. Typical sphere radius: **6-10 mm** centered on peak coordinate (O'Reilly et al., 2012)

2. **Extract time series**: Extract the first eigenvariate from all voxels within the seed ROI that survive a liberal threshold (e.g., p < 0.05 uncorrected at the subject level). The eigenvariate is preferred over the mean because it captures the dominant signal pattern (Stephan et al., 2010)

3. **Deconvolve the HRF**: Estimate the underlying neural signal by deconvolving the HRF from the BOLD time series. This step is critical because the interaction must occur at the neural level, not the hemodynamic level (Gitelman et al., 2003)

4. **Create interaction term**: Multiply the deconvolved neural signal (physiological) by the task regressor (psychological), then reconvolve with the HRF

5. **Specify GLM**: Include three regressors:
 - Seed time series (physiological)
 - Task regressor (psychological)
 - PPI interaction term
 - Plus all standard confound regressors

6. **Test the interaction**: The PPI interaction term tests whether the coupling between the seed and target changes with task context. A positive PPI means coupling increases during the contrast condition; a negative PPI means coupling decreases

### gPPI Implementation (McLaren et al., 2012)

1. Steps 1-3 same as standard PPI
2. Create separate PPI interaction terms for **each** task condition (not just the contrast of interest)
3. Include in GLM:
 - Seed time series
 - All task condition regressors
 - One PPI interaction per condition
 - Confound regressors
4. Form contrasts on the PPI interaction terms (e.g., PPI_condA > PPI_condB)

**Advantage over standard PPI**: gPPI properly models the variance from all conditions simultaneously, reducing residual variance and increasing sensitivity (McLaren et al., 2012).

## DCM Model Construction Guide

### Step 1: Select Regions

- Choose **3-8 regions** based on prior literature and/or functional activation (Stephan et al., 2010)
- All regions must show significant task-related activation in the first-level GLM
- Extract the first eigenvariate from each region (VOI extraction in SPM)
- Regions should be defined with a sphere of **6-8 mm** radius centered on the group peak or subject-specific peak

### Step 2: Define Model Space

Construct candidate models by systematically varying:

| Component | Variations |
|---|---|
| A matrix (intrinsic connections) | Which regions are connected at baseline? Include at minimum the connections supported by anatomical tracing or diffusion imaging |
| B matrix (modulatory effects) | Which connections are modulated by experimental conditions? This is typically the hypothesis being tested |
| C matrix (driving inputs) | Which regions receive direct task input? Usually sensory regions for perceptual tasks, or regions known to initiate task processing |

**Model space reduction strategies**:
- Fix the A matrix across all models (use the most comprehensive plausible connectivity pattern)
- Vary only the B matrix (which connections are modulated) to test specific hypotheses
- Use family-level inference to compare model families (Penny et al., 2010)

### Step 3: Estimate and Compare

1. Estimate all models using variational Laplace (SPM default)
2. Compute log model evidence (free energy approximation) for each model
3. Apply Bayesian model selection:
 - FFX-BMS for homogeneous samples
 - RFX-BMS for heterogeneous samples (Stephan et al., 2009)
4. Report exceedance probability and protected exceedance probability (Rigoux et al., 2014)

## Graph Theory Implementation

### Step-by-Step Pipeline

1. **Parcellation**: Apply an atlas (Schaefer, Gordon, AAL) to extract mean time series from each parcel
2. **Compute connectivity matrix**: Pearson correlation between all pairs of parcels
3. **Threshold**: Apply proportional threshold (e.g., keep top **10%, 15%, 20%** of connections) or absolute threshold (e.g., r > **0.2**)
4. **Binarize or keep weighted**: Binary graphs simplify interpretation; weighted graphs preserve connection strength information (Rubinov & Sporns, 2010)
5. **Compute graph metrics**: See metric definitions in `../SKILL.md`
6. **Normalize against null models**: Generate **1,000+** random networks preserving degree distribution (Maslov & Sneppen, 2002) and compute the same metrics

### Recommended Graph Analysis Software

| Tool | Language | Features | Source |
|---|---|---|---|
| Brain Connectivity Toolbox (BCT) | MATLAB/Python | Comprehensive graph metrics | Rubinov & Sporns, 2010 |
| NetworkX | Python | General graph analysis | Hagberg et al., 2008 |
| GRETNA | MATLAB (GUI) | Network analysis for neuroimaging | Wang et al., 2015 |
| BrainNetViewer | MATLAB | Network visualization | Xia et al., 2013 |

### Threshold Sensitivity Analysis

Because graph metrics depend strongly on the threshold used, always:

1. Compute metrics across a range of thresholds (e.g., proportional thresholds from **5% to 40%** in **5%** steps)
2. Plot metric values as a function of threshold density
3. Report whether group differences or correlations are consistent across thresholds
4. Use area-under-the-curve (AUC) across thresholds as a summary measure (van den Heuvel et al., 2017)

## References

- Gitelman, D. R., Penny, W. D., Ashburner, J., & Friston, K. J. (2003). Modeling regional and psychophysiologic interactions in fMRI. *NeuroImage*, 19(1), 200-207.
- Hagberg, A. A., Schult, D. A., & Swart, P. J. (2008). Exploring network structure, dynamics, and function using NetworkX. In *Proceedings of the 7th Python in Science Conference*, 11-15.
- Maslov, S., & Sneppen, K. (2002). Specificity and stability in topology of protein networks. *Science*, 296(5569), 910-913.
- McLaren, D. G., Ries, M. L., Xu, G., & Johnson, S. C. (2012). A generalized form of context-dependent psychophysiological interactions (gPPI). *NeuroImage*, 61(4), 1277-1286.
- O'Reilly, J. X., Woolrich, M. W., Behrens, T. E. J., et al. (2012). Tools of the trade: Psychophysiological interactions and functional connectivity. *Social Cognitive and Affective Neuroscience*, 7(5), 604-609.
- Penny, W. D., Stephan, K. E., Daunizeau, J., et al. (2010). Comparing families of dynamic causal models. *PLoS Computational Biology*, 6(3), e1000709.
- Rigoux, L., Stephan, K. E., Friston, K. J., & Daunizeau, J. (2014). Bayesian model selection for group studies revisited. *NeuroImage*, 84, 971-985.
- Rubinov, M., & Sporns, O. (2010). Complex network measures of brain connectivity: Uses and interpretations. *NeuroImage*, 52(3), 1059-1069.
- Stephan, K. E., Penny, W. D., Daunizeau, J., et al. (2009). Bayesian model selection for group studies. *NeuroImage*, 46(4), 1004-1017.
- Stephan, K. E., Penny, W. D., Moran, R. J., et al. (2010). Ten simple rules for dynamic causal modelling. *NeuroImage*, 49(4), 3099-3109.
- van den Heuvel, M. P., de Lange, S. C., Zalesky, A., et al. (2017). Proportional thresholding in resting-state fMRI functional connectivity networks. *NeuroImage*, 159, 437-449.
- Wang, J., Wang, X., Xia, M., et al. (2015). GRETNA: A graph theoretical network analysis toolbox for imaging connectomics. *Frontiers in Human Neuroscience*, 9, 386.
- Xia, M., Wang, J., & He, Y. (2013). BrainNet Viewer: A network visualization tool for human brain connectomics. *PLoS ONE*, 8(7), e68910.
