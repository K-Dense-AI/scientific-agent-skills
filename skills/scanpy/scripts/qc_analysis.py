#!/usr/bin/env python3
"""
Quality control and filtering for single-cell RNA-seq data.

Calculates QC metrics (genes/counts per cell, mitochondrial / ribosomal /
hemoglobin fractions), writes before/after QC plots, optionally runs Scrublet
doublet detection, and filters cells and genes by the given thresholds.

Run this FIRST on raw counts, before normalization.

Examples:
    python qc_analysis.py raw.h5ad -o filtered.h5ad
    python qc_analysis.py raw.h5ad -o filtered.h5ad --mt-threshold 10 --min-genes 500
    python qc_analysis.py 10x_dir/ -o filtered.h5ad --max-genes 6000 --scrublet
"""

import argparse

from _common import add_io_args, configure_scanpy, info, load_anndata, save_anndata


def annotate_gene_classes(adata):
    """Flag mitochondrial, ribosomal, and hemoglobin genes (human or mouse names)."""
    names = adata.var_names
    adata.var["mt"] = names.str.startswith(("MT-", "mt-", "Mt-"))
    adata.var["ribo"] = names.str.startswith(("RPS", "RPL", "Rps", "Rpl"))
    adata.var["hb"] = names.str.contains(r"^HB[^P]|^Hb[^p]", regex=True)
    return [v for v in ["mt", "ribo", "hb"] if adata.var[v].any()]


def make_qc_plots(sc, adata, prefix):
    qc_keys = ["n_genes_by_counts", "total_counts", "pct_counts_mt"]
    qc_keys = [k for k in qc_keys if k in adata.obs.columns]
    sc.pl.violin(adata, qc_keys, jitter=0.4, multi_panel=True,
                 show=False, save=f"_{prefix}_violin.png")
    if "pct_counts_mt" in adata.obs.columns:
        sc.pl.scatter(adata, x="total_counts", y="pct_counts_mt",
                      show=False, save=f"_{prefix}_mt.png")
    sc.pl.scatter(adata, x="total_counts", y="n_genes_by_counts",
                  show=False, save=f"_{prefix}_counts.png")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    add_io_args(p, default_output="qc_filtered.h5ad")
    p.add_argument("--min-genes", type=int, default=200, help="Min genes per cell (default 200)")
    p.add_argument("--max-genes", type=int, default=None, help="Max genes per cell (upper outliers)")
    p.add_argument("--min-counts", type=int, default=None, help="Min total counts per cell")
    p.add_argument("--max-counts", type=int, default=None, help="Max total counts per cell")
    p.add_argument("--min-cells", type=int, default=3, help="Min cells per gene (default 3)")
    p.add_argument("--mt-threshold", type=float, default=5, help="Max pct mitochondrial counts (default 5)")
    p.add_argument("--scrublet", action="store_true", help="Run Scrublet doublet detection and drop doublets")
    p.add_argument("--no-plots", action="store_true", help="Skip QC plots")
    args = p.parse_args()

    sc = configure_scanpy(figdir=args.figdir)
    adata = load_anndata(args.input)
    adata.var_names_make_unique()
    info(f"Loaded {adata.n_obs} cells x {adata.n_vars} genes")

    qc_vars = annotate_gene_classes(adata)
    sc.pp.calculate_qc_metrics(adata, qc_vars=qc_vars, percent_top=None,
                               log1p=False, inplace=True)
    info(f"Mean genes/cell={adata.obs['n_genes_by_counts'].mean():.0f}  "
         f"mean counts/cell={adata.obs['total_counts'].mean():.0f}  "
         f"mean pct_mt={adata.obs.get('pct_counts_mt', 0).mean():.1f}")

    if not args.no_plots:
        make_qc_plots(sc, adata, "qc_before")

    n0, g0 = adata.n_obs, adata.n_vars
    sc.pp.filter_cells(adata, min_genes=args.min_genes)
    if args.min_counts:
        sc.pp.filter_cells(adata, min_counts=args.min_counts)
    if args.max_genes:
        adata = adata[adata.obs["n_genes_by_counts"] < args.max_genes, :].copy()
    if args.max_counts:
        adata = adata[adata.obs["total_counts"] < args.max_counts, :].copy()
    if "pct_counts_mt" in adata.obs.columns:
        adata = adata[adata.obs["pct_counts_mt"] < args.mt_threshold, :].copy()
    sc.pp.filter_genes(adata, min_cells=args.min_cells)

    if args.scrublet:
        info("Running Scrublet doublet detection...")
        try:
            sc.pp.scrublet(adata)
        except (ImportError, ValueError) as e:
            die(f"Scrublet failed ({e}). Install with: uv pip install scikit-image")
        n_dbl = int(adata.obs["predicted_doublet"].sum())
        adata = adata[~adata.obs["predicted_doublet"], :].copy()
        info(f"Removed {n_dbl} predicted doublets")

    info(f"Cells {n0} -> {adata.n_obs} ({adata.n_obs / n0 * 100:.1f}% kept)  "
         f"Genes {g0} -> {adata.n_vars}")

    if not args.no_plots:
        make_qc_plots(sc, adata, "qc_after")

    save_anndata(adata, args.output)


if __name__ == "__main__":
    main()
