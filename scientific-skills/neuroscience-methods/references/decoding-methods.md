# Decoding Methods: Detailed Classifier Comparisons, Searchlight Parameters, and Tools

This reference document supplements `SKILL.md` with extended details on classifier selection, searchlight analysis, feature selection, hyperparameter tuning, and software tools for neural decoding.

## Classifier Comparison

### Linear SVM

- **Mechanism**: Finds the maximum-margin hyperplane separating classes in feature space
- **Regularization**: Controlled by parameter C (inverse regularization strength). Default C=1 is appropriate for most neuroimaging applications (Misaki et al., 2010; Varoquaux et al., 2017)
- **Strengths**: Robust to high-dimensional data (n_features >> n_samples); well-suited for fMRI where voxel count vastly exceeds trial count; regularization handles collinear features
- **Weaknesses**: No native probability estimates (use Platt scaling if needed, but this adds a calibration step); sensitive to C parameter when data is noisy
- **Typical neuroimaging performance**: Among the best linear classifiers for fMRI pattern classification (Misaki et al., 2010)

### Linear Discriminant Analysis (LDA)

- **Mechanism**: Projects data onto the direction that maximizes between-class variance relative to within-class variance, assuming Gaussian class distributions with shared covariance
- **Regularization**: Shrinkage of covariance matrix toward identity (Ledoit-Wolf shrinkage recommended); critical when n_features > n_samples
- **Strengths**: Fast to train and test; provides a natural decision boundary; works well after dimensionality reduction
- **Weaknesses**: Unreliable without dimensionality reduction or regularization when voxel count exceeds sample count; assumes equal covariance across classes (Misaki et al., 2010)
- **When to use**: After PCA or feature selection has reduced dimensionality; for EEG/MEG where channel count is moderate (~64-306 channels)

### Logistic Regression

- **Mechanism**: Models the log-odds of class membership as a linear function of features
- **Regularization**: L2 (ridge) penalty is default; L1 (lasso) produces sparse solutions identifying a subset of informative features
- **Strengths**: Provides calibrated probability estimates; L1 variant enables feature selection; comparable performance to linear SVM (Varoquaux et al., 2017)
- **Weaknesses**: L1 solutions are unstable when features are highly correlated (as in fMRI); selected voxels may not be neurophysiologically meaningful
- **When to use**: When probability outputs are needed (e.g., for confidence-weighted analyses); when L1 sparsity is desired for interpretability (with caveats)

### Gaussian Naive Bayes (GNB)

- **Mechanism**: Assumes features are independently Gaussian-distributed within each class
- **Strengths**: Extremely fast; no hyperparameters to tune
- **Weaknesses**: The independence assumption is strongly violated in neuroimaging data (neighboring voxels are correlated); generally performs significantly worse than SVM, LDA, and logistic regression for fMRI (Misaki et al., 2010)
- **When to use**: As a quick sanity check or baseline; avoid for primary analyses

### Nonlinear Classifiers (RBF SVM, Random Forest, Neural Networks)

- **General guidance**: Nonlinear classifiers rarely outperform linear classifiers for typical neuroimaging classification because the feature space is high-dimensional relative to the number of training samples (Misaki et al., 2010)
- **Exception**: May be useful with very large datasets (e.g., thousands of trials pooled across subjects) or when representations are known to be nonlinearly organized
- **Risk**: Overfitting is severe with small neuroimaging samples; results are harder to interpret neurally

### Summary Comparison Table

| Classifier | Speed (train) | Probability output | Feature selection | Typical accuracy rank | Recommended for |
|---|---|---|---|---|---|
| Linear SVM | Medium | No (without Platt) | Via weight magnitude | 1st-2nd | fMRI ROI, searchlight |
| LDA (shrinkage) | Fast | Yes | No | 1st-2nd | EEG/MEG time-resolved |
| Logistic (L2) | Medium | Yes | No | 1st-2nd | General purpose |
| Logistic (L1) | Slow | Yes | Yes (sparse) | 2nd-3rd | Feature identification |
| GNB | Very fast | Yes | No | Last | Quick sanity check |
| RBF SVM | Slow | No | No | Variable | Large datasets only |

