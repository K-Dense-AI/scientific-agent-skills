# Step-by-Step fMRI Preprocessing Pipeline

This reference document provides detailed parameter tables, software-specific guidance, and processing order diagrams for each preprocessing step. It supplements the core decision logic in `SKILL.md`.

---

## Step 1: DICOM to NIfTI Conversion and BIDS Organization

### Why BIDS?

The Brain Imaging Data Structure (BIDS; Gorgolewski et al., 2016) is essential for reproducible neuroimaging. fMRIPrep, MRIQC, and other automated tools require BIDS-formatted input.

### Expected BIDS Directory Structure

```
dataset/
 sub-01/
 anat/
 sub-01_T1w.nii.gz
 sub-01_T1w.json
 func/
 sub-01_task-rest_bold.nii.gz
 sub-01_task-rest_bold.json
 sub-01_task-rest_events.tsv
 fmap/
 sub-01_dir-AP_epi.nii.gz
 sub-01_dir-PA_epi.nii.gz
 sub-01_dir-AP_epi.json
 sub-01_dir-PA_epi.json
```

### Software-Specific Guidance

| Tool | Command Example | Notes |
|---|---|---|
| `dcm2niix` | `dcm2niix -b y -z y -o output_dir input_dir` | Recommended; preserves all metadata in JSON sidecar |
| `heudiconv` | `heudiconv -d {subject}/* -s 01 -c dcm2niix -o bids_dir -f heuristic.py` | Automates BIDS naming with heuristic files |
| `BIDScoin` | GUI-based mapping | User-friendly for complex protocols |

### What Happens If You Skip This Step

Without BIDS organization, automated tools like fMRIPrep cannot run. Manual pipelines will lack standardized metadata, making it difficult to detect acquisition parameters (TR, slice timing, phase-encoding direction) automatically.

---

## Step 2: Non-Steady-State Volume Removal

### Detailed Parameters

| Parameter | Value | Source |
|---|---|---|
| Volumes to discard | **3-5** (or until signal stabilizes) | Poldrack et al., 2011, Ch. 5 |
| Time equivalent | ~5-15 seconds depending on TR | Standard practice |
| Detection method | Signal intensity in first volumes >> subsequent volumes | fMRIPrep automatic detection |

### Software-Specific Guidance

| Tool | Implementation |
|---|---|
| **fMRIPrep** | Automatic detection and flagging via `non_steady_state_outlier_XX` columns in confounds TSV |
| **FSL** | Manual: remove volumes with `fslroi input output 5 -1` (skips first 5) |
| **SPM** | Set "Images to remove" in the batch editor before any preprocessing |
| **AFNI** | `3dTcat -prefix output input'[5..$]'` (removes first 5 volumes) |

### What Happens If You Skip This Step

Non-steady-state volumes have artificially high signal intensity. If retained, they bias the mean image (used as motion correction reference), inflate temporal variance, and can introduce artifacts in motion parameter estimates.

---

## Step 3: Slice Timing Correction — Detailed Parameters

### Parameters by Acquisition Type

| Acquisition | Slice Order | STC Reference Slice | Notes |
|---|---|---|---|
| Sequential ascending | 1, 2, 3, ... N | Middle slice (N/2) | Simple; less common in modern protocols |
| Sequential descending | N, N-1, ... 1 | Middle slice (N/2) | Less common |
| Interleaved (odd first) | 1, 3, 5, ... 2, 4, 6, ... | Middle slice | SPM/FSL default for interleaved |
| Interleaved (even first) | 2, 4, 6, ... 1, 3, 5, ... | Middle slice | Check scanner documentation |
| Multiband/SMS | Multiple slices simultaneously | Use slice timings, not slice order | Slice order cannot represent simultaneous slices |

### Software-Specific Guidance

| Tool | Implementation | Key Parameter |
|---|---|---|
| **fMRIPrep** | Automatic if BIDS metadata includes `SliceTiming` field | Reads from JSON sidecar |
| **FSL** (`slicetimer`) | `slicetimer -i input -o output -r TR --tcustom=timings.txt` | Custom timing file for multiband |
| **SPM** | Slice Timing module in batch editor | Specify slice order and reference slice |
| **AFNI** (`3dTshift`) | `3dTshift -tpattern alt+z -prefix output input` | Pattern: alt+z (interleaved), seq+z (sequential) |

