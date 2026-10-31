#!/usr/bin/env python3
"""
PyDESeq2 Analysis Script

This script performs a complete differential expression analysis using PyDESeq2.
It can be used as a template for standard RNA-seq DEA workflows.

Usage:
    python run_deseq2_analysis.py --counts counts.csv --metadata metadata.csv \
           --design "~condition" --contrast condition treated control \
           --output results/

Requirements:
    - pydeseq2
    - pandas
    - matplotlib (installed by PyDESeq2; used for plots)
"""

import argparse
import csv
import json
from importlib.metadata import version
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.default_inference import DefaultInference
    from pydeseq2.ds import DeseqStats
except ImportError:
    print("Error: pydeseq2 not installed. Install with: uv pip install pydeseq2==0.5.4")
    sys.exit(1)


def read_indexed_csv(path):
    """Reject ambiguous source headers before pandas can rename duplicates."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        for line_number, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValueError(f"CSV row {line_number} has the wrong number of fields")
    if len(header) < 2 or any(not item.strip() for item in header[1:]):
        raise ValueError("CSV requires an identifier column and named data columns")
    if len(set(header)) != len(header):
        raise ValueError("CSV contains duplicate headers")
    frame = pd.read_csv(path, dtype={0: str})
    frame = frame.set_index(frame.columns[0])
    for axis in (frame.index, frame.columns):
        if axis.has_duplicates or axis.isna().any() or any(not str(x).strip() for x in axis):
            raise ValueError("Sample, gene, and metadata identifiers must be nonempty and unique")
    return frame


def validate_counts(counts_df):
    """Validate the count domain; integer-valued data do not prove raw-count provenance."""
    if counts_df.empty:
        raise ValueError("Count matrix must contain samples and genes")
    try:
        values = counts_df.to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Counts must be numeric") from exc
    if not np.isfinite(values).all():
        raise ValueError("Counts must be finite without missing values")
    if (values < 0).any():
        raise ValueError("Count matrix contains negative values")
    if (values != np.floor(values)).any() or (values > 2**53 - 1).any():
        raise ValueError("Counts must be exact nonnegative integers no larger than 2**53 - 1")
    if (values.sum(axis=1) == 0).any():
        raise ValueError("Every sample must have positive total counts")


def load_and_validate_data(counts_path, metadata_path, transpose_counts=True):
    """Load explicitly oriented CSVs, require the same sample set, then align."""
    counts_df = read_indexed_csv(counts_path)
    if transpose_counts:
        counts_df = counts_df.T
    metadata = read_indexed_csv(metadata_path)
    if set(counts_df.index) != set(metadata.index):
        raise ValueError("Sample sets differ; resolve omissions explicitly before analysis")
    metadata = metadata.loc[counts_df.index].copy()
    validate_counts(counts_df)
    print(f"[OK] Loaded {counts_df.shape[0]} samples x {counts_df.shape[1]} genes")
    return counts_df.astype(np.int64), metadata


def filter_data(counts_df, metadata, min_counts=10, condition_col=None):
    """Apply a declared total-count gene prefilter without silently excluding samples."""
    if isinstance(min_counts, bool) or not isinstance(min_counts, (int, np.integer)) or min_counts < 0:
        raise ValueError("min_counts must be a nonnegative integer")
    if not counts_df.index.equals(metadata.index):
        raise ValueError("Counts and metadata sample order must match")
    if condition_col:
        if condition_col not in metadata:
            raise ValueError(f"Missing contrast column: {condition_col}")
        if metadata[condition_col].isna().any():
            raise ValueError("Missing contrast annotations; resolve sample exclusions explicitly")
    validate_counts(counts_df)
    counts_df = counts_df.loc[:, counts_df.sum(axis=0) >= min_counts].copy()
    validate_counts(counts_df)
    print(f"[OK] Retained {counts_df.shape[1]} genes at total counts >= {min_counts}")
    return counts_df, metadata


def prepare_contrast_metadata(metadata, contrast):
    """Set the CLI categorical reference before fitting, preserving all observed levels."""
    variable, tested, reference = contrast
    if variable not in metadata or metadata[variable].isna().any():
        raise ValueError("Contrast variable must exist and have no missing annotations")
    values = metadata[variable].astype(str)
    levels = list(pd.unique(values))
    if tested == reference or tested not in levels or reference not in levels:
        raise ValueError("Contrast requires two distinct observed levels")
    metadata = metadata.copy()
    metadata[variable] = pd.Categorical(values, categories=[reference] + [x for x in levels if x != reference])
    return metadata


def run_deseq2(counts_df, metadata, design, n_cpus=1):
    """Run DESeq2 normalization and fitting."""
    print(f"\nInitializing DeseqDataSet with design: {design}")

    validate_counts(counts_df)
    if n_cpus < 1:
        raise ValueError("n_cpus must be positive")
    inference = DefaultInference(n_cpus=n_cpus)
    dds = DeseqDataSet(
        counts=counts_df,
        metadata=metadata,
        design=design,
        refit_cooks=True,
        inference=inference,
        quiet=False
    )

    matrix = dds.obsm["design_matrix"]
    if not matrix.index.equals(counts_df.index) or not np.isfinite(matrix.to_numpy()).all():
        raise ValueError("Design matrix must retain every sample and contain finite values")
    if np.linalg.matrix_rank(matrix.to_numpy()) != matrix.shape[1]:
        raise ValueError("Design is not full rank; inspect confounding and redundant terms")
    if matrix.shape[0] <= matrix.shape[1]:
        raise ValueError("Design requires residual degrees of freedom and biological replication")

    print("\nRunning DESeq2 pipeline...")
    print("  Step 1/7: Computing size factors...")
    print("  Step 2/7: Fitting genewise dispersions...")
    print("  Step 3/7: Fitting dispersion trend curve...")
    print("  Step 4/7: Computing dispersion priors...")
    print("  Step 5/7: Fitting MAP dispersions...")
    print("  Step 6/7: Fitting log fold changes...")
    print("  Step 7/7: Calculating Cook's distances...")

    dds.deseq2()

    print("\n[OK] DESeq2 fitting complete")

    return dds, inference


def infer_shrink_coeff(dds, contrast, coeff=None):
    """Require the tested contrast to equal one positive design coefficient."""
    columns = list(dds.obsm["design_matrix"].columns)
    vector = np.asarray(dds.contrast(column=contrast[0], group_to_compare=contrast[1], baseline=contrast[2]))
    matches = [name for i, name in enumerate(columns)
               if np.allclose(vector, np.eye(len(columns))[i], rtol=0, atol=1e-12)]
    if len(matches) != 1 or (coeff is not None and coeff != matches[0]):
        raise ValueError(
            "LFC shrinkage needs a single positive coefficient matching the exact contrast. "
            f"Contrast vector: {vector.tolist()}; columns: {columns}. "
            "Relevel and refit, or use --no-shrink; --shrink-coeff cannot override a mismatch."
        )
    return matches[0]


def run_statistical_tests(dds, contrast, alpha=0.05, shrink_lfc=True, inference=None, shrink_coeff=None):
    """Perform Wald tests and compute p-values."""
    if not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be finite and between 0 and 1")
    coeff = infer_shrink_coeff(dds, contrast, shrink_coeff) if shrink_lfc else None
    print(f"\nPerforming statistical tests...")
    print(f"  Contrast: {contrast}")
    print(f"  Significance threshold: {alpha}")

    ds = DeseqStats(
        dds,
        contrast=contrast,
        alpha=alpha,
        cooks_filter=True,
        independent_filter=True,
        inference=inference,
        quiet=False
    )

    print("\n  Running Wald tests...")
    print("  Filtering outliers based on Cook's distance...")
    print("  Applying independent filtering...")
    print("  Adjusting p-values (Benjamini-Hochberg)...")

    ds.summary()
    ds.unshrunk_results_df = ds.results_df.copy(deep=True)
    ds.shrink_coeff = coeff

    print("\n[OK] Statistical testing complete")

    # Optional LFC shrinkage
    if shrink_lfc:
        print("\nApplying LFC shrinkage for visualization...")
        ds.lfc_shrink(coeff=coeff)
        print("[OK] LFC shrinkage complete")

    return ds


def save_results(ds, dds, output_dir):
    """Save results and intermediate objects."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving results to {output_dir}/")

    # Save statistical results
    results_path = output_dir / "deseq2_results.csv"
    ds.results_df.to_csv(results_path)
    unshrunk = getattr(ds, "unshrunk_results_df", ds.results_df)
    unshrunk.to_csv(output_dir / "deseq2_results_unshrunken.csv")
    print(f"  Saved: {results_path}")

    # Save significant genes
    alpha = ds.alpha
    significant = ds.results_df[ds.results_df.padj < alpha]
    sig_path = output_dir / "significant_genes.csv"
    significant.to_csv(sig_path)
    print(f"  Saved: {sig_path} ({len(significant)} significant genes)")

    # Save sorted results
    sorted_results = ds.results_df.sort_values("padj")
    sorted_path = output_dir / "results_sorted_by_padj.csv"
    sorted_results.to_csv(sorted_path)
    print(f"  Saved: {sorted_path}")

    # Save as AnnData/H5AD to avoid unsafe pickle interchange.
    dds_path = output_dir / "deseq_dataset.h5ad"
    dds.to_picklable_anndata().write_h5ad(dds_path)
    print(f"  Saved: {dds_path}")

    manifest = {
        "alpha": alpha,
        "design": getattr(dds, "design", None),
        "size_factors_fit_type_requested": getattr(dds, "size_factors_fit_type", None),
        "retained_genes": len(ds.results_df),
        "contrast": list(ds.contrast),
        "shrink_coefficient": getattr(ds, "shrink_coeff", None),
        "pvalues_and_stat": "unshrunken Wald test",
        "versions": {name: version(name) for name in ("pydeseq2", "anndata", "numpy", "pandas")},
    }
    (output_dir / "analysis_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # Print summary
    print(f"\n{'='*60}")
    print("ANALYSIS SUMMARY")
    print(f"{'='*60}")
    print(f"Genes retained: {len(ds.results_df)}; finite p-values: {ds.results_df.pvalue.notna().sum()}")
    print(f"Significant genes (padj < {alpha}): {len(significant)}")
    print(f"Upregulated: {len(significant[significant.log2FoldChange > 0])}")
    print(f"Downregulated: {len(significant[significant.log2FoldChange < 0])}")
    print(f"{'='*60}")

    # Show top genes
    print("\nTop 10 most significant genes:")
    print(sorted_results.head(10)[["baseMean", "log2FoldChange", "pvalue", "padj"]])

    return results_path


def create_plots(ds, output_dir):
    """Create basic visualization plots."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("\nNote: matplotlib not installed. Skipping plot generation.")
        return

    output_dir = Path(output_dir)
    results = ds.results_df.copy()
    alpha = ds.alpha
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nGenerating plots...")

    # Volcano plot
    # Missing adjusted p-values remain missing; zero p-values are capped only for display.
    results["-log10(padj)"] = -np.log10(results.padj.clip(lower=np.finfo(float).tiny))

    plt.figure(figsize=(10, 6))
    significant = results.padj < alpha
    plt.scatter(
        results.loc[~significant, "log2FoldChange"],
        results.loc[~significant, "-log10(padj)"],
        alpha=0.3, s=10, c='gray', label='Not significant'
    )
    plt.scatter(
        results.loc[significant, "log2FoldChange"],
        results.loc[significant, "-log10(padj)"],
        alpha=0.6, s=10, c='red', label=f'Significant (padj < {alpha})'
    )
    plt.axhline(-np.log10(alpha), color='blue', linestyle='--', linewidth=1, alpha=0.5)
    plt.axvline(1, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    plt.axvline(-1, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    plt.xlabel("Log2 Fold Change", fontsize=12)
    plt.ylabel("-Log10(Adjusted P-value)", fontsize=12)
    plt.title("Volcano Plot", fontsize=14, fontweight='bold')
    plt.legend()
    plt.tight_layout()
    volcano_path = output_dir / "volcano_plot.png"
    plt.savefig(volcano_path, dpi=300)
    plt.close()
    print(f"  Saved: {volcano_path}")

    # MA plot: distinguish absent adjusted tests from tested nonsignificant genes.
    plt.figure(figsize=(10, 6))
    tested_nonsignificant = (~significant) & results.padj.notna()
    plt.scatter(
        np.log10(results.loc[tested_nonsignificant, "baseMean"] + 1),
        results.loc[tested_nonsignificant, "log2FoldChange"],
        alpha=0.3, s=10, c='gray', label='Not significant'
    )
    plt.scatter(
        np.log10(results.loc[significant, "baseMean"] + 1),
        results.loc[significant, "log2FoldChange"],
        alpha=0.6, s=10, c='red', label=f'Significant (padj < {alpha})'
    )
    missing = results.padj.isna()
    plt.scatter(
        np.log10(results.loc[missing, "baseMean"] + 1),
        results.loc[missing, "log2FoldChange"],
        alpha=0.4, s=12, c='silver', marker='x', label='No adjusted p-value'
    )
    plt.axhline(0, color='blue', linestyle='--', linewidth=1, alpha=0.5)
    plt.xlabel("Log10(Base Mean + 1)", fontsize=12)
    plt.ylabel("Log2 Fold Change", fontsize=12)
    plt.title("MA Plot", fontsize=14, fontweight='bold')
    plt.legend()
    plt.tight_layout()
    ma_path = output_dir / "ma_plot.png"
    plt.savefig(ma_path, dpi=300)
    plt.close()
    print(f"  Saved: {ma_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run PyDESeq2 differential expression analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  python run_deseq2_analysis.py \\
    --counts counts.csv \\
    --metadata metadata.csv \\
    --design "~condition" \\
    --contrast condition treated control \\
    --output results/

  # Multi-factor analysis
  python run_deseq2_analysis.py \\
    --counts counts.csv \\
    --metadata metadata.csv \\
    --design "~batch + condition" \\
    --contrast condition treated control \\
    --output results/ \\
    --n-cpus 4 \\
    --shrink-coeff "condition[T.treated]"
        """
    )

    parser.add_argument("--counts", required=True, help="Path to count matrix CSV file")
    parser.add_argument("--metadata", required=True, help="Path to metadata CSV file")
    parser.add_argument("--design", required=True, help="Design formula (e.g., '~condition')")
    parser.add_argument(
        "--contrast",
        nargs=3,
        required=True,
        metavar=("VARIABLE", "TEST", "REFERENCE"),
        help="Contrast specification: variable test_level reference_level",
    )
    parser.add_argument("--output", default="results", help="Output directory (default: results)")
    parser.add_argument(
        "--min-counts",
        type=int,
        default=10,
        help="Minimum total counts for gene filtering (default: 10)",
    )
    parser.add_argument("--alpha", type=float, default=0.05, help="Significance threshold (default: 0.05)")
    parser.add_argument(
        "--no-transpose",
        action="store_true",
        help="Don't transpose count matrix (use if already samples × genes)",
    )
    parser.add_argument("--no-shrink", action="store_true", help="Skip LFC shrinkage")
    parser.add_argument(
        "--shrink-coeff",
        help="Design-matrix coefficient to shrink (e.g., 'condition[T.treated]')",
    )
    parser.add_argument(
        "--n-cpus",
        type=int,
        default=1,
        help="Number of CPUs for parallel processing (default: 1)",
    )
    parser.add_argument("--plots", action="store_true", help="Generate volcano and MA plots")

    args = parser.parse_args()
    if not np.isfinite(args.alpha) or not 0 < args.alpha < 1:
        parser.error("--alpha must be finite and between 0 and 1")
    if args.n_cpus < 1 or args.min_counts < 0:
        parser.error("--n-cpus must be positive and --min-counts nonnegative")
    if args.no_shrink and args.shrink_coeff:
        parser.error("--shrink-coeff cannot be combined with --no-shrink")

    # Load data
    counts_df, metadata = load_and_validate_data(
        args.counts,
        args.metadata,
        transpose_counts=not args.no_transpose,
    )

    # Filter data
    condition_col = args.contrast[0]
    counts_df, metadata = filter_data(
        counts_df,
        metadata,
        min_counts=args.min_counts,
        condition_col=condition_col,
    )

    metadata = prepare_contrast_metadata(metadata, args.contrast)

    # Run DESeq2
    dds, inference = run_deseq2(counts_df, metadata, args.design, n_cpus=args.n_cpus)

    # Statistical testing
    ds = run_statistical_tests(
        dds,
        contrast=args.contrast,
        alpha=args.alpha,
        shrink_lfc=not args.no_shrink,
        inference=inference,
        shrink_coeff=args.shrink_coeff,
    )

    # Save results
    save_results(ds, dds, args.output)

    # Create plots if requested
    if args.plots:
        create_plots(ds, args.output)

    print(f"\n[OK] Analysis complete! Results saved to {args.output}/")


if __name__ == "__main__":
    main()
