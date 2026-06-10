# Statistical Inference for fMRI GLM Results

## Overview

After fitting the GLM and computing contrast maps, the resulting statistical images (typically z-maps or t-maps) must be thresholded to identify statistically significant activations. Because approximately **100,000 voxels** are tested simultaneously, correction for multiple comparisons is essential (Poldrack et al., 2011, Ch. 6).

This reference provides detailed guidance on each correction method, its assumptions, strengths, and weaknesses.

## The Multiple Comparisons Problem

At a nominal alpha of 0.05, testing 100,000 voxels produces approximately **5,000 false positives** if no correction is applied. Two families of correction exist:

1. **Family-Wise Error Rate (FWE/FWER)**: Controls the probability of any false positive across all voxels. More conservative; fewer false positives, more false negatives
2. **False Discovery Rate (FDR)**: Controls the expected proportion of false positives among significant results. Less conservative; more discoveries, but some proportion are expected to be false

## Voxelwise Correction Methods

### Random Field Theory (RFT) FWE

**Method**: Uses the smoothness of the statistical map to estimate the number of independent tests (resolution elements, or "resels"), then applies a correction based on the expected Euler characteristic of the thresholded random field (Worsley et al., 1996).

**Assumptions** (all must be met):
- Data are sufficiently smooth (FWHM of smoothness > **3x voxel size**; Worsley et al., 1996)
- The error fields are a good lattice approximation to a continuous Gaussian random field
- The smoothness estimate is accurate (requires > **20 degrees of freedom** for reliable estimation; Worsley et al., 1996)

**When to use**: When you expect highly localized activations and need the strictest control of false positives.

**Typical threshold**: p < 0.05, FWE-corrected (corresponds to z > approximately **4.5-5.0** for typical whole-brain analyses).

**Limitations**: Very conservative; may miss real but distributed effects.

### Bonferroni Correction

**Method**: Divides the alpha level by the number of tests (voxels). Threshold = 0.05 / n_voxels.

**When to use**: When you have a small number of tests (e.g., a few pre-specified ROIs). For whole-brain analysis, this is excessively conservative because it ignores spatial correlation (the data are smooth, so neighboring voxels are not independent).

**Typical threshold**: For 100,000 voxels, p < 0.0000005 (z > 4.93). This is slightly more conservative than RFT-FWE because it does not account for smoothness.

### False Discovery Rate (FDR)

**Method**: The Benjamini-Hochberg procedure ranks all voxel p-values and applies an adaptive threshold such that the expected proportion of false positives among rejected voxels is controlled at q (Benjamini & Hochberg, 1995; Genovese et al., 2002).

**Advantages:**
- More powerful than FWER methods when effects are distributed across many voxels
- Adaptive: the threshold adjusts based on the signal present in the data
- Does not require assumptions about smoothness

**When to use**: When you expect distributed activations across many brain regions and can tolerate a known proportion of false positives.

**Typical threshold**: q < 0.05 (5% of detected voxels are expected to be false positives).

**Limitations**: The actual threshold depends on the data, so it cannot be predicted in advance. When signal is sparse, FDR can be as conservative as FWE.

## Cluster-Based Inference

### How It Works

Cluster-based inference is a two-stage procedure:

1. **Stage 1 -- Cluster-defining threshold (CDT)**: Threshold the statistical map at an uncorrected p-value (e.g., p < 0.001). This defines contiguous clusters of suprathreshold voxels
2. **Stage 2 -- Cluster-level correction**: For each cluster, compute the probability of observing a cluster of that size (or larger) by chance, given the estimated smoothness. Retain only clusters with corrected p < 0.05

### The Critical CDT Choice

The CDT is the most consequential decision in cluster-based inference. **This is where many fMRI analyses go wrong.**

| CDT | Validity | False Positive Rate | Source |
|---|---|---|---|
| p < 0.001 | Valid | Near nominal (5%) for parametric methods | Eklund et al., 2016 |
| p < 0.01 | **Invalid** | **Up to 60-70%** instead of 5% | Eklund et al., 2016 |
| p < 0.05 | **Severely invalid** | Dramatically inflated | Eklund et al., 2016 |