(Rankings based on Misaki et al., 2010; Varoquaux et al., 2017)

## Searchlight Analysis

### Overview

Searchlight analysis (Kriegeskorte et al., 2006) maps information content across the brain by applying multivariate classification to a small sphere of voxels centered on each brain voxel, producing a whole-brain accuracy map.

### Parameters

| Parameter | Recommended Value | Rationale | Source |
|---|---|---|---|
| **Sphere radius** | **3-4 voxels** (e.g., 4 mm for 2 mm isovoxels) | Balances spatial specificity with sufficient features; 4 mm radius yields ~100-120 voxels per searchlight | Kriegeskorte et al., 2006 |
| **Classifier** | Linear SVM or LDA | Fast classifiers essential given thousands of searchlight positions | Misaki et al., 2010 |
| **Cross-validation** | Leave-one-run-out | Respects temporal structure of fMRI data | Varoquaux et al., 2017 |
| **Correction for multiple comparisons** | Cluster-based permutation or TFCE | Searchlight maps are spatially smooth; voxelwise FWE is overly conservative | Etzel et al., 2013 |
| **Chance level map** | Subtract 1/n_classes or use permutation-based null | Raw accuracy maps are biased; always subtract chance or z-score | Combrisson & Jerbi, 2015 |

### Searchlight Pitfalls

1. **Spatial blurring**: The accuracy at each voxel reflects information in the entire sphere, not just the center voxel. Clusters in searchlight maps are larger than the true informative region (Etzel et al., 2013)
2. **Center bias**: Voxels near the center of a large informative region get high accuracy because their spheres overlap maximally with the informative area; edge voxels get lower accuracy even if equally informative
3. **Double-dipping**: Selecting ROIs based on searchlight maps and then performing further analyses on those ROIs using the same data is circular (Kriegeskorte et al., 2009). Use independent data for follow-up
4. **Variable SNR**: Searchlights near brain edges contain fewer grey-matter voxels, reducing effective feature dimensionality and potentially accuracy. Use a grey-matter mask

## Feature Selection Methods

Feature selection can improve decoding by removing noisy features, but MUST be performed within each cross-validation fold.

### ANOVA-Based Selection

- Compute a one-way ANOVA F-statistic for each feature (voxel/channel) using training data
- Select the top k features by F-value (typical: top **500-2000 voxels** for whole-brain fMRI; Haynes, 2015)
- Fast and effective; widely used in fMRI MVPA
- **Critical**: Compute ANOVA on training data only; selecting on all data leaks information (Kriegeskorte et al., 2009)

### Recursive Feature Elimination (RFE)

- Iteratively remove the least informative features based on classifier weights
- Computationally expensive; requires re-training at each elimination step
- Can improve accuracy but increases risk of overfitting to the cross-validation structure
- Use only when theoretical motivation exists for sparse feature selection

### Anatomical ROI Selection

- Pre-define ROIs using anatomical atlases or functional localizers from independent data
- Avoids the circularity of data-driven feature selection entirely
- **Preferred** when you have strong anatomical hypotheses (Haynes, 2015)

### PCA/ICA-Based Dimensionality Reduction

- PCA: Retain components explaining **95-99%** of variance (community convention; no single citation)
- ICA: Use independent components as features; more common for EEG/MEG
- **Critical**: Fit PCA/ICA on training data only, then transform test data with the training-data projection

## Hyperparameter Tuning

### General Principle

**Never optimize hyperparameters on the test set.** Use nested cross-validation: the inner loop tunes hyperparameters, the outer loop evaluates generalization (Varoquaux et al., 2017).

### SVM C Parameter

- **Default C=1** works well for most neuroimaging applications (Varoquaux et al., 2017)
- If tuning: search over C = {0.001, 0.01, 0.1, 1, 10, 100} in inner cross-validation fold
- Sane defaults often outperform tuned parameters when sample sizes are small, because nested cross-validation has even smaller training sets (Varoquaux et al., 2017)

