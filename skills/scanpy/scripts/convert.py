#!/usr/bin/env python3
"""
Load any supported single-cell format and write it as .h5ad.

Convenience wrapper to get 10x mtx folders, 10x .h5, CSV/TSV, loom, or mtx
files into AnnData .h5ad once, so later steps all read a single fast format.
For R-native files (.rds / Seurat / SingleCellExperiment), see
references/r_interop.md — those must be converted with R first.

Examples:
    python convert.py filtered_feature_bc_matrix/ -o data.h5ad
    python convert.py raw_counts.csv -o data.h5ad --transpose
    python convert.py matrix.h5 -o data.h5ad
"""

import argparse

from _common import add_io_args, configure_scanpy, info, load_anndata, save_anndata, summarize


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    add_io_args(p, default_output="data.h5ad")
    p.add_argument("--transpose", action="store_true",
                   help="Transpose after loading (use if matrix is genes x cells)")
    p.add_argument("--make-unique", action="store_true",
                   help="Make var (gene) names unique")
    args = p.parse_args()

    configure_scanpy(figdir=args.figdir)
    adata = load_anndata(args.input)
    if args.transpose:
        adata = adata.T
        info(f"Transposed -> {adata.n_obs} cells x {adata.n_vars} genes")
    if args.make_unique:
        adata.var_names_make_unique()
    print(summarize(adata))
    save_anndata(adata, args.output)


if __name__ == "__main__":
    main()
