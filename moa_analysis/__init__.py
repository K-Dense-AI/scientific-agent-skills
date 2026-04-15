"""
MoA Analysis Pipeline
Mechanism-of-action analysis from quantitative proteomics data.

Skills used:
    pyopenms         – MS data structures and file I/O
    statistical-analysis – assumption checks, t-tests, FDR correction
    scikit-learn     – PCA, clustering, RandomForest MoA classifier
    scanpy / anndata – AnnData container for multi-sample proteomics
"""

from .data_loader import simulate_p53_experiment, load_from_csv, build_anndata
from .preprocessing import filter_by_missingness, impute_missing, normalize, log2_transform
from .differential import run_differential_abundance, classify_hits
from .enrichment import build_pathway_genesets, run_ora, score_signatures
from .clustering import run_pca, run_hierarchical_clustering, run_umap
from .moa_classifier import build_reference_signatures, train_moa_classifier, predict_moa
from .plots import (
    plot_volcano, plot_heatmap, plot_pca,
    plot_pathway_enrichment, plot_moa_similarity,
)

__all__ = [
    "simulate_p53_experiment", "load_from_csv", "build_anndata",
    "filter_by_missingness", "impute_missing", "normalize", "log2_transform",
    "run_differential_abundance", "classify_hits",
    "build_pathway_genesets", "run_ora", "score_signatures",
    "run_pca", "run_hierarchical_clustering", "run_umap",
    "build_reference_signatures", "train_moa_classifier", "predict_moa",
    "plot_volcano", "plot_heatmap", "plot_pca",
    "plot_pathway_enrichment", "plot_moa_similarity",
]
