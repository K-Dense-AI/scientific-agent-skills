"""
pipeline.py
===========
End-to-end MoA analysis pipeline for quantitative proteomics data.

Usage — Python API:
    from moa_analysis.pipeline import run_moa_analysis
    results = run_moa_analysis()                      # runs on built-in demo data
    results = run_moa_analysis(data_path="data.csv")  # runs on your data

Usage — CLI:
    python -m moa_analysis.pipeline                         # demo mode
    python -m moa_analysis.pipeline --data data.csv \\
        --output results/ --condition Drug_EC50

Pipeline steps:
    1. Load / simulate data                (data_loader)
    2. Log2 transform + QC filter         (preprocessing)
    3. Median-centering normalisation     (preprocessing)
    4. MinProb imputation                 (preprocessing)
    5. PCA + hierarchical clustering      (clustering)
    6. Differential abundance             (differential)
    7. Pathway ORA + signature scoring    (enrichment)
    8. MoA classification + similarity    (moa_classifier)
    9. Figures                            (plots)

Skills used:
    pyopenms           – referenced for MS data ingestion pathway
    statistical-analysis – Welch's t-test, BH FDR, normality
    scikit-learn       – PCA, RandomForest, silhouette
    scanpy / anndata   – AnnData container throughout
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .data_loader import simulate_p53_experiment, load_from_csv, build_anndata
from .preprocessing import log2_transform, filter_by_missingness, normalize, impute_missing
from .differential import run_differential_abundance, get_hits
from .enrichment import build_pathway_genesets, run_ora, score_signatures
from .clustering import run_pca, run_hierarchical_clustering, compute_sample_distance
from .moa_classifier import (
    build_reference_signatures,
    train_moa_classifier,
    predict_moa,
    compute_moa_similarity,
)
from .plots import (
    plot_volcano,
    plot_heatmap,
    plot_pca,
    plot_pathway_enrichment,
    plot_moa_similarity,
    plot_signature_scores,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_moa_analysis(
    data_path: str | Path | None = None,
    sample_metadata_path: str | Path | None = None,
    output_dir: str | Path = "moa_results",
    condition_col: str = "condition",
    timepoint_col: str = "timepoint",
    control_condition: str = "DMSO",
    fc_threshold: float = 1.0,
    fdr_threshold: float = 0.05,
    focus_condition: str | None = None,
    focus_timepoint: str | None = None,
    save_figures: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Run the complete MoA analysis pipeline.

    Parameters
    ----------
    data_path:             Path to protein intensity CSV/TSV (MaxQuant, DIA-NN,
                           Spectronaut, or generic).  Runs on simulated p53
                           data if None.
    sample_metadata_path:  Path to sample metadata CSV with columns:
                           sample_id, condition, timepoint [, replicate, batch].
                           Auto-inferred from column names if None.
    output_dir:            Directory for figures and TSV results.
    condition_col:         Column in sample metadata for treatment condition.
    timepoint_col:         Column in sample metadata for timepoint.
    control_condition:     Value of condition_col for the vehicle control.
    fc_threshold:          |log2FC| cutoff for hit classification.
    fdr_threshold:         BH-adjusted p-value cutoff.
    focus_condition:       Condition to use in per-figure analysis (default:
                           last non-control condition alphabetically).
    focus_timepoint:       Timepoint to use in per-figure analysis (default:
                           last timepoint).
    save_figures:          Write PNG figures to output_dir.
    verbose:               Print progress to stdout.

    Returns
    -------
    dict with keys:
        'adata'           – AnnData (preprocessed, with PCA / cluster labels)
        'diff_df'         – differential abundance table
        'ora_results'     – pathway ORA results per (condition, timepoint)
        'score_df'        – per-sample pathway signature scores
        'moa_predictions' – MoA classifier predictions
        'moa_similarity'  – cosine similarity to reference MoA signatures
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Load or simulate data ──────────────────────────────────────
    _log("Step 1/9 – Loading data", verbose)
    if data_path is None:
        _log("  No data_path provided → using built-in p53 simulation", verbose)
        adata = simulate_p53_experiment()
    else:
        intensity_df = load_from_csv(data_path)
        if sample_metadata_path:
            obs_df = pd.read_csv(sample_metadata_path, index_col=0)
        else:
            obs_df = _infer_sample_metadata(
                intensity_df.columns.tolist(), condition_col, timepoint_col
            )
        adata = build_anndata(intensity_df, obs_df)

    _log(f"  Loaded {adata.n_obs} samples × {adata.n_vars} proteins", verbose)

    # ── Step 2: Log2 transform + missingness filter ─────────────────────────
    _log("Step 2/9 – QC filter + log2 transform", verbose)
    log2_transform(adata)
    filter_by_missingness(
        adata,
        max_missing_fraction=0.70,
        min_valid_per_group=2,
        group_col=condition_col,
    )

    # ── Step 3: Normalisation ───────────────────────────────────────────────
    _log("Step 3/9 – Median-centering normalisation", verbose)
    normalize(adata, method="median_centering")

    # ── Step 4: Imputation ─────────────────────────────────────────────────
    _log("Step 4/9 – MinProb imputation", verbose)
    impute_missing(adata, method="minprob")

    # ── Step 5: PCA + clustering ───────────────────────────────────────────
    _log("Step 5/9 – PCA + hierarchical clustering", verbose)
    run_pca(adata, n_components=30, use_top_variable=2000, scale=True)
    run_hierarchical_clustering(adata, auto_select_k=True, use_pca=True, n_pcs=15)

    # ── Step 6: Differential abundance ────────────────────────────────────
    _log("Step 6/9 – Differential abundance (Welch's t-test + BH FDR)", verbose)
    diff_df = run_differential_abundance(
        adata,
        condition_col=condition_col,
        timepoint_col=timepoint_col,
        control_condition=control_condition,
        fc_threshold=fc_threshold,
        fdr_threshold=fdr_threshold,
    )

    # ── Step 7: Pathway enrichment ─────────────────────────────────────────
    _log("Step 7/9 – Pathway enrichment + signature scoring", verbose)
    genesets = build_pathway_genesets()

    # Determine focus condition / timepoint for single-comparison reports
    conditions = [c for c in adata.obs[condition_col].unique()
                  if c != control_condition]
    timepoints = sorted(adata.obs[timepoint_col].unique())
    fc_cond = focus_condition or conditions[-1]
    fc_tp   = focus_timepoint or timepoints[-1]

    ora_results = {}
    for cond in conditions:
        for tp in timepoints:
            key = f"{cond}@{tp}"
            ora = run_ora(
                diff_df,
                genesets=genesets,
                condition=cond,
                timepoint=tp,
                fdr_threshold=fdr_threshold,
            )
            if not ora.empty:
                ora_results[key] = ora

    score_df = score_signatures(adata, genesets=genesets, method="mean_zscore")

    # ── Step 8: MoA classification ─────────────────────────────────────────
    _log("Step 8/9 – MoA classification", verbose)
    signatures = build_reference_signatures()
    classifier = train_moa_classifier(diff_df, signatures=signatures)
    moa_predictions = predict_moa(diff_df, classifier)
    moa_similarity  = compute_moa_similarity(diff_df, signatures=signatures)

    # ── Step 9: Figures ───────────────────────────────────────────────────
    _log("Step 9/9 – Generating figures", verbose)
    if save_figures:
        _generate_figures(
            adata, diff_df, ora_results, score_df, moa_similarity,
            fc_cond, fc_tp, fc_threshold, fdr_threshold,
            output_dir, condition_col, timepoint_col, control_condition,
            genesets,
        )

    # ── Save tabular results ──────────────────────────────────────────────
    diff_df.to_csv(output_dir / "differential_abundance.tsv", sep="\t", index=False)
    moa_predictions.to_csv(output_dir / "moa_predictions.tsv", sep="\t", index=False)
    moa_similarity.to_csv(output_dir / "moa_similarity.tsv", sep="\t")
    score_df.to_csv(output_dir / "signature_scores.tsv", sep="\t")

    for key, ora in ora_results.items():
        fname = f"ora_{key.replace('@','_').replace(' ','_')}.tsv"
        ora.to_csv(output_dir / fname, sep="\t", index=False)

    # ── Summary ────────────────────────────────────────────────────────────
    _print_summary(diff_df, moa_predictions, classifier, fc_cond, fc_tp, verbose)

    return {
        "adata":           adata,
        "diff_df":         diff_df,
        "ora_results":     ora_results,
        "score_df":        score_df,
        "moa_predictions": moa_predictions,
        "moa_similarity":  moa_similarity,
        "classifier":      classifier,
    }


# ---------------------------------------------------------------------------
# Figure generation
# ---------------------------------------------------------------------------

def _generate_figures(
    adata, diff_df, ora_results, score_df, moa_similarity,
    fc_cond, fc_tp, fc_threshold, fdr_threshold,
    output_dir, condition_col, timepoint_col, control_condition,
    genesets,
):
    fig_dir = output_dir / "figures"
    fig_dir.mkdir(exist_ok=True)

    conditions = [c for c in adata.obs[condition_col].unique()
                  if c != control_condition]
    timepoints = sorted(adata.obs[timepoint_col].unique())

    # 1. Volcano plots for all (condition × timepoint)
    for cond in conditions:
        for tp in timepoints:
            ctp_df = diff_df[
                (diff_df["condition"] == cond) & (diff_df["timepoint"] == tp)
            ]
            if ctp_df["regulation"].nunique() <= 1:
                continue
            plot_volcano(
                diff_df, condition=cond, timepoint=tp,
                fc_threshold=fc_threshold, fdr_threshold=fdr_threshold,
                label_top_n=15,
                save_path=fig_dir / f"volcano_{cond}_{tp}.png",
            )

    # 2. Top-hits heatmap
    plot_heatmap(
        adata, diff_df=diff_df, n_top=60,
        condition_col=condition_col, timepoint_col=timepoint_col,
        title="Top 60 differentially abundant proteins",
        save_path=fig_dir / "heatmap_top60.png",
    )

    # 3. PCA
    plot_pca(
        adata, pc_x=1, pc_y=2,
        color_col=condition_col, shape_col=timepoint_col,
        save_path=fig_dir / "pca_pc1_pc2.png",
    )
    if adata.uns["pca"]["n_components"] >= 3:
        plot_pca(
            adata, pc_x=1, pc_y=3,
            color_col=condition_col, shape_col=timepoint_col,
            title="PCA — PC1 vs PC3",
            save_path=fig_dir / "pca_pc1_pc3.png",
        )

    # 4. Pathway enrichment (focus comparison)
    ora_key = f"{fc_cond}@{fc_tp}"
    if ora_key in ora_results and not ora_results[ora_key].empty:
        plot_pathway_enrichment(
            ora_results[ora_key],
            title=f"Pathway ORA — {fc_cond} vs {control_condition} @ {fc_tp}",
            save_path=fig_dir / f"pathway_ora_{fc_cond}_{fc_tp}.png",
        )

    # 5. MoA similarity heatmap
    plot_moa_similarity(
        moa_similarity,
        save_path=fig_dir / "moa_similarity.png",
    )

    # 6. Signature score time-course
    key_pathways = [
        "p53_stabilization", "p53_apoptosis", "p53_cell_cycle_arrest",
        "cell_cycle_G1S", "dna_damage_response", "apoptosis_intrinsic",
    ]
    available = [p for p in key_pathways if p in score_df.columns]
    if available:
        plot_signature_scores(
            score_df[available], adata.obs,
            pathways=available,
            condition_col=condition_col, timepoint_col=timepoint_col,
            control_condition=control_condition,
            title="Pathway activation over treatment time course",
            save_path=fig_dir / "signature_scores_timecourse.png",
        )

    print(f"[pipeline] Figures saved to {fig_dir}/")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _infer_sample_metadata(
    sample_names: list[str],
    condition_col: str,
    timepoint_col: str,
) -> pd.DataFrame:
    """
    Attempt to parse condition and timepoint from column names.
    Expected format: {condition}_{timepoint}_rep{n}  or similar.
    """
    rows = []
    for name in sample_names:
        parts = name.split("_")
        rows.append({
            "sample_id":  name,
            condition_col: parts[0] if len(parts) > 0 else "Unknown",
            timepoint_col: parts[1] if len(parts) > 1 else "t0",
            "replicate":  parts[2].replace("rep", "") if len(parts) > 2 else "1",
        })
    df = pd.DataFrame(rows)
    df.index = df["sample_id"]
    return df


def _print_summary(diff_df, moa_pred, classifier, fc_cond, fc_tp, verbose):
    if not verbose:
        return
    print("\n" + "=" * 60)
    print("MoA ANALYSIS COMPLETE")
    print("=" * 60)
    cv_mean, cv_std = classifier["cv_accuracy"]
    print(f"  Classifier CV accuracy : {cv_mean:.3f} ± {cv_std:.3f}")
    print(f"  Feature genes          : {len(classifier['feature_genes'])}")
    print(f"\n  MoA predictions:")
    for _, r in moa_pred.iterrows():
        print(f"    {r['condition']:20s} @ {r['timepoint']:5s} → "
              f"{r['predicted_moa']} ({r['confidence']:.2f})")
    print(f"\n  Top 10 MoA-informative proteins:")
    top10 = classifier["feature_importances"].head(10)
    for gene, imp in top10.items():
        print(f"    {gene:10s}  {imp:.4f}")
    print("=" * 60)


def _log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="MoA analysis pipeline for quantitative proteomics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run on built-in simulated p53 data
  python -m moa_analysis.pipeline

  # Run on your own data
  python -m moa_analysis.pipeline \\
      --data proteinGroups.txt \\
      --metadata sample_metadata.csv \\
      --output results/ \\
      --fc 1.0 --fdr 0.05

  # Specify focus condition for detailed reports
  python -m moa_analysis.pipeline \\
      --data data.csv --condition Drug_2xEC50 --timepoint 24h
        """,
    )
    parser.add_argument("--data",      help="Protein intensity TSV/CSV")
    parser.add_argument("--metadata",  help="Sample metadata CSV")
    parser.add_argument("--output",    default="moa_results", help="Output directory")
    parser.add_argument("--condition", help="Focus condition for detailed figures")
    parser.add_argument("--timepoint", help="Focus timepoint for detailed figures")
    parser.add_argument("--fc",        type=float, default=1.0,  help="|log2FC| threshold")
    parser.add_argument("--fdr",       type=float, default=0.05, help="FDR threshold")
    parser.add_argument("--no-figures", action="store_true", help="Skip figure generation")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    run_moa_analysis(
        data_path=args.data,
        sample_metadata_path=args.metadata,
        output_dir=args.output,
        focus_condition=args.condition,
        focus_timepoint=args.timepoint,
        fc_threshold=args.fc,
        fdr_threshold=args.fdr,
        save_figures=not args.no_figures,
    )
