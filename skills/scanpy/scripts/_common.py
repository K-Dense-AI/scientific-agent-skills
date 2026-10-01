#!/usr/bin/env python3
"""
Shared helpers for the scanpy script toolkit.

Every CLI script in this directory imports from this module so that data
loading, saving, figure configuration, and logging behave consistently.
This file is NOT a CLI itself; import it:

    from _common import load_anndata, save_anndata, configure_scanpy, info
"""

import os
import sys


def info(msg):
    """Print a progress message to stderr-friendly stdout with a marker."""
    print(f"[scanpy] {msg}", flush=True)


def die(msg, code=1):
    """Print an error and exit."""
    print(f"Error: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def _import_scanpy():
    try:
        import scanpy as sc  # noqa: F401
        return sc
    except ImportError:
        die('scanpy not installed. Install with: uv pip install "scanpy[leiden]"')


def configure_scanpy(figdir="figures", dpi=120, verbosity=1, autosave=False,
                     file_format="png"):
    """Apply consistent scanpy settings and return the scanpy module.

    Note: autosave is left off by default because the toolkit scripts pass
    explicit ``save=`` suffixes to plotting calls for predictable filenames.
    """
    sc = _import_scanpy()
    sc.settings.verbosity = verbosity
    sc.set_figure_params(dpi=dpi, facecolor="white")
    sc.settings.figdir = figdir
    sc.settings.file_format_figs = file_format
    sc.settings.autosave = autosave
    sc.settings.autoshow = False
    os.makedirs(figdir, exist_ok=True)
    return sc


def load_anndata(path, var_names="gene_symbols"):
    """Load an AnnData object, dispatching on the file extension / layout.

    Supported inputs:
      * ``.h5ad``                  -> sc.read_h5ad
      * ``.h5`` (10x CellRanger)   -> sc.read_10x_h5
      * ``.csv`` / ``.tsv`` / ``.txt`` -> sc.read_csv / read_text
      * ``.loom``                  -> sc.read_loom
      * ``.mtx``                   -> sc.read (matrix market)
      * a directory                -> sc.read_10x_mtx (10x mtx folder)
    """
    sc = _import_scanpy()
    if not os.path.exists(path):
        die(f"input not found: {path}")

    path = os.fspath(path)
    lower = path.lower()
    if os.path.isdir(path):
        info(f"Reading 10x mtx directory: {path}")
        return sc.read_10x_mtx(path, var_names=var_names)
    if lower.endswith(".h5ad"):
        return sc.read_h5ad(path)
    if lower.endswith(".h5"):
        info("Reading 10x HDF5 (.h5)")
        return sc.read_10x_h5(path)
    if lower.endswith(".loom"):
        return sc.read_loom(path)
    if lower.endswith(".csv"):
        return sc.read_csv(path)
    if lower.endswith((".tsv", ".txt")):
        return sc.read_text(path)
    if lower.endswith(".mtx") or lower.endswith(".mtx.gz"):
        return sc.read_mtx(path)
    die(f"unrecognized input format: {path}")


def save_anndata(adata, path):
    """Write an AnnData object to .h5ad, creating parent dirs as needed."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    adata.write_h5ad(path)
    info(f"Wrote {path}  ({adata.n_obs} cells x {adata.n_vars} genes)")


def add_io_args(parser, default_output=None):
    """Attach the standard input/output/figdir arguments to an argparse parser."""
    parser.add_argument("input", help="Input file (.h5ad, .h5, .csv, .loom, or 10x mtx dir)")
    parser.add_argument("-o", "--output", default=default_output,
                        help="Output .h5ad path" +
                             (f" (default: {default_output})" if default_output else ""))
    parser.add_argument("--figdir", default="figures",
                        help="Directory for saved figures (default: figures)")
    return parser


def _named_keys(mapping):
    """Named keys of an AnnData mapping, in order.

    anndata >= 0.13 reports an unnamed `None` key on `.layers` standing for X
    itself. Joining that into a string raises TypeError, so filter it out.
    """
    return [key for key in mapping.keys() if isinstance(key, str)]


def summarize(adata):
    """Return a short human-readable summary string of an AnnData object."""
    lines = [f"{adata.n_obs} cells x {adata.n_vars} genes"]
    if len(adata.obs.columns):
        lines.append("obs: " + ", ".join(adata.obs.columns[:20]))
    obsm = _named_keys(adata.obsm)
    if obsm:
        lines.append("obsm: " + ", ".join(obsm))
    layers = _named_keys(adata.layers)
    if layers:
        lines.append("layers: " + ", ".join(layers))
    return "\n".join(lines)


def validate_counts(matrix, label="counts", require_nonzero_cells=True):
    """Validate finite, nonnegative integer counts without densifying sparse input.

    Values alone cannot establish provenance: the caller must identify the actual
    unnormalized assay. Floating dtypes are accepted when every value is integral.
    """
    import numpy as np
    from scipy import sparse

    if matrix is None or len(matrix.shape) != 2 or min(matrix.shape) == 0:
        die(f"{label}: expected a nonempty cells x genes count matrix")
    values = matrix.data if sparse.issparse(matrix) else np.asarray(matrix)
    if (not np.isfinite(values).all() or (values < 0).any()
            or not np.equal(values, np.floor(values)).all()):
        die(f"{label}: expected finite, nonnegative integer counts; verify assay provenance")
    if require_nonzero_cells and (np.asarray(matrix.sum(axis=1)).ravel() <= 0).any():
        die(f"{label}: contains zero-total cells; filter them before normalization")


def prepare_counts(adata, layer=None):
    """Select explicitly identified counts and preserve an independent copy."""
    import numpy as np
    from scipy import sparse

    if layer is not None and layer not in adata.layers:
        die(f"counts layer '{layer}' is missing")
    matrix = adata.X if layer is None else adata.layers[layer]
    validate_counts(matrix, "X" if layer is None else f"layers[{layer!r}]")
    if layer is None and "log1p" in adata.uns:
        die("X has log1p provenance; select the original --counts-layer explicitly")
    if layer is None and "counts" in adata.layers:
        old = adata.layers["counts"]
        delta = old - matrix
        differs = delta.nnz != 0 if sparse.issparse(delta) else np.any(delta != 0)
        if differs:
            die("X differs from the preserved counts layer; select --counts-layer counts")
    adata.X = matrix.copy()
    adata.layers["counts"] = matrix.copy()
    adata.uns.pop("log1p", None)


def normalize_hvg(sc, adata, *, target_sum=1e4, n_top_genes=2000,
                  flavor="seurat", batch_key=None):
    """Keep all genes/counts, select HVGs on the flavor's required representation."""
    if target_sum <= 0 or n_top_genes < 1:
        die("target_sum and n_top_genes must be positive")
    if batch_key is not None:
        ensure_categories(adata, batch_key)
    count_flavor = flavor in {"seurat_v3", "seurat_v3_paper"}
    if count_flavor:
        sc.pp.highly_variable_genes(adata, layer="counts", n_top_genes=n_top_genes,
                                    flavor=flavor, batch_key=batch_key)
    sc.pp.normalize_total(adata, target_sum=target_sum)
    sc.pp.log1p(adata)
    if not count_flavor:
        sc.pp.highly_variable_genes(adata, n_top_genes=n_top_genes,
                                    flavor=flavor, batch_key=batch_key)
    if not adata.var["highly_variable"].any():
        die("HVG selection returned no genes; inspect expression/filtering parameters")
    adata.raw = adata.copy()


def ensure_categories(adata, key):
    """Use observed, nonmissing categories; numeric labels become lexical strings."""
    if key not in adata.obs or adata.obs[key].isna().any():
        die(f"obs column '{key}' must exist and contain no missing labels")
    adata.obs[key] = adata.obs[key].astype(str).astype("category")


def compute_pca(sc, adata, n_comps=50):
    """ARPACK requires fewer components than both cells and selected features."""
    n_features = int(adata.var["highly_variable"].sum()) if "highly_variable" in adata.var else adata.n_vars
    actual = min(n_comps, adata.n_obs - 1, n_features - 1)
    if actual < 1:
        die("PCA requires at least two cells and two selected genes")
    sc.pp.pca(adata, n_comps=actual, svd_solver="arpack", random_state=0)
    return actual


def build_neighbors(sc, adata, *, use_rep="X_pca", n_pcs=40, n_neighbors=15):
    if use_rep not in adata.obsm:
        die(f"embedding '{use_rep}' is missing")
    if adata.n_obs < 3 or n_pcs < 1 or n_neighbors < 2:
        die("neighbors requires at least three cells, n_pcs >= 1 and n_neighbors >= 2")
    actual = min(n_pcs, adata.obsm[use_rep].shape[1])
    sc.pp.neighbors(adata, use_rep=use_rep, n_pcs=actual,
                    n_neighbors=min(n_neighbors, adata.n_obs - 1), random_state=0)


def clear_graph(adata, clear_pca=False):
    """Remove standard derived results after changing expression or cell selection."""
    for key in ("neighbors", "umap", "paga", "rank_genes_groups", "diffmap_evals", "iroot"):
        adata.uns.pop(key, None)
    for key in list(adata.uns):
        if key.startswith("dendrogram_"):
            adata.uns.pop(key)
    for key in ("connectivities", "distances"):
        adata.obsp.pop(key, None)
    for key in ("X_umap", "X_tsne", "X_diffmap", "X_draw_graph_fa"):
        adata.obsm.pop(key, None)
    if clear_pca:
        adata.uns.pop("pca", None)
        adata.varm.pop("PCs", None)
        for key in ("X_pca", "X_pca_harmony"):
            adata.obsm.pop(key, None)


def integrate_harmony(adata, key):
    """Use harmonypy 2's cells x PCs output; Scanpy 1.12.4 transposes it incorrectly."""
    import numpy as np
    import harmonypy
    from importlib.metadata import version

    if int(version("harmonypy").split(".", 1)[0]) != 2:
        die("this Harmony path targets harmonypy 2.x; install harmonypy==2.0.2")
    pcs = np.asarray(adata.obsm["X_pca"], dtype=np.float64)
    result = harmonypy.run_harmony(pcs, adata.obs, key, random_state=0, ncores=1)
    corrected = np.asarray(result.Z_corr)
    if corrected.shape != pcs.shape or not np.isfinite(corrected).all():
        die("Harmony returned invalid cells x PCs coordinates")
    adata.obsm["X_pca_harmony"] = corrected
