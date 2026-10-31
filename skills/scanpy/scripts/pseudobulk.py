#!/usr/bin/env python3
"""Sum raw counts by biological sample and cell type for downstream DE.

Exports genes x pseudobulk samples and aligned metadata. Transpose counts for
PyDESeq2's samples x genes API. Analyze one cell type at a time with independent
biological replicates; cells and sample x cell-type rows are not new donors.

Example:
    python pseudobulk.py annotated.h5ad --by sample cell_type --metadata condition donor --out-prefix results/pb
"""

import argparse
import os

from _common import configure_scanpy, die, info, load_anndata, validate_counts


def aggregate_counts(adata, by, layer="counts", metadata=(), min_cells=1):
    """Collision-free groups, exact layer selection, constant group metadata."""
    import numpy as np
    import pandas as pd
    import scanpy as sc

    if min_cells < 1 or not by or len(set(by)) != len(by):
        die("--by must contain unique grouping columns and --min-cells must be positive")
    for key in list(by) + list(metadata):
        if key not in adata.obs or adata.obs[key].isna().any():
            die(f"obs column '{key}' must exist and contain no missing values")
    if layer is not None and layer not in adata.layers:
        die(f"raw-count layer '{layer}' is missing; no fallback to X is permitted")
    matrix = adata.X if layer is None else adata.layers[layer]
    validate_counts(matrix, "pseudobulk counts", require_nonzero_cells=False)
    if not adata.var_names.is_unique:
        die("gene identifiers must be unique before aggregation")
    # Scanpy joins multiple keys with underscores; ambiguous labels can collide.
    # Aggregate by opaque IDs and retain the original grouping columns separately.
    codes, _ = pd.factorize(pd.MultiIndex.from_frame(adata.obs[list(by)]), sort=False)
    ids = pd.Index([f"pb{i:06d}" for i in range(int(codes.max()) + 1)], name="sample_id")
    cols = list(dict.fromkeys(list(by) + list(metadata)))
    rows = []
    for code, sample_id in enumerate(ids):
        group = adata.obs.iloc[np.flatnonzero(codes == code)]
        if any(group[key].nunique(dropna=False) != 1 for key in metadata):
            die(f"metadata is not constant within pseudobulk group {sample_id}")
        row = group.iloc[0][cols].to_dict()
        row["n_cells"] = len(group)
        rows.append(row)
    meta = pd.DataFrame(rows, index=ids)
    # No copy of expression and no mutation of the source object.
    import anndata as ad
    work = ad.AnnData(matrix, obs=pd.DataFrame({"group": pd.Categorical(ids[codes])},
                                              index=adata.obs_names), var=adata.var.copy())
    pb = sc.get.aggregate(work, by="group", func="sum")
    mat = pb.layers["sum"]  # aggregate returns layers, not an expression matrix in X
    arr = mat.toarray() if hasattr(mat, "toarray") else np.asarray(mat)
    ordered = pb.obs["group"].astype(str).to_numpy()
    meta = meta.loc[ordered]
    keep = meta["n_cells"].to_numpy() >= min_cells
    if not keep.any():
        die("no pseudobulk groups meet --min-cells")
    counts = pd.DataFrame(arr[keep].T, index=adata.var_names,
                          columns=meta.index[keep])
    counts.index.name = "gene_id"
    return counts, meta.iloc[np.flatnonzero(keep)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", help="Input .h5ad with full-gene raw counts")
    p.add_argument("--by", nargs="+", required=True, help="Sample and cell-type obs columns")
    source = p.add_mutually_exclusive_group()
    source.add_argument("--layer", default="counts", help="Raw counts layer (default counts)")
    source.add_argument("--use-x", action="store_true", help="Explicitly declare X as raw counts")
    p.add_argument("--func", choices=["sum"], default="sum", help="Count-based DE requires sums")
    p.add_argument("--metadata", nargs="+", default=[], help="Group-constant donor/condition/design columns")
    p.add_argument("--min-cells", type=int, default=1, help="Minimum contributing cells per profile")
    p.add_argument("--out-prefix", default="pseudobulk")
    args = p.parse_args()
    configure_scanpy()
    adata = load_anndata(args.input)
    counts, meta = aggregate_counts(adata, args.by, None if args.use_x else args.layer,
                                    args.metadata, args.min_cells)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_prefix)), exist_ok=True)
    counts.to_csv(f"{args.out_prefix}_counts.csv")
    meta.to_csv(f"{args.out_prefix}_samples.csv")
    info(f"Wrote {counts.shape[0]} genes x {counts.shape[1]} pseudobulk profiles")
    info("Transpose counts for PyDESeq2; preserve IDs as strings, align metadata, and fit each cell type with biological replicates.")


if __name__ == "__main__":
    main()