### When to Definitely Skip STC

- **TR < 0.5 seconds**: Common STC interpolation methods provide negligible benefit (Sladky et al., 2011). Even newer methods (e.g., filter-shift) show minimal improvement at very short TRs
- **No accurate slice timing information available**: STC with wrong parameters is worse than no STC
- **Using only temporal derivatives in GLM**: The temporal derivative of the HRF can absorb timing shifts of approximately +/- 1 second (Henson et al., 2002), partially compensating for slice timing differences

### What Happens If You Skip This Step

Without STC, the temporal offset between first and last slices introduces a systematic timing error. For a TR of 2 seconds with interleaved acquisition, the last slice is offset by nearly 2 seconds from the first. This reduces statistical power for event-related designs and can bias estimates of hemodynamic response timing (Sladky et al., 2011).

---

## Step 4: Motion Correction — Detailed Parameters

### MCFLIRT (FSL) Parameters

| Parameter | Default | Recommended | Notes |
|---|---|---|---|
| Reference volume | Middle volume | Mean image after initial pass | Mean is more representative (Jenkinson et al., 2002) |
| Cost function | Normalized correlation | Normalized correlation | Robust for intra-modal EPI-to-EPI |
| Search stages | 8 mm, then 4 mm (x2) | Default | Three-stage coarse-to-fine optimization |
| Interpolation (estimation) | Trilinear | Trilinear | Fast; adequate for parameter estimation |
| Interpolation (final reslice) | Trilinear | **Sinc** (--sinc_final) | Reduces blurring in output images |
| DOF | 6 (rigid body) | 6 (rigid body) | Never use higher DOF for within-subject motion |

### Software Comparison

| Tool | Algorithm | Key Feature |
|---|---|---|
| **FSL MCFLIRT** | Cost-function optimized rigid body | Three-stage optimization; robust to local minima (Jenkinson et al., 2002) |
| **SPM Realign** | Least squares rigid body | Iterative resampling to mean image |
| **AFNI 3dvolreg** | Iterated linearized weighted least-squares | Fast; supports multiple cost functions |
| **ANTs** | Symmetric normalization (rigid) | Used by fMRIPrep for high-quality registration |
| **fMRIPrep** | MCFLIRT (default) or ANTs | Automatically selects based on data characteristics |

### Output: Motion Parameters

The 6 rigid-body parameters should be saved and used as confound regressors:

| Parameter | Unit | Typical Range (good data) | Concern Threshold |
|---|---|---|---|
| Translation X (left/right) | mm | < 1 mm total range | > 3 mm (Poldrack et al., 2011) |
| Translation Y (anterior/posterior) | mm | < 1 mm total range | > 3 mm |
| Translation Z (superior/inferior) | mm | < 1 mm total range | > 3 mm |
| Rotation pitch (around X) | radians | < 0.02 rad (~1 degree) | > 0.05 rad |
| Rotation roll (around Y) | radians | < 0.02 rad | > 0.05 rad |
| Rotation yaw (around Z) | radians | < 0.02 rad | > 0.05 rad |

### What Happens If You Skip This Step

Without motion correction, even small head movements (1-2 mm) produce signal changes that are larger than the BOLD effect (~1-3% signal change). Motion artifacts are the single largest source of false positives in fMRI (Power et al., 2012).

---

## Step 5: Distortion Correction — Detailed Parameters

### Method Comparison

| Method | Data Required | Accuracy | Software | When to Use |
|---|---|---|---|---|
| **TOPUP** (reverse PE) | Opposite-PE EPI pair (e.g., AP + PA blip-up/blip-down) | **High** | FSL TOPUP | Preferred when opposite-PE data available (Andersson et al., 2003) |
| **FUGUE** (fieldmap) | Dual-echo gradient-echo magnitude + phase images | **High** | FSL FUGUE | When GRE fieldmap was acquired (Jezzard & Balaban, 1995) |
| **SyN-SDC** (fieldmapless) | T1-weighted structural only | **Moderate** | ANTs / fMRIPrep | Fallback when no fieldmap data exists |
| **3dQwarp** | Opposite-PE pair | **High** | AFNI | AFNI pipeline equivalent of TOPUP |

### TOPUP Parameters (FSL)

