# RSA Analysis Guide: Step-by-Step Workflow

This reference document supplements `SKILL.md` with a complete step-by-step workflow for representational similarity analysis (RSA), including RDM construction, model specification, noise ceiling computation, and visualization.

## Step-by-Step RSA Workflow

### Step 1: Estimate Condition-Specific Activity Patterns

**For fMRI:**
1. Run a general linear model (GLM) with one regressor per condition (beta-series or least-squares-separate approach)
2. Each condition yields a beta-weight map across voxels in an ROI
3. Use **least-squares-separate (LSS)** for single-trial estimates when computing trial-wise RDMs (Mumford et al., 2012)
4. Use **least-squares-all (LSA)** when you have a small number of conditions with many trials each

> **Domain judgment**: For single-trial estimation, LSS produces less biased estimates than LSA when trials are closely spaced in time, because including all regressors simultaneously leads to collinearity in the design matrix (Mumford et al., 2012).

**For EEG/MEG:**
1. Epoch data around stimulus onset; average trials within each condition
2. Use the spatial pattern at a specific time point, or average over a time window
3. For time-resolved RSA: compute RDM at each time point separately

### Step 2: Extract Patterns for the ROI or Brain Region

- **ROI approach**: Extract voxel/channel values for each condition from a predefined region
- **Searchlight RSA**: Compute RDMs in a local sphere around each voxel (same radius considerations as decoding searchlight: **3-4 voxels** for fMRI; Kriegeskorte et al., 2006)
- **Whole-brain RSA**: Use parcellation (e.g., Glasser atlas with 360 parcels) and compute one RDM per parcel

### Step 3: Construct the Neural RDM

#### Choosing a Distance Metric

| Metric | Formula | Bias | Scale | Best For |
|---|---|---|---|---|
| **Correlation distance** | 1 - Pearson(pattern_a, pattern_b) | Positively biased by noise | 0 to 2 | Exploratory RSA; comparing pattern shape |
| **Euclidean distance** | sqrt(sum((a - b)^2)) | Positively biased by noise | 0 to inf | When amplitude matters |
| **Crossnobis (cross-validated Mahalanobis)** | Multiply pattern differences across independent data partitions, with multivariate noise normalization | **Unbiased** (expected value = 0 under null) | -inf to inf | **Inferential statistics; model comparison** |

(Walther et al., 2016; Kriegeskorte & Diedrichsen, 2019)

#### Computing the Crossnobis Distance

The crossnobis estimator requires data from multiple independent partitions (e.g., fMRI runs):

