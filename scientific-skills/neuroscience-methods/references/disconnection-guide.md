# Disconnection Analysis and Network Lesion Mapping Guide

This reference document supplements `SKILL.md` with detailed procedures for disconnection analysis using BCBToolkit and network lesion mapping approaches.

## Disconnection Analysis with BCBToolkit

### Overview

BCBToolkit (Foulon et al., 2018) maps focal brain lesions to the white matter pathways they disrupt, using a normative tractography atlas derived from 170 healthy control diffusion MRI datasets.

### Step-by-Step Procedure

#### Step 1: Prepare Lesion Masks

- Lesion masks must be in MNI152 space (1mm or 2mm resolution)
- Binary format (0 = healthy, 1 = lesioned)
- One NIfTI file per patient

#### Step 2: Run Disconnection Mapping

For each patient lesion mask:
1. The toolbox identifies which tractography streamlines pass through the lesion
2. For each voxel outside the lesion, compute the probability of disconnection:
 ```
 P(disconnection at voxel v) = N(streamlines through lesion AND through v) / N(total streamlines through v)
 ```
3. Output: a whole-brain disconnection probability map per patient

#### Step 3: Threshold Disconnection Maps

- Apply a disconnection probability threshold (typically **> 0.5** or **> 0.7**)
- Lower thresholds are more sensitive but include more false positives
- Higher thresholds are more specific but may miss partially disconnected regions

#### Step 4: Statistical Analysis

Use disconnection probability maps in the same statistical framework as VLSM:
- **AnaCOM**: Anatomical connectivity-based mapping (included in BCBToolkit)
- **Voxelwise regression**: Disconnection probability as predictor of behavior
- **Tract-specific analysis**: Sum disconnection probability within specific tracts (e.g., arcuate fasciculus, corticospinal tract)

### Tract-Specific Analysis

Major tracts to consider in lesion studies:

| Tract | Function | Common Lesion Association | Source |
|---|---|---|---|
| Arcuate fasciculus | Language (phonological) | Conduction aphasia, repetition deficits | Catani & Mesulam, 2008 |
| Inferior fronto-occipital fasciculus | Semantic processing | Semantic deficits | Duffau et al., 2005 |
| Superior longitudinal fasciculus (II, III) | Spatial attention, praxis | Neglect, apraxia | Thiebaut de Schotten et al., 2011 |
| Uncinate fasciculus | Ventral semantic pathway | Naming deficits (controversial) | Papagno et al., 2011 |
| Corticospinal tract | Motor function | Hemiparesis | Zhu et al., 2010 |
| Inferior longitudinal fasciculus | Visual processing | Visual recognition deficits | Catani et al., 2003 |
| Cingulum | Memory, emotional processing | Memory deficits | Bubb et al., 2018 |
| Corpus callosum | Interhemispheric transfer | Disconnection syndromes | Gazzaniga, 2005 |

### Comparing VLSM and Disconnection Results

Run both VLSM and disconnection analysis on the same dataset to compare:

1. **Overlap**: Regions identified by both methods are strong candidates for critical involvement
2. **VLSM-only regions**: May reflect direct grey matter damage effects
3. **Disconnection-only regions**: May reflect remote effects via white matter disruption
4. **Statistical comparison**: Test whether disconnection probability explains additional behavioral variance beyond lesion location (using hierarchical regression)

## Network Lesion Mapping

### Lesion Network Mapping Procedure (Boes et al., 2015; Fox, 2018)

#### Step 1: Obtain Normative Connectome Data

- Use a large resting-state fMRI dataset (N >= 500 healthy controls)
- Common choices:
 - GSP 1000 connectome (Harvard/MGH)
 - Human Connectome Project (HCP)
 - UK Biobank
- Preprocess normative data with standard resting-state pipeline (motion correction, bandpass filtering 0.01--0.1 Hz, nuisance regression)

#### Step 2: Compute Lesion-Seeded Connectivity

For each patient:
1. Use the lesion mask as a seed region
2. Extract the mean BOLD time series from the seed location using the normative data
3. Compute whole-brain connectivity (Pearson correlation) from the seed
4. Fisher z-transform the correlation map