```
# Example TOPUP configuration
topup --imain=AP_PA_blips --datain=acqparams.txt --config=b02b0.cnf --out=topup_results
applytopup --imain=AP_bold,PA_bold --topup=topup_results --datain=acqparams.txt --method=jac --out=corrected
```

The `acqparams.txt` file specifies phase-encoding direction and total readout time. These values **must** match the actual acquisition parameters.

### Regions Most Affected by Distortion

| Brain Region | Proximity to Air-Tissue Interface | Typical Displacement | Impact |
|---|---|---|---|
| Orbitofrontal cortex | Paranasal sinuses | **Several mm** | Signal loss and mislocalization in reward/decision studies |
| Anterior temporal lobe | Ear canals, mastoid | **Several mm** | Affects memory and language studies |
| Inferior temporal lobe | Sphenoid sinus | Moderate | Affects face perception and object recognition studies |
| Brainstem | Surrounding bone | Moderate | Affects autonomic and arousal studies |

### What Happens If You Skip This Step

Without distortion correction, functional images are geometrically distorted along the phase-encoding direction. This causes: (1) misregistration with the T1 structural image, (2) mislocalization of functional activations after normalization, and (3) signal pileup and signal void in affected regions. The impact is most severe for studies targeting orbitofrontal, temporal, and brainstem regions (Jezzard & Balaban, 1995).

---

## Step 6: Coregistration — Detailed Parameters

### Boundary-Based Registration (BBR)

BBR (Greve & Fischl, 2009) is the recommended method for EPI-to-T1 coregistration:

| Parameter | Value | Notes |
|---|---|---|
| Cost function | BBR (boundary-based) | Uses WM boundary; more robust than mutual information for EPI-T1 |
| Input | Distortion-corrected mean EPI | Apply distortion correction before coregistration |
| Reference | Skull-stripped T1 | Brain extraction must be accurate |
| DOF | 6 (rigid body) | EPI and T1 are from the same subject/session |
| Initialization | FLIRT 6-DOF (schedule=bbr.sch) | BBR refines initial FLIRT alignment |

### Software-Specific Guidance

| Tool | Method | Command |
|---|---|---|
| **fMRIPrep** | BBR (via FreeSurfer + FSL) | Automatic |
| **FSL** | `flirt -cost bbr -wmseg wm_seg -schedule bbr.sch` | Requires WM segmentation |
| **SPM** | `Coregister: Estimate` with mutual information | Less robust than BBR for EPI |
| **FreeSurfer** | `bbregister --bold --mov func.nii --s subject --init-fsl` | Excellent for surface-based analyses |

### What Happens If You Skip This Step

Without coregistration, functional and structural images are in different coordinate spaces. Normalization to MNI space via the structural image becomes impossible, and anatomical labeling of functional results is inaccurate.

---

## Step 7: Spatial Normalization — Detailed Parameters

### Normalization Methods

| Method | Software | Quality | Speed | Source |
|---|---|---|---|---|
| **ANTs SyN** | ANTs / fMRIPrep | **Excellent** | Slow (~1-2 hr/subject) | Avants et al., 2008 |
| **Unified Segmentation** | SPM | Good | Moderate | Ashburner & Friston, 2005 |
| **DARTEL** | SPM | **Excellent** | Slow (study-specific template) | Ashburner, 2007 |
| **FNIRT** | FSL | Good | Moderate | Andersson et al., 2007 |

### Template Spaces

| Template | Resolution | When to Use | Source |
|---|---|---|---|
| **MNI152NLin2009cAsym** | 1 mm | fMRIPrep default; current standard | Fonov et al., 2011 |
| **MNI152NLin6Asym** | 1 mm | FSL default (MNI152 6th generation) | FSL convention |
| **MNI152Lin** | 2 mm | Legacy; older SPM analyses | Older convention |
| **fsaverage** | Surface | Surface-based group analyses (FreeSurfer) | Fischl et al., 1999 |
| **fsLR** | Surface | HCP-style surface analyses | Van Essen et al., 2012 |

### Output Resolution

| Analysis | Recommended Output Voxel Size | Rationale |
|---|---|---|
| Standard group analysis | **2 mm isotropic** | Matches template resolution; balances detail and file size |
| High-resolution studies | **1-1.5 mm isotropic** | Preserves spatial detail for laminar or columnar analysis |
| ROI-based analysis | **2 mm isotropic** | Standard; ROIs average over voxels anyway |
| Connectivity with small ROIs | **2 mm isotropic** | Smaller voxels preserve signal in small subcortical structures |

