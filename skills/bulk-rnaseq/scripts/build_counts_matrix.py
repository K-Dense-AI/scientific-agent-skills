#!/usr/bin/env python3
"""Assemble a gene-level counts matrix from RNA-seq quantification output.

Bridges the upstream (Salmon / STAR / featureCounts) and downstream (PyDESeq2)
halves of a bulk RNA-seq pipeline. Writes:

  counts.csv             genes x samples, INTEGER counts (never TPM/FPKM)
  metadata_template.csv  one row per sample (index=sample) to fill in for DE

Hand both to the `pydeseq2` skill. counts.csv stays genes x samples; the
pydeseq2 loader transposes to samples x genes.

Examples
--------
# Salmon: per-sample quant dirs (each containing quant.sf) + a tx2gene map
python build_counts_matrix.py --from salmon \
    --quant-dir quant/ --tx2gene tx2gene.tsv --output-dir counts/

# STAR --quantMode GeneCounts: a dir of *.ReadsPerGene.out.tab files
python build_counts_matrix.py --from star \
    --quant-dir star/ --strandedness reverse --output-dir counts/

# featureCounts: the combined matrix it wrote
python build_counts_matrix.py --from featurecounts \
    --counts-file counts/featurecounts.txt --output-dir counts/

Requires: pandas. Salmon mode also needs pytximport (uv pip install pytximport).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# STAR ReadsPerGene.out.tab column index per strandedness (col 0 is the gene id).
STAR_STRAND_COL = {"unstranded": 1, "forward": 2, "reverse": 3}


def _clean_sample_name(name: str) -> str:
    """Strip common aligner suffixes/extensions from a file or column name."""
    name = Path(str(name)).name
    for suf in (
        ".ReadsPerGene.out.tab",
        ".Aligned.sortedByCoord.out.bam",
        ".Aligned.out.bam",
        ".bam",
        ".sf",
    ):
        if name.endswith(suf):
            name = name[: -len(suf)]
    return name.rstrip(".")


def build_from_salmon(quant_dir: Path, tx2gene: Path) -> pd.DataFrame:
    """Aggregate per-sample Salmon quant.sf to gene level via pytximport.

    Uses counts_from_abundance='length_scaled_tpm' (the right choice for
    gene-level DE) and rounds the resulting estimated counts to integers,
    which PyDESeq2 requires. See references/counts-and-handoff.md.
    """
    try:
        from pytximport import tximport
    except ImportError:
        sys.exit("Salmon mode needs pytximport. Install with: uv pip install pytximport")

    if tx2gene is None:
        sys.exit("--tx2gene is required for --from salmon (columns: transcript_id, gene_id)")

    # Discover per-sample quant.sf files (sample name = parent directory name).
    sf_files = sorted(quant_dir.glob("*/quant.sf"))
    if not sf_files:
        # Fall back to a flat layout: *.sf directly in quant_dir.
        sf_files = sorted(quant_dir.glob("*.sf"))
    if not sf_files:
        sys.exit(f"No quant.sf found under {quant_dir} (expected <sample>/quant.sf)")

    sample_names = [
        f.parent.name if f.name == "quant.sf" else _clean_sample_name(f.name)
        for f in sf_files
    ]
    print(f"Salmon: {len(sf_files)} samples -> {sample_names}")

    txi = tximport(
        [str(f) for f in sf_files],
        data_type="salmon",
        transcript_gene_map=str(tx2gene),
        counts_from_abundance="length_scaled_tpm",
        ignore_transcript_version=True,
        output_type="anndata",
        return_data=True,
    )
    # AnnData: obs=samples, var=genes, X=samples x genes. Transpose to genes x samples.
    counts = txi.to_df().T
    counts.columns = sample_names
    counts.index.name = "gene_id"
    return counts.round().astype(int)


def build_from_star(quant_dir: Path, strandedness: str) -> pd.DataFrame:
    """Combine STAR *.ReadsPerGene.out.tab files into a gene x sample matrix."""
    col = STAR_STRAND_COL[strandedness]
    tabs = sorted(quant_dir.glob("*ReadsPerGene.out.tab"))
    if not tabs:
        sys.exit(f"No *ReadsPerGene.out.tab found under {quant_dir}")
    print(f"STAR: {len(tabs)} samples, strandedness={strandedness} (column {col})")

    series = {}
    for tab in tabs:
        # First 4 rows are summary stats (N_unmapped, N_multimapping, ...).
        df = pd.read_csv(tab, sep="\t", header=None, skiprows=4)
        s = pd.Series(df[col].values, index=df[0].values, dtype="int64")
        series[_clean_sample_name(tab.name)] = s

    counts = pd.DataFrame(series).fillna(0).astype("int64")
    counts.index.name = "gene_id"
    return counts


def build_from_featurecounts(counts_file: Path) -> pd.DataFrame:
    """Parse a combined featureCounts matrix into a gene x sample matrix."""
    if not counts_file.is_file():
        sys.exit(f"featureCounts file not found: {counts_file}")
    # featureCounts prepends a '#' command line; real header is the next row.
    df = pd.read_csv(counts_file, sep="\t", comment="#")
    # Layout: Geneid, Chr, Start, End, Strand, Length, <bam1>, <bam2>, ...
    meta_cols = ["Geneid", "Chr", "Start", "End", "Strand", "Length"]
    sample_cols = [c for c in df.columns if c not in meta_cols]
    if not sample_cols:
        sys.exit("No sample/count columns found in featureCounts file")
    counts = df.set_index("Geneid")[sample_cols].astype("int64")
    counts.columns = [_clean_sample_name(c) for c in counts.columns]
    counts.index.name = "gene_id"
    print(f"featureCounts: {len(sample_cols)} samples -> {list(counts.columns)}")
    return counts


def write_outputs(counts: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Drop all-zero genes (uninformative; pydeseq2 filters further).
    n_before = counts.shape[0]
    counts = counts[counts.sum(axis=1) > 0]
    dropped = n_before - counts.shape[0]

    counts_path = output_dir / "counts.csv"
    counts.to_csv(counts_path)

    meta = pd.DataFrame(
        {"condition": ["CHANGE_ME"] * counts.shape[1], "batch": [""] * counts.shape[1]},
        index=pd.Index(counts.columns, name="sample"),
    )
    meta_path = output_dir / "metadata_template.csv"
    meta.to_csv(meta_path)

    print(f"\n  genes:   {counts.shape[0]} (dropped {dropped} all-zero)")
    print(f"  samples: {counts.shape[1]}")
    print(f"  wrote {counts_path}  (genes x samples, integer)")
    print(f"  wrote {meta_path}  (fill in 'condition'/'batch', then run the pydeseq2 skill)")
    if (counts.columns.duplicated()).any():
        print("  WARNING: duplicate sample names detected — check your inputs.")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--from", dest="source", required=True,
        choices=["salmon", "star", "featurecounts"],
        help="Quantifier that produced the input.",
    )
    p.add_argument("--quant-dir", type=Path,
                   help="Directory of per-sample quant output (salmon/star).")
    p.add_argument("--tx2gene", type=Path,
                   help="transcript_id->gene_id map (salmon). TSV/CSV with those columns.")
    p.add_argument("--strandedness", choices=list(STAR_STRAND_COL), default="reverse",
                   help="Library strandedness for STAR column selection (default: reverse).")
    p.add_argument("--counts-file", type=Path,
                   help="Combined featureCounts matrix (featurecounts).")
    p.add_argument("--output-dir", type=Path, default=Path("counts"),
                   help="Where to write counts.csv + metadata_template.csv (default: counts/).")
    args = p.parse_args()

    if args.source == "salmon":
        if not args.quant_dir:
            sys.exit("--quant-dir is required for --from salmon")
        counts = build_from_salmon(args.quant_dir, args.tx2gene)
    elif args.source == "star":
        if not args.quant_dir:
            sys.exit("--quant-dir is required for --from star")
        counts = build_from_star(args.quant_dir, args.strandedness)
    else:
        if not args.counts_file:
            sys.exit("--counts-file is required for --from featurecounts")
        counts = build_from_featurecounts(args.counts_file)

    write_outputs(counts, args.output_dir)


if __name__ == "__main__":
    main()
