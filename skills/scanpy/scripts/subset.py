#!/usr/bin/env python3
"""
Subset an AnnData object by cell metadata or genes.

Filter cells by obs-column values (keep or drop), or restrict to a gene list.
Useful for isolating a cell type / condition for focused re-analysis.

Examples:
    python subset.py annotated.h5ad -o tcells.h5ad --obs cell_type --keep "CD4 T cells" "CD8 T cells"
    python subset.py annotated.h5ad -o no_doublets.h5ad --obs predicted_doublet --drop True
    python subset.py data.h5ad -o panel.h5ad --genes CD3D CD14 MS4A1 NKG7
"""

import argparse

from _common import add_io_args, configure_scanpy, die, info, load_anndata, save_anndata, clear_graph


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    add_io_args(p, default_output="subset.h5ad")
    p.add_argument("--obs", default=None, help="obs column to filter on")
    p.add_argument("--keep", nargs="+", default=None, help="Values of --obs to keep")
    p.add_argument("--drop", nargs="+", default=None, help="Values of --obs to drop")
    p.add_argument("--genes", nargs="+", default=None, help="Restrict to these genes")
    p.add_argument("--recompute-hvg", action="store_true",
                   help="After subsetting, drop stale embeddings so the next steps recompute cleanly")
    args = p.parse_args()

    configure_scanpy(figdir=args.figdir)
    adata = load_anndata(args.input)
    n0 = adata.n_obs

    if args.obs:
        if args.obs not in adata.obs.columns:
            die(f"obs column '{args.obs}' not found: {list(adata.obs.columns)}")
        vals = adata.obs[args.obs].astype(str)
        if args.keep:
            adata = adata[vals.isin([str(v) for v in args.keep]), :].copy()
        elif args.drop:
            adata = adata[~vals.isin([str(v) for v in args.drop]), :].copy()
        else:
            die("provide --keep or --drop with --obs")
        info(f"Cells {n0} -> {adata.n_obs}")

    if args.genes:
        present = [g for g in args.genes if g in adata.var_names]
        if not present:
            die("none of the requested genes are present")
        adata = adata[:, present].copy()
        info(f"Restricted to {adata.n_vars} genes")

    if args.recompute_hvg:
        clear_graph(adata, clear_pca=True)
        for key in list(adata.var):
            if key.startswith("highly_variable"):
                del adata.var[key]
        info("Cleared standard HVG/embedding/graph results. Recompute HVGs on the existing log-normalized X; do not normalize it again.")

    save_anndata(adata, args.output)


if __name__ == "__main__":
    main()