### What Happens If You Skip This Step

Without normalization, each subject's brain is in its own native space. Group-level analyses (second-level GLM, group connectivity maps) are impossible because there is no common coordinate system. Subject-level analyses in native space are valid but results cannot be reported in standard coordinates.

---

## Step 8: Spatial Smoothing — Detailed Parameters

### Kernel Size Recommendations

| Voxel Size | Analysis Type | FWHM | Result | Source |
|---|---|---|---|---|
| 2 mm | Univariate group | **6 mm** | 3x voxel size; good SNR gain | Mikl et al., 2008 |
| 3 mm | Univariate group | **6-8 mm** | 2-3x voxel size; standard | Poldrack et al., 2011 |
| 2 mm | Resting-state connectivity | **4-6 mm** | Moderate smoothing | Ciric et al., 2017 |
| 2 mm | MVPA | **0 mm (none)** | Preserve spatial patterns | Misaki et al., 2013 |
| 1.5 mm | High-resolution | **3-4 mm** | 2x voxel size; preserve resolution | Matched filter theorem |
| Any | Searchlight | **0 mm (none)** | Searchlight provides spatial averaging | Etzel et al., 2013 |

### Software-Specific Guidance

| Tool | Command | Notes |
|---|---|---|
| **FSL** | `fslmaths input -s 2.548 output` | FSL uses sigma, not FWHM: sigma = FWHM / 2.355 |
| **SPM** | Smooth module: set FWHM [6 6 6] | Specify FWHM in mm for each axis |
| **AFNI** | `3dmerge -1blur_fwhm 6 -prefix output input` | Specify FWHM directly |
| **Nilearn** | `smooth_img(img, fwhm=6)` | Python; can also specify per-axis |
| **fMRIPrep** | Does NOT smooth | Smoothing is intentionally left to the user |

### Smoothing and Random Field Theory (RFT)

For cluster-based inference using RFT (Worsley et al., 1996), the data must be sufficiently smooth. The smoothness estimation assumes a minimum smoothness of approximately 2-3 voxel FWHM. Applying a kernel of at least 2x voxel size ensures this assumption is met. If data are already smooth (e.g., after normalization and resampling), additional smoothing may not be needed for RFT validity, but this should be verified.

### What Happens If You Skip This Step

Without smoothing for univariate analyses: (1) SNR is lower, reducing power; (2) inter-subject anatomical variability is not compensated, reducing group-level sensitivity; (3) RFT assumptions may be violated, leading to invalid cluster-based inference. However, skipping smoothing is correct and necessary for MVPA.

---

## Complete Pipeline Processing Order Diagram

### Standard Task fMRI Pipeline

```
Raw DICOM data
 |
 v
[1] DICOM to NIfTI (dcm2niix) + BIDS organization
 |
 v
[2] Remove non-steady-state volumes (first 3-5 TRs)
 |
 v
[3] Slice timing correction (if TR > 1 s)
 | - Reference: middle slice
 | - Interpolation: sinc or Fourier
 |
 v
[4] Motion correction (6-DOF rigid body)
 | - Reference: mean image
 | - Save 6 motion parameters
 | - Calculate FD and DVARS
 |
 v
[5] Distortion correction (TOPUP or FUGUE)
 | - Requires fieldmap or opposite-PE data
 |
 v
[6] Coregistration (EPI to T1)
 | - Method: BBR (Greve & Fischl, 2009)
 |
 v
[7] Spatial normalization (to MNI space)
 | - Method: ANTs SyN or SPM unified segmentation
 | - Output: 2 mm isotropic
 |
 v
[8] Smoothing (FWHM = 2-3x voxel size)
 | - SKIP for MVPA
 |
 v
Preprocessed BOLD data (ready for GLM)
 + Confound time series (motion, FD, DVARS, CompCor)
```

### Resting-State Connectivity Pipeline Additions

After the standard pipeline, resting-state analyses typically add:

