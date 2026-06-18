#!/usr/bin/env python3
"""
End-to-end standard scRNA-seq pipeline in one command.

Runs the full exploratory workflow on raw counts:
    load -> QC + filter -> (optional doublets) -> normalize + log1p -> HVG
    -> (optional scale/regress) -> PCA -> (optional batch correction)
    -> neighbors -> UMAP -> Leiden -> marker genes -> save.

Produces a processed .h5ad, marker CSVs, and figures. Tune the common knobs via
flags, or pass a JSON config with ``--config`` (keys mirror the flag names with
underscores). This is the fastest path from counts to a clustered, annotated-
ready object; use the individual step scripts when you need to iterate on one stage.

Examples:
    python run_pipeline.py raw.h5ad -o processed.h5ad
    python run_pipeline.py raw.h5ad -o processed.h5ad --resolution 0.8 --n-top-genes 3000
    python run_pipeline.py raw.h5ad -o processed.h5ad --batch-key sample --batch-method harmony
    python run_pipeline.py raw.h5ad -o processed.h5ad --config params.json
"""

import argparse
import json
import os

from _common import configure_scanpy, info, load_anndata, save_anndata


def build_parser():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="Input raw-counts file (.h5ad, .h5, .csv, 10x dir, ...)")
    p.add_argument("-o", "--output", default="processed.h5ad", help="Output .h5ad")
    p.add_argument("--figdir", default="figures", help="Figure directory")
    p.add_argument("--marker-dir", default="results/markers", help="Marker CSV directory")
    p.add_argument("--config", default=None, help="JSON file overriding any of the options below")
    # QC
    p.add_argument("--min-genes", type=int, default=200)
    p.add_argument("--max-genes", type=int, default=None)
    p.add_argument("--min-cells", type=int, default=3)
    p.add_argument("--mt-threshold", type=float, default=5)
    p.add_argument("--scrublet", action="store_true")
    # normalization / HVG
    p.add_argument("--target-sum", type=float, default=1e4)
    p.add_argument("--n-top-genes", type=int, default=2000)
    p.add_argument("--hvg-flavor", default="seurat", choices=["seurat", "cell_ranger", "seurat_v3"])
    p.add_argument("--scale", action="store_true")
    p.add_argument("--regress-out", nargs="+", default=None)
    # dim reduction / clustering
    p.add_argument("--n-pcs", type=int, default=40)
    p.add_argument("--n-neighbors", type=int, default=15)
    p.add_argument("--resolution", type=float, default=0.5)
    # batch correction
    p.add_argument("--batch-key", default=None)
    p.add_argument("--batch-method", default="harmony", choices=["harmony", "combat"])
    # markers
    p.add_argument("--marker-method", default="wilcoxon")
    p.add_argument("--skip-markers", action="store_true")
    return p


def apply_config(args):
    if args.config:
        with open(args.config) as fh:
            cfg = json.load(fh)
        for k, v in cfg.items():
            setattr(args, k.replace("-", "_"), v)
    return args