1. Estimate condition-specific patterns separately for each run
2. Compute the residual covariance matrix from the GLM residuals (for noise normalization)
3. For each pair of conditions (i, j):
 - Compute the pattern difference (beta_i - beta_j) in each run
 - Multiply the pattern differences from different runs (cross-validated: never multiply a run's data with itself)
 - Apply multivariate noise normalization (whiten using the residual covariance)
4. Average across all cross-validated run pairs

> **Domain judgment**: The cross-validation step ensures the estimator is unbiased. Without it, noise in the patterns inflates all pairwise distances by a positive amount proportional to the noise variance divided by the number of voxels. This bias makes it impossible to test whether two conditions are truly distinguishable (Walther et al., 2016).

#### Noise Normalization (Multivariate Whitening)

- Estimate the noise covariance matrix Sigma from GLM residuals
- Apply Sigma^(-1/2) to the pattern differences before computing distances
- This weights informative voxels (low noise correlation) more heavily than noisy or correlated voxels
- Improves reliability of RDMs substantially, especially for large ROIs (Walther et al., 2016)

### Step 4: Construct Model RDMs

Model RDMs encode your theoretical predictions about representational structure.

#### Common Model RDM Types

| Model Type | Construction | Example |
|---|---|---|
| **Categorical** | Binary: 0 for same category, 1 for different category | "Face vs. object" model: 0 within faces, 0 within objects, 1 between |
| **Feature-based** | Continuous distances from computational features | DNN layer activations; Gabor filter responses; semantic embedding distances |
| **Behavioral** | Distances derived from human similarity judgments | Multi-arrangement task (Kriegeskorte & Mur, 2012); pairwise similarity ratings |
| **Hierarchical** | Graded distances reflecting taxonomic depth | 0 within species, 0.5 within class, 1 across kingdoms |
| **Computational model** | Distances from the internal representations of a model | CNN layer RDMs; RNN hidden state RDMs; reinforcement learning value RDMs |

#### Constructing Model RDMs from Theoretical Predictions

1. **Define your stimulus set**: List all conditions (N conditions)
2. **For each pair of conditions**: Assign a predicted dissimilarity value
3. **Organize into an N x N symmetric matrix** with zeros on the diagonal
4. **Vectorize the lower triangle**: Extract the N*(N-1)/2 unique pairwise distances

> **Domain judgment**: Model RDMs should be constructed BEFORE looking at neural data. Constructing models post-hoc to match observed neural RDMs is circular (Kriegeskorte et al., 2009). Pre-register your model RDMs when possible.

### Step 5: Compare Neural RDMs to Model RDMs

#### Comparison Methods

| Method | Use When | Formula | Source |
|---|---|---|---|
| **Spearman rank correlation** | Default; robust to outliers and nonlinear monotonic relationships | rho(vectorized_brain_RDM, vectorized_model_RDM) | Nili et al., 2014 |
| **Pearson correlation** | When the linear relationship between model and brain distances is theoretically motivated | r(vectorized_brain_RDM, vectorized_model_RDM) | Kriegeskorte et al., 2008 |
| **Kendall tau-a** | For RDMs with many tied values (e.g., binary categorical models) | tau_a(vectorized_brain_RDM, vectorized_model_RDM) | Nili et al., 2014 |
| **Partial correlation** | When controlling for a confound model (e.g., low-level visual similarity) | partial_rho(brain, model_A \| model_B) | Kriegeskorte & Diedrichsen, 2019 |
| **Weighted regression** | Fitting multiple models simultaneously; estimating relative contributions | beta = (X'X)^{-1} X'y on vectorized RDMs | Kriegeskorte & Diedrichsen, 2019 |

#### Choosing Between Spearman and Pearson

- **Spearman** (default): Does not assume linearity between model and brain distances; only assumes a monotonic relationship. More robust to the arbitrary scaling of model predictions (Nili et al., 2014)
- **Pearson**: Appropriate when the model makes quantitative predictions about the magnitude of distances, not just their rank order

### Step 6: Statistical Inference

#### Permutation Test for Individual Model Significance

1. Permute condition labels **of the neural data** (not the model) to generate null RDMs
2. Recompute the correlation between each permuted neural RDM and the model RDM
3. Repeat **10,000 times** (Nili et al., 2014)
4. p-value = proportion of null correlations >= observed correlation

> **Domain judgment**: You must permute the condition labels (rows and columns of the RDM simultaneously), NOT individual entries of the RDM. Permuting entries destroys the distance-matrix structure and produces an invalid null distribution (Nili et al., 2014).

#### Noise Ceiling Computation

The noise ceiling bounds the best possible model fit given between-subject variability.

**Upper bound:**
1. For each subject, compute the correlation between that subject's RDM and the group-average RDM (including that subject)
2. Average across subjects

**Lower bound (preferred -- cross-validated):**
1. For each subject, compute the correlation between that subject's RDM and the group-average RDM **excluding** that subject
2. Average across subjects

(Nili et al., 2014)

**Interpretation:**
- A model whose fit falls within the noise ceiling explains as much representational variance as is possible given the noise in the data
- A model below the lower bound leaves systematic, explainable variance unaccounted for
- The gap between upper and lower bound reflects the degree of between-subject variability

#### Comparing Two Models

1. For each subject, compute the correlation of the brain RDM with Model A and with Model B
2. Compute the difference (corr_A - corr_B) for each subject
3. Test the group-level difference with a paired t-test or Wilcoxon signed-rank test
4. Alternatively, use a bootstrap test: resample subjects and test whether the difference in model fit is consistently positive or negative (Nili et al., 2014)

### Step 7: Visualize Results

#### RDM Visualization

- Display as a **color-coded matrix** (conditions x conditions) with an appropriate colormap (diverging for crossnobis, sequential for correlation distance)
- Order conditions meaningfully: group by category, sort by a relevant feature dimension
- Always include a **colorbar** with the distance metric labeled
- For crossnobis RDMs: use a diverging colormap centered at zero (e.g., blue-white-red) to highlight that negative values are meaningful

#### Multidimensional Scaling (MDS)

- Apply classical (metric) MDS to the RDM to project conditions into a 2D or 3D space
- Useful for visualizing cluster structure and gradients in the representation
- Report the stress value or proportion of variance explained by the MDS solution
- **Caution**: MDS is a visualization aid, not a statistical test. Do not draw inferential conclusions from MDS plots alone (Kriegeskorte et al., 2008)

#### Model Comparison Bar Plots

- Plot the correlation between each model RDM and the brain RDM (one bar per model)
- Include error bars (SEM across subjects or bootstrap confidence intervals)
- Overlay the noise ceiling as a shaded band
- Mark significant models and significant model differences

## Category-Level vs. Exemplar-Level RSA

### Category-Level Analysis

- Conditions represent categories (e.g., faces, houses, tools, animals)
- Typically **4-20 categories** with multiple exemplars per category
- RDM captures between-category representational distances
- Appropriate for: testing categorical organization (e.g., animate vs. inanimate distinction)
- **Limitation**: Cannot distinguish whether a region encodes the category boundary or continuous features that correlate with category membership

### Exemplar-Level Analysis

- Each condition is a unique stimulus (e.g., 96 individual object images)
- RDM captures fine-grained representational geometry
- Appropriate for: comparing neural representations to computational model layer representations (e.g., DNN layers)
- **Requirement**: Many more conditions (typically **48-96+**); each shown multiple times
- **Challenge**: Single-trial beta estimates are noisier; crossnobis estimator is essential to avoid bias (Walther et al., 2016)

> **Domain judgment**: Category-level RSA with few categories (e.g., 4) has very few unique distances in the RDM (only 6 for 4 categories), making model comparisons statistically weak. Exemplar-level designs with many conditions provide much more statistical power for RSA because the number of unique distances grows as N*(N-1)/2 (Kriegeskorte et al., 2008).

## Multi-Arrangement for Behavioral RDMs

### The Method

The multi-arrangement task (Kriegeskorte & Mur, 2012) efficiently measures perceived similarity among stimuli:

1. Participants view all stimuli on a computer screen and arrange them by perceived similarity (drag-and-drop)
2. Similar items are placed close together; dissimilar items far apart
3. The procedure adaptively selects subsets of stimuli for additional arrangements to improve estimation
4. Pairwise distances between stimulus positions are extracted and combined across arrangements

### Practical Parameters

- **Number of stimuli**: Works well with **12-96** stimuli (fewer than 12: too few distances; more than 96: too many items to arrange simultaneously)
- **Number of arrangements**: Typically **10-30** per participant; the algorithm adaptively selects informative subsets
- **Subset size per arrangement**: **6-12 stimuli** per arrangement screen (participant fatigue increases with larger subsets)
- **Duration**: Approximately **20-60 minutes** depending on stimulus set size

### When to Use Behavioral RDMs

- To test whether neural representations predict perceived similarity
- To bridge neural and behavioral levels of description (Kriegeskorte et al., 2008)
- As a model RDM alongside computational models to test which better explains neural data

## Using the RSA Toolbox (Python: rsatoolbox)

### Basic Workflow

```python
import rsatoolbox
import numpy as np

# 1. Create dataset objects (one per subject/session)
# data: n_conditions x n_channels/voxels
# descriptors: condition labels
dataset = rsatoolbox.data.Dataset(
 measurements=beta_patterns, # conditions x voxels
 obs_descriptors={'stimulus': condition_labels}
)

# 2. Compute RDM
rdm = rsatoolbox.rdm.calc_rdm(
 dataset,
 method='crossnobis', # preferred for inference
 descriptor='stimulus',
 noise=noise_covariance # from GLM residuals
)

# 3. Define model RDMs
model_rdm = rsatoolbox.rdm.RDMs(
 dissimilarities=model_distances, # vectorized lower triangle
 rdm_descriptors={'name': 'my_model'}
)

# 4. Compare
result = rsatoolbox.rdm.compare(
 rdm, model_rdm,
 method='spearman' # or 'corr', 'kendall'
)

# 5. Noise ceiling
ceiling = rsatoolbox.inference.eval_fixed(
 model_rdm, subject_rdms,
 method='spearman'
)
```

### Key Function Parameters

| Function | Key Parameter | Recommended Value | Rationale |
|---|---|---|---|
| `calc_rdm` | `method` | `'crossnobis'` | Unbiased estimator (Walther et al., 2016) |
| `calc_rdm` | `noise` | GLM residual covariance | Multivariate noise normalization improves reliability |
| `compare` | `method` | `'spearman'` | Robust to nonlinear monotonic transforms (Nili et al., 2014) |
| `eval_fixed` | `method` | `'spearman'` | Consistent with comparison method |

## References

- Kriegeskorte, N., Goebel, R., & Bandettini, P. (2006). Information-based functional brain mapping. *PNAS*, 103(10), 3863-3868.
- Kriegeskorte, N., Mur, M., & Bandettini, P. (2008). Representational similarity analysis. *Front. Syst. Neurosci.*, 2, 4.
- Kriegeskorte, N., et al. (2009). Circular analysis in systems neuroscience. *Nat. Neurosci.*, 12(5), 535-540.
- Kriegeskorte, N., & Mur, M. (2012). Inverse MDS: Inferring dissimilarity structure from multiple item arrangements. *Front. Psychol.*, 3, 245.
- Kriegeskorte, N., & Diedrichsen, J. (2019). Peeling the onion of brain representations. *Annu. Rev. Neurosci.*, 42, 407-432.
- Mumford, J. A., Turner, B. O., Ashby, F. G., & Poldrack, R. A. (2012). Deconvolving BOLD activation in event-related designs for multivoxel pattern classification analyses. *NeuroImage*, 59(3), 2636-2643.
- Nili, H., et al. (2014). A toolbox for representational similarity analysis. *PLoS Comput. Biol.*, 10(4), e1003553.
- Walther, A., et al. (2016). Reliability of dissimilarity measures for multi-voxel pattern analysis. *NeuroImage*, 137, 188-200.