```
Preprocessed BOLD data
 |
 v
[9] Confound regression
 | - 24-parameter motion model (Friston et al., 1996)
 | - aCompCor: 5-6 WM/CSF components (Behzadi et al., 2007)
 | - Optional: global signal regression (Murphy & Fox, 2017)
 | - Spike regressors for FD > 0.2 mm (Power et al., 2014)
 |
 v
[10] Temporal filtering
 | - Band-pass: 0.01-0.1 Hz (for connectivity)
 | - OR high-pass only: 0.01 Hz (if GSR applied)
 |
 v
[11] Scrubbing / censoring
 | - Remove volumes with FD > 0.2 mm + 1 volume before + 2 after
 | - Require minimum 5 minutes of clean data (Power et al., 2014)
 |
 v
Cleaned BOLD data (ready for connectivity analysis)
```

---

## Key References for This Document

- Andersson, J. L. R., Skare, S., & Ashburner, J. (2003). How to correct susceptibility distortions in spin-echo echo-planar images. *NeuroImage*, 20(2), 870-888.
- Ashburner, J. (2007). A fast diffeomorphic image registration algorithm. *NeuroImage*, 38(1), 95-113.
- Ashburner, J., & Friston, K. J. (2005). Unified segmentation. *NeuroImage*, 26(3), 839-851.
- Avants, B. B., Epstein, C. L., Grossman, M., & Gee, J. C. (2008). Symmetric diffeomorphic image registration with cross-correlation. *Medical Image Analysis*, 12(1), 26-41.
- Behzadi, Y., Restom, K., Liau, J., & Liu, T. T. (2007). A component based noise correction method (CompCor). *NeuroImage*, 37(1), 90-101.
- Ciric, R., Wolf, D. H., Power, J. D., et al. (2017). Benchmarking confound regression strategies. *NeuroImage*, 154, 174-187.
- Etzel, J. A., Zacks, J. M., & Braver, T. S. (2013). Searchlight analysis: promise, pitfalls, and potential. *NeuroImage*, 78, 261-269.
- Fonov, V. S., Evans, A. C., Botteron, K., et al. (2011). Unbiased average age-appropriate atlases for pediatric studies. *NeuroImage*, 54(1), 313-327.
- Friston, K. J., Williams, S., Howard, R., et al. (1996). Movement-related effects in fMRI time-series. *Magnetic Resonance in Medicine*, 35(3), 346-355.
- Gorgolewski, K. J., et al. (2016). The brain imaging data structure. *Scientific Data*, 3, 160044.
- Greve, D. N., & Fischl, B. (2009). Accurate and robust brain image alignment using boundary-based registration. *NeuroImage*, 48(1), 63-72.
- Henson, R. N. A., et al. (2002). Detecting latency differences in event-related BOLD responses. *NeuroImage*, 15(1), 83-97.
- Jenkinson, M., Bannister, P., Brady, J. M., & Smith, S. M. (2002). Improved optimization for the robust and accurate linear registration and motion correction of brain images. *NeuroImage*, 17(2), 825-841.
- Jezzard, P., & Balaban, R. S. (1995). Correction for geometric distortion in echo planar images from B0 field variations. *Magnetic Resonance in Medicine*, 34(1), 65-73.
- Mikl, M., et al. (2008). Effects of spatial smoothing on fMRI group inferences. *Magnetic Resonance Imaging*, 26(4), 490-503.
- Misaki, M., Luh, W. M., & Bandettini, P. A. (2013). The effect of spatial smoothing on fMRI decoding. *NeuroImage*, 78, 13-22.
- Murphy, K., & Fox, M. D. (2017). Towards a consensus regarding global signal regression. *NeuroImage*, 154, 169-173.
- Parker, D. B., & Razlighi, Q. R. (2019). The benefit of slice timing correction in common fMRI preprocessing pipelines. *Frontiers in Neuroscience*, 13, 821.
- Poldrack, R. A., Mumford, J. A., & Nichols, T. E. (2011). *Handbook of Functional MRI Data Analysis*. Cambridge University Press.
- Power, J. D., et al. (2012). Spurious but systematic correlations in functional connectivity MRI networks arise from subject motion. *NeuroImage*, 59(3), 2142-2154.
- Power, J. D., et al. (2014). Methods to detect, characterize, and remove motion artifact in resting state fMRI. *NeuroImage*, 84, 320-341.
- Sladky, R., et al. (2011). Slice-timing effects and their correction in functional MRI. *NeuroImage*, 58(2), 588-594.
- Worsley, K. J., et al. (1996). A unified statistical approach for determining significant signals in images of cerebral activation. *Human Brain Mapping*, 4(1), 58-73.
