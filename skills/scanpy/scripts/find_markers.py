#!/usr/bin/env python3
"""
Rank marker genes per group and export tables + plots.

Runs ``sc.tl.rank_genes_groups`` for a grouping (e.g. leiden clusters), writes
a combined CSV of the top markers per group, per-group CSVs, and the standard
marker plots (rank panel, heatmap, dotplot).

NOTE: per-cell tests inflate significance because cells are not independent.
Use this for EXPLORATORY cluster markers. For rigorous DE between conditions,
use pseudobulk.py + pydeseq2.

Examples:
    python find_markers.py clustered.h5ad -o markers.h5ad
    python find_markers.py clustered.h5ad --groupby leiden --method wilcoxon --n-genes 50
    python find_markers.py clustered.h5ad --csv-dir results/markers --top 10
"""

import argparse
import os

from _common import add_io_args, configure_scanpy, die, info, load_anndata, save_anndata, ensure_categories


def safe_name(value):
    from urllib.parse import quote
    return quote(str(value), safe="")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    add_io_args(p, default_output=None)
    p.add_argument("--groupby", default="leiden", help="obs column to group by (default leiden)")
    p.add_argument("--method", default="wilcoxon",
                   choices=["wilcoxon", "t-test", "t-test_overestim_var", "logreg"],
                   help="Test method (default wilcoxon)")
    p.add_argument("--n-genes", type=int, default=25, help="Genes shown in plots (default 25)")
    p.add_argument("--top", type=int, default=25, help="Top markers per group in CSV (default 25)")
    p.add_argument("--use-raw", action=argparse.BooleanOptionalAction, default=None,
                   help="Rank on adata.raw (normalized log values) instead of X")
    p.add_argument("--layer", default=None, help="Explicit log-normalized layer (disables raw)")
    p.add_argument("--groups", nargs="+", default=None, help="Groups to compare (default all)")
    p.add_argument("--reference", default="rest", help="Reference label or rest")
    p.add_argument("--csv-dir", default="results/markers", help="Directory for marker CSVs")
    p.add_argument("--no-plots", action="store_true", help="Skip marker plots")
    args = p.parse_args()

    sc = configure_scanpy(figdir=args.figdir)
    adata = load_anndata(args.input)
    if args.groupby not in adata.obs.columns:
        die(f"groupby column '{args.groupby}' not found in obs: {list(adata.obs.columns)}")

    ensure_categories(adata, args.groupby)
    if args.use_raw is True and adata.raw is None:
        die("--use-raw requested but .raw is missing")
    if args.layer and args.use_raw is True:
        die("choose --layer or --use-raw, not both")
    use_raw = False if args.layer else (adata.raw is not None if args.use_raw is None else args.use_raw)
    sc.tl.rank_genes_groups(adata, args.groupby, method=args.method,
                            use_raw=use_raw, layer=args.layer, groups=args.groups or "all",
                            reference=args.reference, corr_method="benjamini-hochberg", tie_correct=True)

    os.makedirs(args.csv_dir, exist_ok=True)
    # logreg, selected groups and explicit references can return fewer groups.
    groups = list(adata.uns["rank_genes_groups"]["names"].dtype.names)
    combined = []
    for g in groups:
        df = sc.get.rank_genes_groups_df(adata, group=str(g)).head(args.top)
        df.insert(0, "group", g)
        df.to_csv(os.path.join(args.csv_dir, f"markers_{safe_name(args.groupby)}_{safe_name(g)}.csv"), index=False)
        combined.append(df)
    if combined:
        import pandas as pd
        all_path = os.path.join(args.csv_dir, f"markers_{safe_name(args.groupby)}_all.csv")
        pd.concat(combined, ignore_index=True).to_csv(all_path, index=False)
        info(f"Wrote marker tables to {args.csv_dir}/ ({len(groups)} groups)")

    if not args.no_plots:
        sc.pl.rank_genes_groups(adata, n_genes=args.n_genes, sharey=False,
                                show=False, save="_markers.png")
        sc.pl.rank_genes_groups_dotplot(adata, n_genes=5, use_raw=use_raw, layer=args.layer, show=False, save="_markers_dotplot.png")
        sc.pl.rank_genes_groups_heatmap(adata, n_genes=10, use_raw=use_raw, layer=args.layer, show=False, save="_markers_heatmap.png")

    if args.output:
        save_anndata(adata, args.output)


if __name__ == "__main__":
    main()