### Number of Cross-Validation Folds

- **k=5** provides a good bias-variance tradeoff for accuracy estimation (Varoquaux, 2018)
- **Leave-one-out** is unbiased but high variance; leads to unstable estimates (Varoquaux et al., 2017)
- For fMRI, leave-one-run-out is dictated by the data structure (typically 4-12 runs, so k=4-12)
- **Repeat** random splits 10-100 times to stabilize estimates when using k-fold (Varoquaux et al., 2017)

## Software Tools

### Python Ecosystem

| Tool | Primary Use | URL |
|---|---|---|
| **scikit-learn** | General ML: classifiers, cross-validation, feature selection, permutation testing | scikit-learn.org |
| **Nilearn** | fMRI decoding, searchlight, ROI-based MVPA, brain visualization | nilearn.github.io |
| **MNE-Python** | EEG/MEG decoding, temporal generalization, sensor-space MVPA | mne.tools |
| **rsatoolbox** (Python) | RSA: RDM construction, model comparison, noise ceiling, visualization | rsatoolbox.readthedocs.io |
| **PyMVPA** | Full MVPA pipeline for fMRI; searchlight, cross-validation, feature selection | pymvpa.org |
| **BrainIAK** | Advanced fMRI analysis: SRM, HTFA, MVPA, connectivity | brainiak.org |

### MATLAB Ecosystem

| Tool | Primary Use | URL |
|---|---|---|
| **CoSMoMVPA** | Comprehensive MVPA toolbox for fMRI, EEG, MEG; searchlight, RSA | cosmomvpa.org |
| **The Decoding Toolbox (TDT)** | fMRI MVPA with SPM integration; decoding, RSA, reconstruction | tdt.sourceforge.net |
| **RSA Toolbox** (MATLAB) | RSA: RDM construction, model testing, noise ceiling, visualization | github.com/rsagroup/rsatoolbox |
| **MVPA-Light** | Classification and regression for multi-dimensional data; EEG/MEG focus | github.com/treder/MVPA-Light |
| **FieldTrip** | EEG/MEG analysis including MVPA and temporal generalization | fieldtriptoolbox.org |
| **ADAM Toolbox** | EEG MVPA: temporal generalization, group statistics | github.com/fahrenfort/ADAM |

### Tool Selection Guidance

- **fMRI, Python**: Nilearn + scikit-learn for standard MVPA; rsatoolbox for RSA
- **fMRI, MATLAB**: CoSMoMVPA or TDT (integrates with SPM)
- **EEG/MEG, Python**: MNE-Python for temporal decoding and RSA
- **EEG/MEG, MATLAB**: CoSMoMVPA, MVPA-Light, or FieldTrip
- **RSA specifically**: rsatoolbox (Python) or RSA Toolbox (MATLAB) by Kriegeskorte/Nili

## References

- Combrisson, E., & Jerbi, K. (2015). Exceeding chance level by chance. *J. Neurosci. Methods*, 250, 126-136.
- Etzel, J. A., Zacks, J. M., & Braver, T. S. (2013). Searchlight analysis: Promise, pitfalls, and potential. *NeuroImage*, 78, 261-269.
- Haynes, J.-D. (2015). A primer on pattern-based approaches to fMRI. *Neuron*, 87(2), 257-270.
- Kriegeskorte, N., Goebel, R., & Bandettini, P. (2006). Information-based functional brain mapping. *PNAS*, 103(10), 3863-3868.
- Kriegeskorte, N., et al. (2009). Circular analysis in systems neuroscience. *Nat. Neurosci.*, 12(5), 535-540.
- Misaki, M., Kim, Y., Bandettini, P. A., & Kriegeskorte, N. (2010). Comparison of multivariate classifiers and response normalizations for pattern-information fMRI. *NeuroImage*, 53(1), 103-118.
- Varoquaux, G., et al. (2017). Assessing and tuning brain decoders. *NeuroImage*, 145, 166-179.
- Varoquaux, G. (2018). Cross-validation failure: Small sample sizes lead to large error bars. *NeuroImage*, 180, 68-77.
