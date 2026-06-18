#!/usr/bin/env python3
"""
Annotate clusters with cell-type labels from a mapping file.

Maps a cluster column (e.g. leiden) to cell-type names using a JSON or CSV
mapping, writes the labels into a new obs column, and saves a UMAP and dotplot.

The mapping file is one of:
  * JSON  : {"0": "CD4 T cells", "1": "B cells", ...}
  * CSV    : two columns ``cluster,cell_type``

Optionally provide a marker-gene JSON to draw a reference dotplot that helps
decide the mapping:
  {"T cells": ["CD3D","CD3E"], "B cells": ["MS4A1","CD79A"]}

Examples:
    python annotate.py clustered.h5ad -o annotated.h5ad --mapping celltypes.json
    python annotate.py clustered.h5ad -o annotated.h5ad --mapping map.csv --cluster-key leiden
    python annotate.py clustered.h5ad --markers markers.json --cluster-key leiden   # dotplot only
"""

import argparse
import json
import os

from _common import add_io_args, configure_scanpy, die, info, load_anndata, save_anndata


def load_mapping(path):
    if path.lower().endswith(".json"):
        with open(path) as fh:
            return {str(k): v for k, v in json.load(fh).items()}
    import pandas as pd
    df = pd.read_csv(path)
    if df.shape[1] < 2:
        die("CSV mapping needs at least two columns: cluster,cell_type")
    return {str(k): v for k, v in zip(df.iloc[:, 0], df.iloc[:, 1])}


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    add_io_args(p, default_output="annotated.h5ad")
    p.add_argument("--cluster-key", default="leiden", help="obs column with clusters (default leiden)")
    p.add_argument("--mapping", default=None, help="JSON or CSV cluster->cell_type mapping")
    p.add_argument("--label-key", default="cell_type", help="New obs column name (default cell_type)")
    p.add_argument("--markers", default=None,
                   help="JSON of {cell_type: [genes]} to draw a reference dotplot")
    p.add_argument("--no-plots", action="store_true", help="Skip plots")
    args = p.parse_args()

    sc = configure_scanpy(figdir=args.figdir)
    adata = load_anndata(args.input)
    if args.cluster_key not in adata.obs.columns:
        die(f"cluster key '{args.cluster_key}' not in obs: {list(adata.obs.columns)}")

    if args.markers:
        with open(args.markers) as fh:
            marker_dict = json.load(fh)
        present = {ct: [g for g in genes if g in (adata.raw.var_names if adata.raw is not None else adata.var_names)]
                   for ct, genes in marker_dict.items()}
        present = {ct: g for ct, g in present.items() if g}
        if present and not args.no_plots:
            sc.pl.dotplot(adata, present, groupby=args.cluster_key,
                          use_raw=adata.raw is not None, show=False, save="_marker_reference.png")
            info("Wrote marker reference dotplot")

    if args.mapping:
        mapping = load_mapping(args.mapping)
        adata.obs[args.label_key] = (
            adata.obs[args.cluster_key].astype(str).map(mapping).fillna("Unknown").astype("category")
        )
        info(f"Annotated '{args.label_key}': "
             + ", ".join(f"{k}={v}" for k, v in adata.obs[args.label_key].value_counts().items()))
        if not args.no_plots:
            sc.pl.umap(adata, color=args.label_key, legend_loc="on data",
                       show=False, save="_celltypes.png")
        save_anndata(adata, args.output)
    elif not args.markers:
        die("provide --mapping (to annotate) and/or --markers (for a reference dotplot)")


if __name__ == "__main__":
    main()
