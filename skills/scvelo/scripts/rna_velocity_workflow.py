"""RNA velocity from raw, aligned spliced/unspliced layers (scVelo 0.3.4).

The workflow mutates AnnData in place; pass a copy to retain all input genes.
Run --help for a local-file CLI. No datasets are downloaded automatically.
"""
from __future__ import annotations

import argparse
from importlib.metadata import version
from pathlib import Path

import anndata as ad
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
import scvelo as scv
from packaging.version import Version
from scipy import sparse


def validate_layers(adata):
    """Reject missing, nonfinite, negative, empty or ambiguously indexed counts."""
    if not adata.obs_names.is_unique or not adata.var_names.is_unique:
        raise ValueError("Cell and gene identifiers must be unique before alignment.")
    if adata.n_obs < 5 or adata.n_vars < 3:
        raise ValueError("This workflow needs at least 5 cells and 3 genes to run.")
    for name in ("spliced", "unspliced"):
        if name not in adata.layers:
            raise ValueError(f"Missing '{name}' layer; supply raw quantifier counts.")
        matrix = adata.layers[name]
        values = matrix.data if sparse.issparse(matrix) else np.asarray(matrix)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f"'{name}' must contain finite nonnegative counts.")
        if not np.any(values > 0):
            raise ValueError(f"'{name}' contains no positive counts.")
    if np.any(np.asarray(adata.layers["spliced"].sum(axis=1)).ravel() == 0):
        raise ValueError("Remove cells with zero spliced library size before analysis.")


def _check_versions(mode, make_plots):
    """Reject confirmed upstream failures, without silently changing estimators."""
    if Version(scv.__version__) == Version("0.3.4"):
        if mode == "stochastic" and Version(np.__version__) >= Version("2"):
            raise RuntimeError(
                "scVelo 0.3.4 default stochastic GLS fails with NumPy >=2. "
                "Use a separately validated legacy NumPy<2/Scanpy<1.12 environment, "
                "or explicitly choose a different scientific model."
            )
        if (mode == "dynamical" or make_plots) and Version(pd.__version__) >= Version("3"):
            raise RuntimeError("scVelo 0.3.4 dynamical fitting/plots require pandas<3.")


def _save_plot(function, adata, destination, **kwargs):
    """Own figure paths directly; scVelo's figdir/save prefix is not a path API."""
    before = set(plt.get_fignums())
    try:
        function(adata, show=False, save=False, **kwargs)
        figure = plt.gcf()
        figure.savefig(destination, dpi=150, bbox_inches="tight")
    finally:
        for number in set(plt.get_fignums()) - before:
            plt.close(number)


