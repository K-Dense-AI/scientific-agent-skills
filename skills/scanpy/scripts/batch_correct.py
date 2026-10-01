#!/usr/bin/env python3
"""
Batch correction / integration across samples.

Supports three methods:
  * harmony  : corrects the PCA embedding -> writes obsm['X_pca_harmony'].
               Embedding integration. Needs harmonypy (uv pip install harmonypy==2.0.2).
               Follow with: reduce_dimensions.py --use-rep X_pca_harmony
  * bbknn     : batch-balanced kNN graph (replaces sc.pp.neighbors). Then cluster directly.
               Needs bbknn (uv pip install bbknn).
  * combat    : corrects the expression matrix in place (sc.pp.combat). Built into scanpy.

Run on a normalized object that already has PCA (harmony/bbknn) computed.

Examples:
    python batch_correct.py reduced.h5ad -o integrated.h5ad --method harmony --batch-key sample
    python batch_correct.py reduced.h5ad -o integrated.h5ad --method bbknn --batch-key sample
    python batch_correct.py normalized.h5ad -o integrated.h5ad --method combat --batch-key batch
"""

import argparse

from _common import add_io_args, configure_scanpy, die, info, load_anndata, save_anndata, compute_pca, clear_graph, ensure_categories, integrate_harmony


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    add_io_args(p, default_output="integrated.h5ad")
    p.add_argument("--method", default="harmony", choices=["harmony", "bbknn", "combat"])
    p.add_argument("--batch-key", required=True, help="obs column identifying batches")
    args = p.parse_args()

    sc = configure_scanpy(figdir=args.figdir)
    adata = load_anndata(args.input)
    if args.batch_key not in adata.obs.columns:
        die(f"batch key '{args.batch_key}' not in obs: {list(adata.obs.columns)}")

    ensure_categories(adata, args.batch_key)
    if adata.obs[args.batch_key].nunique() < 2:
        die("batch correction requires at least two batches")

    if args.method == "harmony":
        if "X_pca" not in adata.obsm:
            compute_pca(sc, adata)
        try:
            integrate_harmony(adata, args.batch_key)
        except ImportError:
            die("harmonypy not installed. Install with: uv pip install harmonypy==2.0.2")
        clear_graph(adata)
        info("Wrote obsm['X_pca_harmony']. Next: "
             "reduce_dimensions.py --use-rep X_pca_harmony")
    elif args.method == "bbknn":
        if "X_pca" not in adata.obsm:
            compute_pca(sc, adata)
        try:
            sc.external.pp.bbknn(adata, batch_key=args.batch_key,
                                 n_pcs=adata.obsm["X_pca"].shape[1],
                                 approx=False, use_faiss=False)
        except ImportError:
            die("bbknn not installed. Install with: uv pip install bbknn")
        sc.tl.umap(adata)
        info("Built batch-balanced graph + UMAP. Next: cluster.py")
    elif args.method == "combat":
        sc.pp.combat(adata, key=args.batch_key)
        clear_graph(adata, clear_pca=True)
        info("Corrected expression matrix with ComBat. Re-run reduce_dimensions.py.")

    save_anndata(adata, args.output)


if __name__ == "__main__":
    main()
