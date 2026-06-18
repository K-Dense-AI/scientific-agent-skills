#!/usr/bin/env python3
"""
Batch correction / integration across samples.

Supports three methods:
  * harmony  : corrects the PCA embedding -> writes obsm['X_pca_harmony'].
               Fast, recommended default. Needs harmonypy (uv pip install harmonypy).
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

from _common import add_io_args, configure_scanpy, die, info, load_anndata, save_anndata


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

    if args.method == "harmony":
        if "X_pca" not in adata.obsm:
            sc.tl.pca(adata, svd_solver="arpack")
        try:
            sc.external.pp.harmony_integrate(adata, args.batch_key)
        except ImportError:
            die("harmonypy not installed. Install with: uv pip install harmonypy")
        info("Wrote obsm['X_pca_harmony']. Next: "
             "reduce_dimensions.py --use-rep X_pca_harmony")
    elif args.method == "bbknn":
        if "X_pca" not in adata.obsm:
            sc.tl.pca(adata, svd_solver="arpack")
        try:
            sc.external.pp.bbknn(adata, batch_key=args.batch_key)
        except ImportError:
            die("bbknn not installed. Install with: uv pip install bbknn")
        sc.tl.umap(adata)
        info("Built batch-balanced graph + UMAP. Next: cluster.py")
    elif args.method == "combat":
        sc.pp.combat(adata, key=args.batch_key)
        info("Corrected expression matrix with ComBat. Re-run reduce_dimensions.py.")

    save_anndata(adata, args.output)


if __name__ == "__main__":
    main()