def run_velocity_analysis(
    adata,
    groupby="leiden",
    n_top_genes=2000,
    n_neighbors=30,
    mode="dynamical",
    n_jobs=1,
    output_dir="velocity_results",
    *,
    min_shared_counts=20,
    n_pcs=30,
    random_state=0,
    make_plots=True,
    recover_max_iter=10,
):
    """Analyze raw velocity layers in place, rebuilding X, PCA and neighbors.

    Existing X (including integrated/scaled values) is replaced from spliced
    counts; existing UMAP is recomputed for plotted runs. Cluster annotations
    are preserved, but their biological validity is the caller's responsibility.
    Input layers must be raw counts (fractional count estimates are permitted),
    never logged/scaled/normalized. Numeric inspection cannot establish this
    provenance. Save the original full-gene input before running.
    """
    if mode not in {"deterministic", "stochastic", "dynamical"}:
        raise ValueError("mode must be deterministic, stochastic or dynamical")
    validate_layers(adata)
    if "velocity_workflow" in adata.uns or any(k in adata.layers for k in ("Ms", "Mu", "velocity")):
        raise ValueError("Use fresh raw layers; existing velocity preprocessing must not be repeated.")
    for name, value, minimum in (("n_top_genes", n_top_genes, 3), ("n_neighbors", n_neighbors, 2),
                                 ("n_pcs", n_pcs, 1), ("n_jobs", n_jobs, 1),
                                 ("recover_max_iter", recover_max_iter, 1)):
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}")
    if not np.isfinite(min_shared_counts) or min_shared_counts < 0:
        raise ValueError("min_shared_counts must be finite and nonnegative")
    _check_versions(mode, make_plots)
    if groupby is not None and groupby not in adata.obs:
        raise ValueError(f"Grouping column {groupby!r} is missing; use groupby=None to omit ranking.")
    if groupby is not None and adata.obs[groupby].isna().any():
        raise ValueError("Grouping labels must not be missing.")

    # Rebuild expression geometry from explicit count provenance. Store raw
    # layers before normalization; filtered-out genes remain in the input file.
    adata.X = adata.layers["spliced"].astype(np.float32).copy()
    for key in ("spliced", "unspliced"):
        adata.layers[f"{key}_counts"] = adata.layers[key].copy()
        adata.layers[key] = adata.layers[key].astype(np.float32).copy()
    for key in ("log1p", "neighbors", "pca"):
        adata.uns.pop(key, None)
    for key in ("initial_size", "initial_size_spliced", "initial_size_unspliced"):
        if key in adata.obs:
            del adata.obs[key]
    print("[1/5] Filter counts, normalize layers, select genes and rebuild neighbors")
    scv.pp.filter_and_normalize(adata, min_shared_counts=min_shared_counts,
                                layers_normalize=["spliced", "unspliced"])
    if adata.n_vars < 3:
        raise ValueError("Fewer than 3 genes survived count filtering; inspect coverage and thresholds.")
    sc.pp.log1p(adata)  # only X; spliced/unspliced stay on linear scale
    sc.pp.highly_variable_genes(adata, n_top_genes=min(n_top_genes, adata.n_vars), subset=True)
    if adata.n_vars < 3:
        raise ValueError("Fewer than 3 variable genes remain; inspect the expression distribution.")
    actual_pcs = min(n_pcs, adata.n_obs - 1, adata.n_vars - 1)
    actual_neighbors = min(n_neighbors, adata.n_obs - 1)
    sc.pp.pca(adata, n_comps=actual_pcs, random_state=random_state)
    sc.pp.neighbors(adata, n_neighbors=actual_neighbors, n_pcs=actual_pcs,
                    use_rep="X_pca", random_state=random_state)
    scv.pp.moments(adata, n_neighbors=None)  # consume the explicit Scanpy graph

    print(f"[2/5] Fit {mode} model")
    if mode == "dynamical":
        scv.tl.recover_dynamics(adata, var_names="all", n_jobs=n_jobs,
                                max_iter=recover_max_iter, show_progress_bar=False)
        if not np.isfinite(adata.var["fit_likelihood"]).any():
            raise ValueError("No finite dynamical fits; inspect phase portraits and input coverage.")
    scv.tl.velocity(adata, mode=mode)
    selected = adata.var["velocity_genes"].to_numpy(dtype=bool)
    if selected.sum() < 2 or not np.isfinite(adata.layers["velocity"][:, selected]).all():
        raise ValueError("Fewer than 2 usable velocity genes, or nonfinite fitted velocities.")
    scv.tl.velocity_graph(adata, n_jobs=n_jobs, show_progress_bar=False)
    if not adata.uns["velocity_graph"].nnz:
        raise ValueError("Velocity graph is empty; inspect fitted genes and neighborhood geometry.")

    print("[3/5] Compute coherence and relative time")
    scv.tl.velocity_confidence(adata)
    scv.tl.velocity_pseudotime(adata)
    if mode == "dynamical":
        scv.tl.latent_time(adata)
    diagnostics = {}
    for key in ("velocity_confidence", "velocity_pseudotime", "latent_time"):
        if key not in adata.obs:
            continue
        values = adata.obs[key].to_numpy()
        finite = values[np.isfinite(values)]
        diagnostics[f"{key}_nonfinite"] = int(len(values) - len(finite))
        diagnostics[f"{key}_constant"] = bool(len(finite) == 0 or np.ptp(finite) == 0)
        if len(finite) != len(values) or diagnostics[f"{key}_constant"]:
            print(f"[WARN] {key} is nonfinite or constant; it does not support an ordering/confidence claim.")
    if groupby is not None:
        adata.obs[groupby] = adata.obs[groupby].astype("category")
        sizes = adata.obs[groupby].value_counts()
        if len(sizes) >= 2 and (sizes >= 2).all():
            scv.tl.rank_velocity_genes(adata, groupby=groupby, min_corr=0.3)

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    print("[4/5] Render figures" if make_plots else "[4/5] Figures disabled")
    if make_plots:
        sc.tl.umap(adata, random_state=random_state)
        _save_plot(scv.pl.velocity_embedding_stream, adata, destination / "velocity_stream.png",
                   basis="umap", color=groupby, title="RNA velocity (projected)")
        _save_plot(scv.pl.velocity_embedding, adata, destination / "velocity_arrows.png",
                   basis="umap", color=groupby, arrow_length=3, arrow_size=2)
        _save_plot(scv.pl.scatter, adata, destination / "pseudotime.png", basis="umap",
                   color="velocity_pseudotime", cmap="gnuplot")
        _save_plot(scv.pl.scatter, adata, destination / "velocity_quality.png", basis="umap",
                   color=["velocity_length", "velocity_confidence"], cmap="coolwarm", perc=[5, 95])
        if mode == "dynamical":
            _save_plot(scv.pl.scatter, adata, destination / "latent_time.png", basis="umap",
                       color="latent_time", cmap="gnuplot")
            genes = adata.var["fit_likelihood"].dropna().nlargest(min(50, adata.n_vars)).index
            _save_plot(scv.pl.heatmap, adata, destination / "dynamical_gene_heatmap.png",
                       var_names=genes, sortby="latent_time", col_color=groupby,
                       n_convolve=min(30, adata.n_obs))

    adata.uns["velocity_workflow"] = {
        "mode": mode, "n_neighbors": actual_neighbors, "n_pcs": actual_pcs,
        "random_state": random_state, "input_layers": "raw spliced and unspliced counts",
        "diagnostics": diagnostics,
        "packages": {name: version(name) for name in ("scvelo", "scanpy", "anndata", "numpy", "pandas")},
    }
    print("[5/5] Save annotated data")
    adata.write_h5ad(destination / "adata_velocity.h5ad")
    print(f"[OK] Cells: {adata.n_obs}; selected genes: {adata.n_vars}; velocity genes: {selected.sum()}")
    print("Velocity coherence is a descriptive score, not calibrated certainty.")
    return adata


