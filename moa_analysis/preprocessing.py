"""
preprocessing.py
================
QC, normalization, and imputation for label-free quantitative proteomics.

Workflow order (call in sequence):
    1. log2_transform        – convert raw intensities to log2 scale
    2. filter_by_missingness – remove proteins with too many NaN
    3. normalize             – median-centering or quantile normalization
    4. impute_missing        – MinProb (MNAR) or KNN (MAR)

Skill references:
    statistical-analysis/SKILL.md – normalization justification
    scanpy/SKILL.md               – AnnData manipulation patterns
"""

from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
import anndata as ad
from scipy.stats import rankdata


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log2_transform(adata: ad.AnnData, inplace: bool = True) -> ad.AnnData:
    """
    Apply log2(x) to raw intensities.  Zero / negative values become NaN.

    Skips transformation if values already appear log-scaled (median < 100).
    """
    adata = adata if inplace else adata.copy()

    matrix = adata.X.copy().astype(np.float64)
    median_val = np.nanmedian(matrix)

    if median_val < 100:
        warnings.warn(
            f"Median value is {median_val:.1f} — data may already be log-scaled. "
            "Skipping log2 transform.",
            UserWarning,
            stacklevel=2,
        )
        return adata

    matrix[matrix <= 0] = np.nan
    adata.X = np.log2(matrix).astype(np.float32)
    adata.uns["log2_transformed"] = True
    return adata


def filter_by_missingness(
    adata: ad.AnnData,
    max_missing_fraction: float = 0.70,
    min_valid_per_group: int = 2,
    group_col: str = "condition",
    inplace: bool = True,
) -> ad.AnnData:
    """
    Remove proteins that are missing in too many samples.

    Two complementary criteria (protein kept if it passes either):
    - Global filter : fraction of NaN across ALL samples < max_missing_fraction
    - Group filter  : at least min_valid_per_group non-NaN values in at least
                      one experimental group (allows group-specific proteins)

    Parameters
    ----------
    max_missing_fraction:  Remove proteins missing in more than this fraction
                           of all samples (default 0.70 = 70 %).
    min_valid_per_group:   Minimum non-NaN observations required within any
                           single group for a protein to be retained (default 2).
    group_col:             obs column that defines experimental groups.
    """
    adata = adata if inplace else adata.copy()
    matrix = np.array(adata.X, dtype=np.float64)
    n_samples, n_proteins = matrix.shape

    # Global missingness
    global_missing = np.mean(np.isnan(matrix), axis=0)
    global_pass = global_missing < max_missing_fraction

    # Per-group missingness
    groups = adata.obs[group_col].unique()
    group_pass = np.zeros(n_proteins, dtype=bool)
    for grp in groups:
        mask = (adata.obs[group_col] == grp).values
        n_valid = np.sum(~np.isnan(matrix[mask, :]), axis=0)
        group_pass |= (n_valid >= min_valid_per_group)

    keep = global_pass & group_pass
    n_removed = n_proteins - keep.sum()

    adata = adata[:, keep].copy()
    adata.uns["filter_missingness"] = {
        "n_removed": int(n_removed),
        "n_retained": int(keep.sum()),
        "max_missing_fraction": max_missing_fraction,
    }
    print(
        f"[filter_by_missingness] Retained {keep.sum()} / {n_proteins} proteins "
        f"(removed {n_removed}, {n_removed/n_proteins:.1%} of total)"
    )
    return adata


def normalize(
    adata: ad.AnnData,
    method: str = "median_centering",
    reference_col: str | None = None,
    inplace: bool = True,
) -> ad.AnnData:
    """
    Sample-level normalization to remove systematic loading differences.

    Parameters
    ----------
    method:
        'median_centering'  – shift each sample so its median matches the
                              grand median; appropriate for log2 data.
        'quantile'          – full quantile normalization (assumes same
                              distribution across all samples).
        'vsn'               – variance-stabilizing normalization via iterative
                              median polish (simplified implementation).
        'none'              – no normalization.
    reference_col:
        obs column with 'True' for reference samples used to compute the
        target median (median_centering only). Uses all samples if None.
    """
    adata = adata if inplace else adata.copy()
    matrix = np.array(adata.X, dtype=np.float64)

    if method == "none":
        return adata

    if method == "median_centering":
        matrix = _median_centering(matrix, adata.obs, reference_col)

    elif method == "quantile":
        matrix = _quantile_normalize(matrix)

    elif method == "vsn":
        matrix = _vsn_normalize(matrix)

    else:
        raise ValueError(f"Unknown normalization method: {method!r}")

    adata.X = matrix.astype(np.float32)
    adata.uns["normalization"] = method
    print(f"[normalize] Applied '{method}' normalization")
    return adata


