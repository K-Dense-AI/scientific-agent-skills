#!/usr/bin/env python3
"""
Aggregate single cells into pseudobulk profiles for rigorous DE.

Sums raw counts within each combination of grouping columns (e.g. sample x
cell_type) using ``sc.get.aggregate`` and exports a genes x pseudobulk-sample
count matrix plus a sample-metadata table. Feed these into pydeseq2 / edgeR /
limma for condition comparisons — this is the statistically correct route,
unlike per-cell rank_genes_groups.

Examples:
    python pseudobulk.py annotated.h5ad --by sample cell_type --out-prefix results/pb
    python pseudobulk.py annotated.h5ad --by sample cell_type --layer counts --out-prefix pb
"""

import argparse
import os

from _common import configure_scanpy, die, info, load_anndata


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="Input .h5ad")
    p.add_argument("--by", nargs="+", required=True,
                   help="obs columns to aggregate by (e.g. sample cell_type)")
    p.add_argument("--layer", default="counts",
                   help="Layer with raw counts to sum (default 'counts'; falls back to X)")
    p.add_argument("--func", default="sum", choices=["sum", "mean", "count_nonzero"],
                   help="Aggregation function (default sum)")
    p.add_argument("--out-prefix", default="pseudobulk",
                   help="Output prefix; writes <prefix>_counts.csv and <prefix>_samples.csv")
    args = p.parse_args()

    sc = configure_scanpy()
    adata = load_anndata(args.input)
    for col in args.by:
        if col not in adata.obs.columns:
            die(f"grouping column '{col}' not in obs: {list(adata.obs.columns)}")

    layer = args.layer if args.layer in adata.layers else None
    if args.layer and layer is None:
        info(f"Layer '{args.layer}' not found; aggregating adata.X instead")

    pb = sc.get.aggregate(adata, by=args.by, func=args.func, layer=layer)
    # aggregate stores the result in a layer named after func.
    mat = pb.layers[args.func]

    import pandas as pd
    sample_ids = ["_".join(str(pb.obs.iloc[i][c]) for c in args.by) for i in range(pb.n_obs)]
    counts_df = pd.DataFrame(
        mat.T.toarray() if hasattr(mat, "toarray") else mat.T,
        index=pb.var_names, columns=sample_ids,
    )

    parent = os.path.dirname(os.path.abspath(args.out_prefix))
    if parent:
        os.makedirs(parent, exist_ok=True)
    counts_path = f"{args.out_prefix}_counts.csv"
    samples_path = f"{args.out_prefix}_samples.csv"
    counts_df.to_csv(counts_path)
    meta = pb.obs[args.by].copy()
    meta.index = sample_ids
    meta.to_csv(samples_path)

    info(f"Wrote {counts_df.shape[0]} genes x {counts_df.shape[1]} pseudobulk samples")
    info(f"  counts:  {counts_path}")
    info(f"  samples: {samples_path}")
    info("Next: load these into pydeseq2 for differential expression.")


if __name__ == "__main__":
    main()