def load_from_loom(loom_path, processed_h5ad=None):
    """Read local loom counts and optionally align to processed metadata exactly.

    No barcode rewriting or silent intersections. Resolve library prefixes and
    gene IDs explicitly before combining mismatched files. Extra loom cells and
    genes are permitted, but every processed cell/gene must have a match.
    """
    counts = ad.io.read_loom(loom_path, X_name="spliced", sparse=True)
    validate_layers(counts)
    if processed_h5ad is None:
        return counts
    processed = ad.read_h5ad(processed_h5ad)
    if not processed.obs_names.is_unique or not processed.var_names.is_unique:
        raise ValueError("Processed cell and gene identifiers must be unique.")
    if not processed.obs_names.isin(counts.obs_names).all() or not processed.var_names.isin(counts.var_names).all():
        raise ValueError("Processed IDs do not all match loom IDs; align barcodes and gene identifiers explicitly.")
    aligned = counts[processed.obs_names, processed.var_names]
    for key in ("spliced", "unspliced"):
        processed.layers[key] = aligned.layers[key].copy()
    validate_layers(processed)
    return processed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Local .h5ad or .loom with raw spliced/unspliced layers")
    parser.add_argument("--processed-h5ad", help="Metadata/embedding file to align with loom counts")
    parser.add_argument("--groupby", default=None, help="Optional annotation column for coloring/ranking")
    parser.add_argument("--mode", choices=("deterministic", "stochastic", "dynamical"), default="dynamical")
    parser.add_argument("--n-top-genes", type=int, default=2000)
    parser.add_argument("--n-neighbors", type=int, default=30)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--output-dir", default="velocity_results")
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    if Path(args.input).suffix.lower() == ".loom":
        data = load_from_loom(args.input, args.processed_h5ad)
    else:
        if args.processed_h5ad:
            parser.error("--processed-h5ad is only used with .loom input")
        data = ad.read_h5ad(args.input)
    run_velocity_analysis(data, groupby=args.groupby, n_top_genes=args.n_top_genes,
                          n_neighbors=args.n_neighbors, mode=args.mode, n_jobs=args.n_jobs,
                          output_dir=args.output_dir, make_plots=not args.no_plots)


if __name__ == "__main__":
    main()