def impute_missing(
    adata: ad.AnnData,
    method: str = "minprob",
    n_neighbors: int = 5,
    width: float = 0.3,
    downshift: float = 1.8,
    inplace: bool = True,
) -> ad.AnnData:
    """
    Impute missing values.

    Parameters
    ----------
    method:
        'minprob'  – draw from a Gaussian distribution at the low end of
                     each sample's intensity distribution (MNAR assumption;
                     default for proteomics with data-dependent acquisition).
        'knn'      – K-nearest neighbour imputation (MAR assumption).
        'median'   – replace NaN with column (protein) median across samples.
        'zero'     – replace NaN with 0 (use only for downstream methods that
                     treat 0 as absent, e.g. GSEA with binary presence).
    width:         Width of Gaussian for MinProb (fraction of sample SD).
    downshift:     Downshift of Gaussian mean from sample mean, in SD units.
    n_neighbors:   k for KNN imputation.
    """
    adata = adata if inplace else adata.copy()
    matrix = np.array(adata.X, dtype=np.float64)
    n_missing_before = np.sum(np.isnan(matrix))

    if method == "minprob":
        matrix = _minprob_impute(matrix, width=width, downshift=downshift)

    elif method == "knn":
        matrix = _knn_impute(matrix, k=n_neighbors)

    elif method == "median":
        col_medians = np.nanmedian(matrix, axis=0)
        inds = np.where(np.isnan(matrix))
        matrix[inds] = np.take(col_medians, inds[1])

    elif method == "zero":
        matrix = np.nan_to_num(matrix, nan=0.0)

    else:
        raise ValueError(f"Unknown imputation method: {method!r}")

    n_missing_after = np.sum(np.isnan(matrix))
    adata.X = matrix.astype(np.float32)
    adata.uns["imputation"] = {
        "method": method,
        "n_imputed": int(n_missing_before - n_missing_after),
    }
    print(
        f"[impute_missing] Imputed {n_missing_before - n_missing_after} values "
        f"using '{method}'"
    )
    return adata


# ---------------------------------------------------------------------------
# Private normalization helpers
# ---------------------------------------------------------------------------

def _median_centering(
    matrix: np.ndarray,
    obs: pd.DataFrame,
    reference_col: str | None,
) -> np.ndarray:
    """Shift each sample median to the grand median of reference samples."""
    if reference_col is not None and reference_col in obs.columns:
        ref_mask = obs[reference_col].values.astype(bool)
        target_median = np.nanmedian(matrix[ref_mask, :])
    else:
        target_median = np.nanmedian(matrix)

    sample_medians = np.nanmedian(matrix, axis=1, keepdims=True)
    return matrix - sample_medians + target_median


def _quantile_normalize(matrix: np.ndarray) -> np.ndarray:
    """Full quantile normalization (Bolstad 2003)."""
    n_samples, n_features = matrix.shape
    result = matrix.copy()

    # Compute target distribution (mean of sorted values per rank)
    sorted_cols = np.sort(matrix, axis=1)
    target = np.nanmean(sorted_cols, axis=0)

    for i in range(n_samples):
        row = matrix[i, :]
        valid = ~np.isnan(row)
        if valid.sum() == 0:
            continue
        ranks = rankdata(row[valid], method="ordinal") - 1
        target_idx = np.round(
            ranks * (len(target) - 1) / (valid.sum() - 1)
        ).astype(int)
        target_idx = np.clip(target_idx, 0, len(target) - 1)
        result[i, valid] = target[target_idx]

    return result


def _vsn_normalize(matrix: np.ndarray, n_iter: int = 20) -> np.ndarray:
    """Simplified variance-stabilizing normalization via median polish."""
    result = matrix.copy()
    for _ in range(n_iter):
        row_medians = np.nanmedian(result, axis=1, keepdims=True)
        result -= row_medians
        col_medians = np.nanmedian(result, axis=0, keepdims=True)
        result -= col_medians
    return result


# ---------------------------------------------------------------------------
# Private imputation helpers
# ---------------------------------------------------------------------------

def _minprob_impute(
    matrix: np.ndarray,
    width: float = 0.3,
    downshift: float = 1.8,
    seed: int = 0,
) -> np.ndarray:
    """
    MinProb imputation (Lazar 2016):
    Replace NaN in each sample with draws from N(μ - δ*σ, (w*σ)²)
    where μ, σ are the observed mean/SD of that sample.
    """
    rng = np.random.default_rng(seed)
    result = matrix.copy()
    n_samples = matrix.shape[0]

    for i in range(n_samples):
        row = matrix[i, :]
        valid = row[~np.isnan(row)]
        if len(valid) == 0:
            continue
        mu = np.mean(valid)
        sigma = np.std(valid)
        missing_idx = np.where(np.isnan(row))[0]
        imputed = rng.normal(
            loc=mu - downshift * sigma,
            scale=width * sigma,
            size=len(missing_idx),
        )
        result[i, missing_idx] = imputed

    return result


def _knn_impute(matrix: np.ndarray, k: int = 5) -> np.ndarray:
    """
    KNN imputation: for each missing value, find k nearest neighbor
    proteins (by column) using observed samples and replace with their mean.
    """
    from sklearn.impute import KNNImputer
    imputer = KNNImputer(n_neighbors=k, weights="distance")
    return imputer.fit_transform(matrix)
