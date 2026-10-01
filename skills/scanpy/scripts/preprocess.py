#!/usr/bin/env python3
"""
Normalize, log-transform, select highly variable genes, and optionally scale.

Takes QC-filtered raw counts and produces a normalized, log1p-transformed
object ready for dimensionality reduction. A copy of the raw counts is kept in
``adata.layers['counts']`` and the normalized log values in ``adata.raw`` so
downstream marker/expression plots can use ``use_raw=True``.

Examples:
    python preprocess.py filtered.h5ad -o normalized.h5ad
    python preprocess.py filtered.h5ad -o normalized.h5ad --n-top-genes 3000 --scale
    python preprocess.py filtered.h5ad -o normalized.h5ad --flavor seurat_v3 --batch-key sample
    python preprocess.py filtered.h5ad -o normalized.h5ad --regress-out total_counts pct_counts_mt
"""

import argparse

from _common import add_io_args, configure_scanpy, info, load_anndata, save_anndata, prepare_counts, normalize_hvg


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    add_io_args(p, default_output="normalized.h5ad")
    p.add_argument("--counts-layer", default=None, help="Explicit raw-count layer instead of X")
    p.add_argument("--target-sum", type=float, default=1e4,
                   help="Counts per cell after normalization (default 1e4)")
    p.add_argument("--n-top-genes", type=int, default=2000,
                   help="Number of highly variable genes (default 2000)")
    p.add_argument("--flavor", default="seurat",
                   choices=["seurat", "cell_ranger", "seurat_v3", "seurat_v3_paper"],
                   help="HVG flavor. seurat_v3 expects raw counts (default seurat)")
    p.add_argument("--batch-key", default=None,
                   help="obs column for batch-aware HVG selection")
    p.add_argument("--subset-hvg", action="store_true",
                   help="Subset the matrix to HVGs (smaller, but drops other genes from X)")
    p.add_argument("--regress-out", nargs="+", default=None,
                   help="obs columns to regress out (e.g. total_counts pct_counts_mt)")
    p.add_argument("--scale", action="store_true",
                   help="Scale to unit variance and zero mean (max_value=10)")
    p.add_argument("--no-plots", action="store_true", help="Skip HVG plot")
    args = p.parse_args()

    sc = configure_scanpy(figdir=args.figdir)
    adata = load_anndata(args.input)
    info(f"Loaded {adata.n_obs} cells x {adata.n_vars} genes")

    prepare_counts(adata, args.counts_layer)
    normalize_hvg(sc, adata, target_sum=args.target_sum, n_top_genes=args.n_top_genes,
                  flavor=args.flavor, batch_key=args.batch_key)

    n_hvg = int(adata.var["highly_variable"].sum())
    info(f"Selected {n_hvg} highly variable genes")

    # Stash the full normalized log matrix so plots can use_raw=True.
    # normalize_hvg saved an independent full log-normalized snapshot.

    if not args.no_plots:
        sc.pl.highly_variable_genes(adata, show=False, save="_hvg.png")

    if args.subset_hvg:
        info("HVG subsetting also subsets counts; retain the full-gene input for pseudobulk")
        adata = adata[:, adata.var["highly_variable"]].copy()
        info(f"Subset to {adata.n_vars} HVGs")

    if args.regress_out:
        info(f"Regressing out: {', '.join(args.regress_out)}")
        sc.pp.regress_out(adata, args.regress_out)

    if args.scale:
        info("Scaling (max_value=10)")
        sc.pp.scale(adata, max_value=10)

    save_anndata(adata, args.output)


if __name__ == "__main__":
    main()
