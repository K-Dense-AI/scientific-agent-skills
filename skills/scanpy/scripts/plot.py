#!/usr/bin/env python3
"""
Generate common single-cell plots from a processed AnnData object.

A flexible plotting front-end so the agent doesn't hand-write matplotlib /
scanpy plotting calls. Pick a plot type and the keys/genes to show.

Plot types:
  umap / tsne / pca   : embedding colored by --color obs columns and/or --genes
  violin               : --genes (or QC metrics) split by --groupby
  dotplot / matrixplot / heatmap / tracksplot / stacked_violin : --genes by --groupby

Examples:
    python plot.py annotated.h5ad --kind umap --color leiden cell_type
    python plot.py annotated.h5ad --kind umap --genes CD3D MS4A1 NKG7 --use-raw
    python plot.py annotated.h5ad --kind dotplot --genes CD3D CD14 MS4A1 --groupby cell_type
    python plot.py annotated.h5ad --kind violin --genes CD3D --groupby leiden
"""

import argparse

from _common import configure_scanpy, die, info, load_anndata


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="Input .h5ad")
    p.add_argument("--kind", required=True,
                   choices=["umap", "tsne", "pca", "violin", "dotplot",
                            "matrixplot", "heatmap", "tracksplot", "stacked_violin"])
    p.add_argument("--color", nargs="+", default=None, help="obs columns to color by")
    p.add_argument("--genes", nargs="+", default=None, help="genes to display")
    p.add_argument("--groupby", default=None, help="obs column to group by (violin/dotplot/...)")
    p.add_argument("--use-raw", action="store_true", help="Use adata.raw (normalized log values)")
    p.add_argument("--figdir", default="figures", help="Figure output directory")
    p.add_argument("--save", default=None, help="Filename suffix (default derived from --kind)")
    args = p.parse_args()

    sc = configure_scanpy(figdir=args.figdir)
    adata = load_anndata(args.input)
    # scanpy prepends the plot-function name, so ".png" yields e.g. "umap.png".
    save = args.save or ".png"
    use_raw = args.use_raw and adata.raw is not None

    var_names = adata.raw.var_names if use_raw else adata.var_names
    genes = [g for g in (args.genes or []) if g in var_names]
    if args.genes and len(genes) < len(args.genes):
        missing = set(args.genes) - set(genes)
        info(f"Genes not found (skipped): {sorted(missing)}")

    if args.kind in ("umap", "tsne", "pca"):
        color = (args.color or []) + genes
        if not color:
            die("provide --color and/or --genes for embedding plots")
        fn = {"umap": sc.pl.umap, "tsne": sc.pl.tsne, "pca": sc.pl.pca}[args.kind]
        fn(adata, color=color, use_raw=use_raw, show=False, save=save)
    elif args.kind == "violin":
        keys = genes or [c for c in (args.color or []) if c in adata.obs.columns]
        if not keys:
            die("provide --genes (or obs keys via --color) for violin")
        sc.pl.violin(adata, keys, groupby=args.groupby, use_raw=use_raw,
                     show=False, save=save)
    else:
        if not genes or not args.groupby:
            die(f"{args.kind} requires --genes and --groupby")
        fn = {
            "dotplot": sc.pl.dotplot, "matrixplot": sc.pl.matrixplot,
            "heatmap": sc.pl.heatmap, "tracksplot": sc.pl.tracksplot,
            "stacked_violin": sc.pl.stacked_violin,
        }[args.kind]
        fn(adata, genes, groupby=args.groupby, use_raw=use_raw, show=False, save=save)

    info(f"Saved {args.figdir}/{args.kind}{save}")


if __name__ == "__main__":
    main()