**The Eklund et al. (2016) findings**: Using resting-state fMRI data from 499 healthy controls to create null (no-task) datasets, the authors performed 3 million task group analyses across SPM, FSL, and AFNI. They found that parametric cluster-based inference with a CDT of p < 0.01 produced false positive rates up to **70%** (instead of the nominal 5%). With a CDT of p < 0.001, false positive rates were much closer to nominal, though still somewhat inflated in some software packages (Eklund et al., 2016).

**Mandatory practice**: Always use a CDT of **p < 0.001** (uncorrected) or stricter for cluster-based inference. The commonly used CDT of p < 0.01 is demonstrably invalid.

### Cluster-Based Inference Limitations

Even with valid CDT, cluster-based inference has inherent limitations:

1. **No spatial specificity within clusters**: A significant cluster only tells you that the cluster as a whole is unlikely to have occurred by chance. Individual voxels within the cluster are not individually significant (Woo et al., 2014)
2. **Bias toward large clusters**: Large, diffuse activations are more likely to be detected than small, focal activations, regardless of effect size
3. **Non-stationarity**: The smoothness of fMRI data varies across the brain (e.g., more smoothing near sulci). Standard cluster-based inference assumes uniform smoothness, which can inflate false positives in smooth regions and reduce power in less smooth regions (Worsley et al., 1999)

## Threshold-Free Cluster Enhancement (TFCE)

### Method

TFCE (Smith & Nichols, 2009) avoids the arbitrary CDT by integrating cluster-like information across all possible thresholds. For each voxel, the TFCE score aggregates the extent (cluster size) and height (statistical value) of the cluster containing that voxel at every possible threshold level.

The TFCE-transformed image is then submitted to permutation testing to obtain FWE-corrected p-values for each voxel.

### Parameters

The TFCE transformation uses two exponents:
- **E** (extent weight): default = **0.5** (Smith & Nichols, 2009)
- **H** (height weight): default = **2.0** (Smith & Nichols, 2009)

These defaults were chosen to approximate the sensitivity of cluster-based inference while providing voxelwise specificity (Smith & Nichols, 2009).

### Advantages

- No arbitrary cluster-forming threshold
- Provides voxelwise inference (unlike cluster-based methods)
- Generally more sensitive than both voxelwise and cluster-based RFT approaches across a range of signal shapes (Smith & Nichols, 2009)
- Combined with permutation testing, makes no distributional assumptions

### Limitations

