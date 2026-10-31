#!/usr/bin/env python3
"""
Inspect an AnnData / single-cell file and print a structured summary.

Reports shape, obs/var columns (with dtypes and category counts), layers,
obsm/varm/uns keys, X dtype and value range, and whether the data looks like
raw counts or normalized values. Use this before analysis to understand an
unfamiliar dataset and decide which pipeline steps still need to run.

Examples:
    python inspect_data.py data.h5ad
    python inspect_data.py 10x_dir/
"""

import argparse

import numpy as np

from _common import configure_scanpy, info, load_anndata


def _is_integer_matrix(X, n=10000):
    from scipy import sparse
    if X is None:
        return False
    arr = X.data[:n] if sparse.issparse(X) else np.asarray(X[:50]).ravel()[:n]
    return bool(arr.size and np.isfinite(arr).all() and (arr >= 0).all()
                and np.equal(arr, np.floor(arr)).all())


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="Input file (.h5ad, .h5, .csv, .loom, or 10x mtx dir)")
    p.add_argument("--max-cols", type=int, default=40, help="Max obs/var columns to list")
    args = p.parse_args()

    configure_scanpy()
    adata = load_anndata(args.input)

    print("=" * 70)
    print(f"AnnData: {adata.n_obs} cells x {adata.n_vars} genes")
    print("=" * 70)

    X = adata.X
    if X is None:
        print("\nX is absent; inspect named layers and their provenance")
    else:
        looks_int = _is_integer_matrix(X)
        xmax = float(X.max()) if min(X.shape) else float("nan")
        print(f"\nX dtype={X.dtype} max={xmax:.2f}; sampled values are "
              f"{'nonnegative integers' if looks_int else 'not count-like'}. "
              "This does not establish raw-count provenance.")

    print(f"\nobs columns ({len(adata.obs.columns)}):")
    for c in adata.obs.columns[:args.max_cols]:
        col = adata.obs[c]
        from pandas.api.types import is_numeric_dtype
        if not is_numeric_dtype(col.dtype):
            nuniq = col.nunique()
            extra = f"  {nuniq} categories" + (f": {list(col.unique()[:8])}" if nuniq <= 8 else "")
        else:
            extra = f"  range=[{col.min():.2f}, {col.max():.2f}]"
        print(f"  - {c} ({col.dtype}){extra}")

    print(f"\nvar columns ({len(adata.var.columns)}): {list(adata.var.columns[:args.max_cols])}")
    print(f"\nlayers: {list(adata.layers.keys())}")
    print(f"obsm: {list(adata.obsm.keys())}")
    print(f"varm: {list(adata.varm.keys())}")
    print(f"uns:  {list(adata.uns.keys())}")
    print(f"raw:  {'present' if adata.raw is not None else 'none'}")

    done = []
    if any(k in adata.obsm for k in ("X_pca",)):
        done.append("PCA")
    if "neighbors" in adata.uns:
        done.append("neighbors")
    if "X_umap" in adata.obsm:
        done.append("UMAP")
    if any(k in adata.obs.columns for k in ("leiden", "louvain")):
        done.append("clustering")
    print("\nPipeline steps already present: " + (", ".join(done) if done else "none"))


if __name__ == "__main__":
    main()