def main():
    args = apply_config(build_parser().parse_args())
    sc = configure_scanpy(figdir=args.figdir)

    info("[1/8] Loading data")
    adata = load_anndata(args.input)
    adata.var_names_make_unique()
    info(f"      {adata.n_obs} cells x {adata.n_vars} genes")

    info("[2/8] QC + filtering")
    adata.var["mt"] = adata.var_names.str.startswith(("MT-", "mt-", "Mt-"))
    qc_vars = ["mt"] if adata.var["mt"].any() else []
    sc.pp.calculate_qc_metrics(adata, qc_vars=qc_vars, percent_top=None, log1p=False, inplace=True)
    sc.pl.violin(adata, [k for k in ["n_genes_by_counts", "total_counts", "pct_counts_mt"]
                         if k in adata.obs.columns],
                 jitter=0.4, multi_panel=True, show=False, save="_qc.png")
    n0 = adata.n_obs
    sc.pp.filter_cells(adata, min_genes=args.min_genes)
    sc.pp.filter_genes(adata, min_cells=args.min_cells)
    if args.max_genes:
        adata = adata[adata.obs["n_genes_by_counts"] < args.max_genes, :].copy()
    if qc_vars and "pct_counts_mt" in adata.obs.columns:
        adata = adata[adata.obs["pct_counts_mt"] < args.mt_threshold, :].copy()
    if args.scrublet:
        try:
            sc.pp.scrublet(adata)
            adata = adata[~adata.obs["predicted_doublet"], :].copy()
        except (ImportError, ValueError) as e:
            info(f"      Scrublet skipped ({e}); install scikit-image to enable")
    info(f"      {n0} -> {adata.n_obs} cells, {adata.n_vars} genes")

    info("[3/8] Normalize + log1p + HVG")
    adata.layers["counts"] = adata.X.copy()
    if args.hvg_flavor == "seurat_v3":
        sc.pp.highly_variable_genes(adata, n_top_genes=args.n_top_genes,
                                    flavor="seurat_v3", batch_key=args.batch_key)
        sc.pp.normalize_total(adata, target_sum=args.target_sum)
        sc.pp.log1p(adata)
    else:
        sc.pp.normalize_total(adata, target_sum=args.target_sum)
        sc.pp.log1p(adata)
        sc.pp.highly_variable_genes(adata, n_top_genes=args.n_top_genes,
                                    flavor=args.hvg_flavor, batch_key=args.batch_key)
    adata.raw = adata
    info(f"      {int(adata.var['highly_variable'].sum())} HVGs")

    info("[4/8] Scale / regress (optional)")
    work = adata[:, adata.var["highly_variable"]].copy()
    if args.regress_out:
        sc.pp.regress_out(work, args.regress_out)
    if args.scale:
        sc.pp.scale(work, max_value=10)

    info("[5/8] PCA" + (f" + {args.batch_method} batch correction" if args.batch_key else ""))
    sc.tl.pca(work, svd_solver="arpack")
    sc.pl.pca_variance_ratio(work, log=True, show=False, save="_variance.png")
    use_rep = "X_pca"
    if args.batch_key:
        if args.batch_method == "harmony":
            try:
                sc.external.pp.harmony_integrate(work, args.batch_key)
                use_rep = "X_pca_harmony"
            except ImportError:
                info("      harmonypy not installed; skipping (uv pip install harmonypy)")
        else:
            sc.pp.combat(work, key=args.batch_key)
            sc.tl.pca(work, svd_solver="arpack")

    info("[6/8] Neighbors + UMAP")
    sc.pp.neighbors(work, n_neighbors=args.n_neighbors, n_pcs=args.n_pcs, use_rep=use_rep)
    sc.tl.umap(work)

    info("[7/8] Leiden clustering")
    sc.tl.leiden(work, resolution=args.resolution, flavor="igraph",
                 n_iterations=2, directed=False)
    n_clusters = work.obs["leiden"].nunique()
    color = ["leiden"] + ([args.batch_key] if args.batch_key else [])
    sc.pl.umap(work, color=color, legend_loc="on data", show=False, save="_leiden.png")
    info(f"      {n_clusters} clusters at resolution {args.resolution}")

    # Carry embeddings/clusters back onto the full-gene object so markers use all genes.
    adata.obs["leiden"] = work.obs["leiden"].values
    adata.obsm["X_pca"] = work.obsm["X_pca"]
    adata.obsm["X_umap"] = work.obsm["X_umap"]
    if use_rep in work.obsm:
        adata.obsm[use_rep] = work.obsm[use_rep]
    adata.uns["neighbors"] = work.uns["neighbors"]
    adata.obsp = work.obsp

    if not args.skip_markers:
        info("[8/8] Marker genes")
        sc.tl.rank_genes_groups(adata, "leiden", method=args.marker_method, use_raw=True)
        sc.pl.rank_genes_groups_dotplot(adata, n_genes=5, show=False, save="_markers_dotplot.png")
        os.makedirs(args.marker_dir, exist_ok=True)
        import pandas as pd
        frames = []
        for g in adata.obs["leiden"].cat.categories:
            df = sc.get.rank_genes_groups_df(adata, group=g).head(25)
            df.insert(0, "cluster", g)
            frames.append(df)
        pd.concat(frames, ignore_index=True).to_csv(
            os.path.join(args.marker_dir, "markers_all.csv"), index=False)
        info(f"      marker tables in {args.marker_dir}/")
    else:
        info("[8/8] Skipping markers")

    save_anndata(adata, args.output)
    info("Pipeline complete. Next: inspect markers, then annotate.py with a cluster->cell_type mapping.")


if __name__ == "__main__":
    main()
