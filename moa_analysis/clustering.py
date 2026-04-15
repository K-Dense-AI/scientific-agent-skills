"""
clustering.py
=============
Dimensionality reduction and sample clustering for proteomics MoA analysis.

Methods:
    run_pca                  – PCA with variance-explained diagnostics
    run_umap                 – UMAP 2-D/3-D embedding
    run_hierarchical_clustering – Ward linkage dendrogram + cluster labels
    compute_sample_distance  – pairwise Euclidean / correlation distances

All results are stored in adata.obsm / adata.obs for downstream plotting.

Skill references:
    scikit-learn/SKILL.md  – PCA, AgglomerativeClustering, silhouette score
    scanpy/SKILL.md        – adata.obsm storage conventions
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import anndata as ad
from sklearn.decomposition import PCA
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_pca(
    adata: ad.AnnData,
    n_components: int = 50,
    use_top_variable: int | None = 2000,
    scale: bool = True,
    layer: str | None = None,
    key_added: str = "X_pca",
) -> ad.AnnData:
    """
    PCA on the protein abundance matrix.

    Parameters
    ----------
    n_components:     Number of principal components to compute.
    use_top_variable: Restrict to the N most variable proteins before PCA.
                      Set to None to use all proteins.
    scale:            Z-score each protein before PCA (recommended).
    layer:            Use adata.layers[layer] instead of adata.X.
    key_added:        Key in adata.obsm where PC coordinates are stored.

    Stores:
        adata.obsm[key_added]          – (n_samples × n_components) PC matrix
        adata.uns['pca']['variance_ratio'] – explained variance ratios
        adata.uns['pca']['loadings']       – PC loadings (proteins × PCs)
        adata.uns['pca']['top_genes']      – top 10 proteins per PC
    """
    matrix = _get_matrix(adata, layer)              # (samples × proteins)

    # Select most variable proteins
    if use_top_variable is not None and use_top_variable < matrix.shape[1]:
        var = np.nanvar(matrix, axis=0)
        top_idx = np.argsort(var)[-use_top_variable:]
        sub_matrix = matrix[:, top_idx]
        gene_names = np.array(adata.var_names)[top_idx]
    else:
        sub_matrix = matrix
        gene_names = np.array(adata.var_names)

    # Replace remaining NaN with column medians (should be minimal after imputation)
    sub_matrix = _fill_na(sub_matrix)

    if scale:
        scaler = StandardScaler()
        sub_matrix = scaler.fit_transform(sub_matrix)

    n_components = min(n_components, sub_matrix.shape[0] - 1, sub_matrix.shape[1])
    pca = PCA(n_components=n_components, random_state=42)
    coords = pca.fit_transform(sub_matrix)   # (samples × PCs)

    # Top contributing proteins per PC
    loadings = pd.DataFrame(
        pca.components_.T,
        index=gene_names,
        columns=[f"PC{i+1}" for i in range(n_components)],
    )
    top_genes = {
        f"PC{i+1}": loadings[f"PC{i+1}"].abs().nlargest(10).index.tolist()
        for i in range(min(5, n_components))
    }

    adata.obsm[key_added] = coords.astype(np.float32)
    adata.uns["pca"] = {
        "variance_ratio": pca.explained_variance_ratio_.tolist(),
        "cumulative_variance": np.cumsum(pca.explained_variance_ratio_).tolist(),
        "loadings": loadings,
        "top_genes": top_genes,
        "n_components": n_components,
    }

    var_1 = pca.explained_variance_ratio_[0] * 100
    var_2 = pca.explained_variance_ratio_[1] * 100 if n_components > 1 else 0
    print(
        f"[run_pca] PC1={var_1:.1f}%  PC2={var_2:.1f}%  "
        f"({n_components} PCs cover "
        f"{np.cumsum(pca.explained_variance_ratio_)[-1]*100:.1f}% variance)"
    )
    return adata


def run_umap(
    adata: ad.AnnData,
    n_components: int = 2,
    n_neighbors: int = 10,
    min_dist: float = 0.3,
    metric: str = "euclidean",
    use_pca: bool = True,
    n_pcs: int = 20,
    random_state: int = 42,
    key_added: str = "X_umap",
) -> ad.AnnData:
    """
    UMAP embedding for 2-D visualisation of sample relationships.

    Parameters
    ----------
    use_pca:    Run on PCA-reduced representation rather than full matrix
                (recommended for noisy proteomics data).
    n_pcs:      Number of PCs to use as UMAP input (requires run_pca first).
    key_added:  Key in adata.obsm where UMAP coordinates are stored.
    """
    try:
        import umap
    except ImportError:
        raise ImportError(
            "Install umap-learn: uv pip install umap-learn"
        ) from None

    if use_pca and "X_pca" in adata.obsm:
        X = adata.obsm["X_pca"][:, :n_pcs]
    else:
        X = _fill_na(_get_matrix(adata, None))

    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric=metric,
        random_state=random_state,
    )
    embedding = reducer.fit_transform(X)

    adata.obsm[key_added] = embedding.astype(np.float32)
    print(f"[run_umap] UMAP {n_components}-D embedding complete ({len(X)} samples)")
    return adata


def run_hierarchical_clustering(
    adata: ad.AnnData,
    n_clusters: int | None = None,
    linkage_method: str = "ward",
    metric: str = "euclidean",
    use_pca: bool = True,
    n_pcs: int = 20,
    cluster_col: str = "hclust_cluster",
    auto_select_k: bool = True,
    k_range: range | None = None,
) -> ad.AnnData:
    """
    Hierarchical clustering of samples with optional automatic k selection.

    Parameters
    ----------
    n_clusters:       Fixed number of clusters.  If None and auto_select_k
                      is True, k is chosen by maximising silhouette score.
    linkage_method:   'ward' (default), 'complete', 'average', 'single'.
    auto_select_k:    Try k in k_range and pick best silhouette score.
    k_range:          Range of k values to try; defaults to range(2, min(8, n//2)+1).
    cluster_col:      obs column name for cluster labels.

    Stores:
        adata.obs[cluster_col]         – integer cluster labels
        adata.uns['hclust']['linkage'] – linkage matrix
        adata.uns['hclust']['silhouette_scores'] – scores per k (if auto)
    """
    if use_pca and "X_pca" in adata.obsm:
        X = adata.obsm["X_pca"][:, :n_pcs]
    else:
        X = _fill_na(_get_matrix(adata, None))

    Z = linkage(X, method=linkage_method, metric=metric)
    n_samples = len(X)

    if auto_select_k and n_clusters is None:
        k_range = k_range or range(2, min(8, n_samples // 2) + 1)
        sil_scores = {}
        for k in k_range:
            labels = fcluster(Z, k, criterion="maxclust")
            if len(np.unique(labels)) < 2:
                continue
            sil_scores[k] = silhouette_score(X, labels)
        best_k = max(sil_scores, key=sil_scores.get)
        print(
            f"[hierarchical_clustering] Auto-selected k={best_k} "
            f"(silhouette={sil_scores[best_k]:.3f})"
        )
    else:
        best_k = n_clusters or 3
        sil_scores = {}

    labels = fcluster(Z, best_k, criterion="maxclust")
    adata.obs[cluster_col] = labels.astype(str)
    adata.uns["hclust"] = {
        "linkage": Z,
        "n_clusters": best_k,
        "silhouette_scores": sil_scores,
    }
    return adata


def compute_sample_distance(
    adata: ad.AnnData,
    metric: str = "correlation",
    use_pca: bool = True,
    n_pcs: int = 20,
) -> pd.DataFrame:
    """
    Compute pairwise sample distance matrix.

    Parameters
    ----------
    metric:   'correlation' (1 − Pearson r), 'euclidean', or any
              scipy.spatial.distance metric.
    use_pca:  Use PCA-space distances (recommended; reduces noise).

    Returns
    -------
    pd.DataFrame  (samples × samples) pairwise distance matrix.
    """
    if use_pca and "X_pca" in adata.obsm:
        X = adata.obsm["X_pca"][:, :n_pcs]
    else:
        X = _fill_na(_get_matrix(adata, None))

    dist = squareform(pdist(X, metric=metric))
    return pd.DataFrame(dist, index=adata.obs_names, columns=adata.obs_names)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_matrix(adata: ad.AnnData, layer: str | None) -> np.ndarray:
    if layer and layer in adata.layers:
        return np.array(adata.layers[layer], dtype=np.float64)
    return np.array(adata.X, dtype=np.float64)


def _fill_na(matrix: np.ndarray) -> np.ndarray:
    """Replace NaN with column median (last-resort fallback after imputation)."""
    result = matrix.copy()
    for j in range(result.shape[1]):
        col = result[:, j]
        nan_mask = np.isnan(col)
        if nan_mask.any():
            med = np.nanmedian(col)
            result[nan_mask, j] = med if not np.isnan(med) else 0.0
    return result
