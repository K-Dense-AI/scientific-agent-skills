# VLSM Pipeline: Step-by-Step Workflow

This reference document supplements `SKILL.md` with a detailed step-by-step workflow for voxel-based lesion-symptom mapping.

## Pre-Analysis Checklist

Before starting VLSM, verify:

- [ ] N >= 50 patients (N >= 100 preferred; Sperber, 2020)
- [ ] All patients have T1 (and ideally FLAIR) images
- [ ] Behavioral data available for all patients (continuous preferred)
- [ ] Time post-onset is > 3 months for all (or most) patients
- [ ] Etiology is consistent (e.g., all ischemic stroke) or will be modeled

## Step 1: Lesion Segmentation

### Manual Tracing Protocol

1. **Imaging modality**: Use T1 for chronic lesions (hypointense); FLAIR for acute/subacute lesions (hyperintense) or white matter lesions
2. **Software**: MRIcron, ITK-SNAP, or 3D Slicer
3. **Tracing procedure**:
 - Trace on each axial slice (or coronal if preferred)
 - Include all clearly damaged tissue
 - Exclude peri-lesional edema if visible
 - Include both cortical and subcortical damage
4. **Inter-rater reliability**: If multiple raters, compute Dice coefficient; target >= 0.85 (Pustina et al., 2016)
5. **Save as binary mask** (0 = healthy, 1 = lesioned) in the same space as the T1

### Semi-Automated Segmentation

If using LINDA or lesion_gnb:
1. Run the automated pipeline
2. **CRITICAL**: Visually inspect EVERY patient's segmentation on all slices
3. Manually correct errors (over-segmentation of ventricles, missed lesion regions)
4. Document the correction process

## Step 2: Spatial Normalization

### Using ANTs (recommended)

```bash
# Create lesion cost function mask (inverted lesion)
fslmaths lesion_mask.nii.gz -binv lesion_costmask.nii.gz

# Register T1 to MNI with cost function masking
antsRegistrationSyNQuick.sh \
 -d 3 \
 -f MNI152_T1_1mm.nii.gz \
 -m patient_T1.nii.gz \
 -x lesion_costmask.nii.gz \
 -o patient_to_MNI_

# Apply warp to lesion mask
antsApplyTransforms \
 -d 3 \
 -i lesion_mask.nii.gz \
 -r MNI152_T1_1mm.nii.gz \
 -o lesion_mask_MNI.nii.gz \
 -t patient_to_MNI_1Warp.nii.gz \
 -t patient_to_MNI_0GenericAffine.mat \
 -n NearestNeighbor
```

### Using FSL

```bash
# Register with lesion masking
flirt -in patient_T1 -ref MNI152_T1_2mm -omat affine.mat \
 -inweight lesion_costmask -cost mutualinfo

fnirt --in=patient_T1 --ref=MNI152_T1_2mm --aff=affine.mat \
 --inmask=lesion_costmask --cout=warp_coeff

applywarp --in=lesion_mask --ref=MNI152_T1_2mm \
 --warp=warp_coeff --out=lesion_mask_MNI --interp=nn
```

### Quality Control

For every patient:
1. Overlay the warped T1 on the MNI template
2. Check anatomical landmark alignment (ventricles, central sulcus, Sylvian fissure)
3. Overlay the warped lesion mask on the template
4. Verify the lesion location is anatomically plausible
5. Flag and exclude patients with poor registration quality

## Step 3: Create Lesion Overlap Map

1. Sum all binarized lesion masks in MNI space
2. Inspect the overlap map to understand lesion distribution
3. Set minimum overlap threshold:
 - Include voxels where >= **N_min patients** have lesions
 - N_min = max(10, 10% of sample) (Kimberg et al., 2007)
 - This creates the analysis mask

## Step 4: Run VLSM Analysis

### Using NiiStat (MATLAB)

```matlab
% Load lesion masks and behavioral data
nii_stat(lesion_folder, behavior_file, ...
 'design', 'continuous', ... % or 'binomial'
 'stat', 'brunner-munzel', ... % or 'ttest'
 'perm', 5000, ... % permutation count
 'minOverlap', 10); % minimum lesion overlap
```

### Using LESYMAP (R)

```r
library(LESYMAP)
lsm = lesymap(
 lesions.list = lesion_files,
 behavior = behavior_scores,
 method = "BM", # Brunner-Munzel
 multipleComparison = "FWE",
 nperm = 5000,
 minSubjectPerVoxel = 10
)
```

### Controlling for Lesion Volume

**Method 1: Direct covariate (recommended)**
```r
lsm = lesymap(
 lesions.list = lesion_files,
 behavior = behavior_scores,
 method = "regress", # Regression-based
 covariates = data.frame(lesion_vol = volumes),
 multipleComparison = "FWE",
 nperm = 5000
)
```

**Method 2: Residualization**
```r
residuals = resid(lm(behavior ~ lesion_volume))
# Use residuals as behavior in standard VLSM
```

## Step 5: Interpret Results

### What the Map Shows

- Each supra-threshold voxel indicates a statistical association between damage at that voxel and worse behavioral performance
- The map does NOT directly prove causation; it shows association (confounded by vascular territory collinearity)
- Report peak coordinates, cluster extent, and statistical values

### What the Map Does NOT Show

- It does not identify "the region responsible for X" (collinearity caveat)
- It does not account for white matter disconnection effects
- It does not reveal whether the deficit is due to damage at the voxel or at a distant connected region

### Supplementary Analyses

After VLSM, consider:
1. **Disconnection analysis**: Run BCBToolkit to identify which tracts are disrupted
2. **ROI validation**: Extract lesion load in a priori ROIs and test association with behavior
3. **Lesion network mapping**: Identify the functional network disrupted by the lesion locations

## Common Quality Control Issues

| Issue | Detection | Solution |
|---|---|---|
| Poor registration | Visual inspection of overlay | Re-run with different parameters or enantiomorphic approach |
| Lesion extends beyond brain boundary | Visual inspection | Mask lesion with brain mask |
| Ventricle labeled as lesion | Compare to template ventricles | Manually correct segmentation |
| Behavioral outliers | Box plots, Cook's distance | Investigate; consider robust statistics (Brunner-Munzel) |
| Insufficient lesion overlap | Overlap map shows sparse coverage | Lower voxel threshold or use ROI approach |

## References

- Avants, B. B., et al. (2011). A reproducible evaluation of ANTs similarity metric performance in brain image registration. *NeuroImage*, 54(3), 2033--2044.
- Bates, E., et al. (2003). Voxel-based lesion-symptom mapping. *Nature Neuroscience*, 6(5), 448--450.
- Brett, M., et al. (2001). Spatial normalization of brain images with focal lesions using cost function masking. *NeuroImage*, 14(2), 486--500.
- Kimberg, D. Y., et al. (2007). Power in voxel-based lesion-symptom mapping. *Journal of Cognitive Neuroscience*, 19(7), 1067--1080.
- Pustina, D., et al. (2016). Automated segmentation of chronic stroke lesions using LINDA. *Human Brain Mapping*, 37(4), 1405--1421.
- Pustina, D., et al. (2018). Improved accuracy of lesion to symptom mapping with multivariate sparse canonical correlations. *Neuropsychologia*, 115, 154--166.
- Sperber, C. (2020). Rethinking causality and data complexity in brain lesion-behaviour inference. *Cortex*, 126, 49--62.