#### Step 3: Identify Common Network

Across all patients:
1. Threshold individual connectivity maps (e.g., at z > 0.2)
2. Compute the overlap: which regions are functionally connected to ALL (or most) lesion sites
3. Alternatively, correlate patient-specific connectivity patterns with behavioral scores

#### Step 4: Validate

- Compare the identified network to known functional anatomy
- Test whether network disruption score predicts behavioral deficit severity
- Cross-validate using leave-one-out or split-half approaches

### Network Lesion Mapping Considerations

| Consideration | Details | Source |
|---|---|---|
| Normative data quality | Larger, better-preprocessed datasets yield more reliable maps | Fox, 2018 |
| Lesion size effects | Large lesions produce more diffuse connectivity maps; consider size-matched controls | Fox, 2018 |
| Compensation/reorganization | Normative connectivity does not account for post-lesion plasticity | Fox, 2018 |
| Symptom specificity | Different symptoms from lesions in the same location may map to different networks | Boes et al., 2015 |
| Laterality | Ensure normative data includes adequate coverage of both hemispheres | Expert consensus |

### When to Use Each Approach

| Research Question | Recommended Method | Rationale |
|---|---|---|
| Which voxels are associated with deficit? | VLSM | Direct, established, widely accepted |
| Which tracts mediate the deficit? | Disconnection analysis | Captures white matter effects |
| Which brain network is disrupted? | Lesion network mapping | Captures distributed network effects |
| What explains the most variance? | Combine all three | Compare models; use hierarchical regression |

## Integration of Multiple Approaches

### Recommended Multi-Method Pipeline

1. **Start with VLSM**: Establish voxel-level associations (requires N >= 50)
2. **Add disconnection analysis**: Identify tract-level contributions (BCBToolkit)
3. **Add network mapping**: Identify network-level disruption (if normative connectome available)
4. **Compare**: Use hierarchical regression to test which level (voxel, tract, network) best explains behavioral variance
5. **Report all**: Provide maps at all three levels for comprehensive brain-behavior inference

### Statistical Framework for Model Comparison

```
Model 1: Behavior ~ Lesion volume (baseline)
Model 2: Behavior ~ Lesion volume + VLSM ROI damage
Model 3: Behavior ~ Lesion volume + Tract disconnection
Model 4: Behavior ~ Lesion volume + Network disruption
Model 5: Behavior ~ Lesion volume + All levels
```

Compare using AIC/BIC or likelihood ratio tests to determine which level provides the best explanation.

## References

- Boes, A. D., et al. (2015). Network localization of neurological symptoms from focal brain lesions. *Brain*, 138(10), 3061--3075.
- Bubb, E. J., Metzler-Baddeley, C., & Aggleton, J. P. (2018). The cingulum bundle: Anatomy, function, and dysfunction. *Neuroscience & Biobehavioral Reviews*, 92, 104--127.
- Catani, M., & Mesulam, M. (2008). The arcuate fasciculus and the disconnection theme in language and aphasia. *Cortex*, 44(8), 953--961.
- Catani, M., et al. (2003). Occipito-temporal connections in the human brain. *Brain*, 126(9), 2093--2107.
- Duffau, H., et al. (2005). New insights into the anatomo-functional connectivity of the semantic system. *NeuroReport*, 16(13), 1461--1465.
- Foulon, C., et al. (2018). Advanced lesion symptom mapping analyses and implementation as BCBtoolkit. *GigaScience*, 7(3), giy004.
- Fox, M. D. (2018). Mapping symptoms to brain networks with the human connectome. *New England Journal of Medicine*, 379(23), 2237--2245.
- Gazzaniga, M. S. (2005). Forty-five years of split-brain research and still going strong. *Nature Reviews Neuroscience*, 6(8), 653--659.
- Thiebaut de Schotten, M., et al. (2011). A lateralized brain network for visuospatial attention. *Nature Neuroscience*, 14(10), 1245--1246.
- Thiebaut de Schotten, M., et al. (2015). Brain disconnections link structural connectivity with function and behaviour. *Nature Communications*, 6, 7462.
