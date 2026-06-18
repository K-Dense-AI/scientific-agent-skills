#!/usr/bin/env python3
"""
PCA, neighborhood graph, and UMAP / t-SNE embeddings.

Takes a normalized object (optionally HVG-subset / scaled) and computes PCA,
the kNN graph, and a UMAP (and optionally t-SNE) embedding. Writes a PCA
variance-ratio elbow plot to help choose ``--n-pcs``.

Examples:
    python reduce_dimensions.py normalized.h5ad -o reduced.h5ad
    python reduce_dimensions.py normalized.h5ad -o reduced.h5ad --n-pcs 50 --n-neighbors 15
    python reduce_dimensions.py normalized.h5ad -o reduced.h5ad --tsne --use-rep X_pca_harmony
"""

import argparse

from _common import add_io_args, configure_scanpy, info, load_anndata, save_anndata


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    add_io_args(p, default_output="reduced.h5ad")
    p.add_argument("--n-comps", type=int, default=50, help="PCs to compute (default 50)")
    p.add_argument("--n-pcs", type=int, default=40, help="PCs used for the kNN graph (default 40)")
    p.add_argument("--n-neighbors", type=int, default=15, help="Neighbors for the graph (default 15)")
    p.add_argument("--use-rep", default=None,
                   help="obsm key to build the graph from instead of PCA "
                        "(e.g. X_pca_harmony from batch_correct.py)")
    p.add_argument("--tsne", action="store_true", help="Also compute t-SNE")
    p.add_argument("--color", nargs="+", default=None,
                   help="obs/var keys to color the UMAP by (e.g. sample n_genes_by_counts)")
    p.add_argument("--no-plots", action="store_true", help="Skip plots")
    args = p.parse_args()

    sc = configure_scanpy(figdir=args.figdir)
    adata = load_anndata(args.input)
    info(f"Loaded {adata.n_obs} cells x {adata.n_vars} genes")

    n_comps = min(args.n_comps, adata.n_vars - 1, adata.n_obs - 1)
    sc.tl.pca(adata, n_comps=n_comps, svd_solver="arpack")
    if not args.no_plots:
        sc.pl.pca_variance_ratio(adata, n_pcs=n_comps, log=True,
                                 show=False, save="_variance.png")

    sc.pp.neighbors(adata, n_neighbors=args.n_neighbors, n_pcs=args.n_pcs,
                    use_rep=args.use_rep)
    info("Computing UMAP...")
    sc.tl.umap(adata)

    if args.tsne:
        info("Computing t-SNE...")
        sc.tl.tsne(adata, use_rep=args.use_rep or "X_pca")

    if not args.no_plots and args.color:
        color = [c for c in args.color if c in adata.obs.columns or c in adata.var_names]
        if color:
            sc.pl.umap(adata, color=color, show=False, save="_colored.png")

    save_anndata(adata, args.output)


if __name__ == "__main__":
    main()