- Requires permutation testing (computationally expensive)
- The E and H parameters, while empirically justified, are still somewhat arbitrary
- Less widely implemented than parametric cluster-based methods (primarily available in FSL's randomise and standalone implementations)

### When to Use

TFCE is recommended as the default method when:
- Permutation testing is computationally feasible
- You want both sensitivity and spatial specificity
- You want to avoid choosing an arbitrary CDT

## Permutation Testing

### Method

Nonparametric permutation testing (Nichols & Holmes, 2002) generates the null distribution empirically by permuting the data (e.g., randomly flipping sign of contrast maps in a one-sample test, or shuffling group labels in a two-sample test), re-computing the test statistic under each permutation, and comparing the observed statistic to this null distribution.

### Number of Permutations

| Number of Permutations | Use Case | Source |
|---|---|---|
| 500 | Preliminary exploration only | Nichols & Holmes, 2002 |
| 1,000 | Minimum for any reported result | Nichols & Holmes, 2002 |
| 5,000 | Standard for publication | Nichols & Holmes, 2002 |
| 10,000 | Gold standard; gives stable p-values at p = 0.05 | Nichols & Holmes, 2002 |

**Domain insight**: With N permutations, the minimum achievable p-value is 1/(N+1). For 500 permutations, the minimum p-value is approximately 0.002, which is fine for detecting strong effects but insufficient for very stringent thresholds. For publication-quality results, use at least **5,000 permutations** (Nichols & Holmes, 2002).

### Advantages

- No assumptions about the noise distribution (valid even when parametric assumptions are violated)
- Controls FWE exactly (not approximately)
- Can be combined with any test statistic (voxelwise, cluster-based, TFCE)
- Gold standard for validation of parametric methods

### Limitations

- Computationally expensive (especially for large datasets)
- Requires exchangeability under the null hypothesis (met for most group analyses but not for within-subject time series)
- For one-sample tests, requires sign-flipping; sample size should be at least **12-15 subjects** for a reasonable number of unique permutations (with n subjects, there are 2^n sign-flip permutations; n=12 gives 4,096 permutations; Nichols & Holmes, 2002)

### Software Implementation

| Software | Tool | Permutation Types |
|---|---|---|
| FSL | randomise | Voxelwise, cluster, TFCE; sign-flipping, group shuffling |
| Nilearn | non_parametric_inference | Sign-flipping for second-level models |
| SnPM (SPM extension) | SnPM | Voxelwise and cluster permutation |
| PALM (FSL extension) | palm | Multi-modal permutation with TFCE support |

## Region of Interest (ROI) Analysis

ROI analysis tests hypotheses in pre-specified brain regions, reducing the multiple comparisons burden.

### Approaches

#### A Priori ROI (Preferred)

Define ROIs based on prior literature or anatomical atlases before analyzing the data.

| ROI Source | Approach | Advantages |
|---|---|---|
| Anatomical atlas | Use standard atlases (AAL, Harvard-Oxford, Desikan-Killiany) | Reproducible, unbiased |
| Prior study coordinates | Spherical ROI around published peak coordinate (radius **6-10 mm**; Poldrack et al., 2011, Ch. 6) | Theory-driven |
| Functional localizer | Independent scan to identify functional region (e.g., FFA from face localizer) | Individually tailored |

**Typical sphere radius**: **6-8 mm** for cortical regions, **4-6 mm** for subcortical structures (smaller due to smaller structures; Poldrack et al., 2011, Ch. 6).

#### Leave-One-Subject-Out (LOSO) ROI

When no independent localizer is available, define the ROI from the group analysis excluding the subject to be tested:

1. Run the group analysis N times, each time leaving out one subject
2. For each iteration, define the ROI from the N-1 group map
3. Extract the left-out subject's data from this independently defined ROI
4. Test effects on the extracted values

This avoids circularity while using data-driven ROI definition (Esterman et al., 2010).

#### Functional Localizer

An independent scanning run designed to identify a specific functional region (e.g., fusiform face area, motion-selective area MT+; Saxe et al., 2006).

**Domain warning**: Even functional localizers require a threshold choice, and the ROI definition can influence results. Report the contrast, threshold, and minimum cluster size used to define the ROI.

### ROI Correction

Within-ROI analysis still requires correction if multiple voxels within the ROI are tested:
- **Small volume correction (SVC)**: Apply RFT-FWE correction within the ROI volume only (Worsley et al., 1996)
- **Mean extraction**: Average the parameter estimate or contrast value across all voxels in the ROI, producing a single value per subject. Then test this single value with a standard t-test. No multiple comparison correction is needed because there is one test per ROI (Poldrack et al., 2011, Ch. 6)
- **If testing multiple ROIs**: Apply Bonferroni or FDR correction across the number of ROIs tested

### Avoiding Circular ROI Selection

As established by Kriegeskorte et al. (2009), defining an ROI based on the same contrast you intend to test creates circular (non-independent) analysis. This inflates effect sizes and produces invalid p-values.

**Valid approaches:**
- A priori anatomical ROIs
- Functional localizer from independent data
- LOSO procedure
- Orthogonal contrast for ROI definition (e.g., define ROI by main effect of task, test interaction within that ROI)

**Invalid approaches:**
- Select voxels based on Condition A > B, then test Condition A > B in those voxels (inflated effect)
- Use the group t-map to define "activated" regions, then report mean activation in those regions

## Decision Tree: Choosing an Inference Method

```
What is your primary research question?
 |
 +-- Specific ROI hypothesis (e.g., "is hippocampus active?")
 | |
 | +-- A priori ROI available?
 | |
 | +-- YES --> Extract mean from ROI, simple t-test (no MCP needed)
 | | OR small volume correction within ROI
 | |
 | +-- NO --> LOSO ROI or functional localizer
 |
 +-- Whole-brain analysis
 |
 +-- Is permutation testing feasible (< 50,000 voxels, < 1 day compute)?
 |
 +-- YES --> TFCE with permutation testing (recommended default)
 | OR cluster-based permutation (if spatial extent is of interest)
 |
 +-- NO --> Is the effect expected to be focal or distributed?
 |
 +-- FOCAL --> Voxelwise RFT-FWE (most conservative, best spatial specificity)
 |
 +-- DISTRIBUTED --> Cluster-based RFT with CDT p < 0.001
 OR FDR q < 0.05
```

## Reporting Statistical Results

Based on COBIDAS guidelines (Nichols et al., 2017):

### Required Information

- Inference method (voxelwise FWE, cluster-based, FDR, permutation, TFCE)
- For cluster-based: the cluster-defining threshold used
- For permutation: number of permutations
- For ROI analyses: how ROIs were defined, and whether correction was applied across ROIs
- Smoothing applied before group analysis (kernel FWHM in mm; typically **6-8 mm** for 2-mm voxels; Poldrack et al., 2011, Ch. 5)
- Coordinates of peak activations (in MNI or Talairach space)
- Cluster extent (number of voxels or volume in mm^3)
- Peak and cluster-level statistics and p-values

### Recommended Table Format

| Region | Cluster Size (voxels) | Peak Z | Peak MNI (x, y, z) | Cluster p (FWE) |
|---|---|---|---|---|
| L Inferior Frontal Gyrus | 342 | 5.12 | -48, 14, 22 | < 0.001 |
| R Fusiform Gyrus | 156 | 4.78 | 42, -52, -18 | 0.003 |

### Reporting Unthresholded Maps

In addition to thresholded results, consider uploading unthresholded statistical maps to NeuroVault (Gorgolewski et al., 2015) to facilitate meta-analysis and replication. This is increasingly expected by journals and reviewers.

## References

- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: A practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society B*, 57(1), 289-300.
- Eklund, A., Nichols, T. E., & Knutsson, H. (2016). Cluster failure: Why fMRI inferences for spatial extent have inflated false-positive rates. *PNAS*, 113(28), 7900-7905.
- Esterman, M., Tamber-Rosenau, B. J., Chiu, Y. C., & Yantis, S. (2010). Avoiding non-independence in fMRI data analysis: Leave one subject out. *NeuroImage*, 50(2), 572-576.
- Genovese, C. R., Lazar, N. A., & Nichols, T. (2002). Thresholding of statistical maps in functional neuroimaging using the false discovery rate. *NeuroImage*, 15(4), 870-878.
- Gorgolewski, K. J., Varoquaux, G., Rivera, G., et al. (2015). NeuroVault.org: A web-based repository for collecting and sharing unthresholded statistical maps of the human brain. *Frontiers in Neuroinformatics*, 9, 8.
- Kriegeskorte, N., Simmons, W. K., Bellgowan, P. S., & Baker, C. I. (2009). Circular analysis in systems neuroscience: The dangers of double dipping. *Nature Neuroscience*, 12(5), 535-540.
- Nichols, T. E., Das, S., Eickhoff, S. B., et al. (2017). Best practices in data analysis and sharing in neuroimaging using MRI (COBIDAS). *Nature Neuroscience*, 20(3), 299-303.
- Nichols, T. E., & Holmes, A. P. (2002). Nonparametric permutation tests for functional neuroimaging: A primer with examples. *Human Brain Mapping*, 15(1), 1-25.
- Poldrack, R. A., Mumford, J. A., & Nichols, T. E. (2011). *Handbook of Functional MRI Data Analysis*. Cambridge University Press.
- Saxe, R., Brett, M., & Kanwisher, N. (2006). Divide and conquer: A defense of functional localizers. *NeuroImage*, 30(4), 1088-1096.
- Smith, S. M., & Nichols, T. E. (2009). Threshold-free cluster enhancement: Addressing problems of smoothing, threshold dependence and localisation in cluster inference. *NeuroImage*, 44(1), 83-98.
- Woo, C. W., Krishnan, A., & Wager, T. D. (2014). Cluster-extent based thresholding in fMRI analyses: Pitfalls and recommendations. *NeuroImage*, 91, 412-419.
- Worsley, K. J., Andermann, M., Koulis, T., MacDonald, D., & Evans, A. C. (1999). Detecting changes in nonisotropic images. *Human Brain Mapping*, 8(2-3), 98-101.
- Worsley, K. J., Marrett, S., Neelin, P., Vandal, A. C., Friston, K. J., & Evans, A. C. (1996). A unified statistical approach for determining significant signals in images of cerebral activation. *Human Brain Mapping*, 4(1), 58-73.
