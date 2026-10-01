#!/usr/bin/env python3
"""Assemble a gene-level counts matrix from RNA-seq quantification output.

Bridges the upstream (Salmon / STAR / featureCounts) and downstream (PyDESeq2)
halves of a bulk RNA-seq pipeline. Writes:

  counts.csv             genes x samples, INTEGER counts (never TPM/FPKM)
  metadata_template.csv  one row per sample (index=sample) to fill in for DE
  counts_provenance.json input hashes, count mode and sample order

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

Requires: pandas and NumPy. Salmon mode also needs pytximport.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from _tabular import validate_header

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


def _validate_counts(counts: pd.DataFrame, *, estimated: bool = False) -> pd.DataFrame:
    """Reject ambiguous labels and malformed values before any integer conversion."""
    if counts.empty:
        raise ValueError("Counts matrix is empty")
    for label, values in (("gene", counts.index), ("sample", counts.columns)):
        if values.has_duplicates or values.isna().any() or any(not str(v).strip() for v in values):
            raise ValueError(f"Empty or duplicate {label} IDs in counts matrix")
    numeric = counts.apply(pd.to_numeric, errors="raise")
    values = numeric.to_numpy()
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Counts must be finite and non-negative")
    if (values >= 2**63).any():
        raise ValueError("Counts exceed the supported int64 range")
    if not estimated and (values != np.floor(values)).any():
        raise ValueError("Fractional counts require an explicit estimated-count workflow; refusing truncation")
    return numeric.round().astype("int64")


def _file_record(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest()}


def build_from_salmon(quant_dir: Path, tx2gene: Path,
                      ignore_transcript_version: bool = False) -> pd.DataFrame:
    """Aggregate per-sample Salmon quant.sf to gene level via pytximport.

    Uses counts_from_abundance='length_scaled_tpm' for full-length bulk
    gene-level DE and rounds the resulting estimated counts to integers,
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
    if len(sample_names) != len(set(sample_names)):
        raise ValueError("Duplicate sample IDs after filename normalization")
    validate_header(tx2gene, delimiter=None)
    mapping = pd.read_csv(tx2gene, sep=None, engine="python", dtype=str, keep_default_na=False)
    if not {"transcript_id", "gene_id"}.issubset(mapping.columns):
        raise ValueError("tx2gene needs transcript_id and gene_id headers")
    mapping = mapping[["transcript_id", "gene_id"]].copy()
    if mapping.empty or mapping.eq("").any().any():
        raise ValueError("tx2gene has empty transcript/gene IDs")
    if ignore_transcript_version:
        mapping["transcript_id"] = mapping["transcript_id"].str.replace(r"\.\d+$", "", regex=True)
    if mapping["transcript_id"].duplicated().any():
        raise ValueError("Duplicate transcript IDs in tx2gene (possibly after version stripping)")
    reference_ids = None
    for path in sf_files:
        validate_header(path, delimiter="\t")
        quant = pd.read_csv(path, sep="\t", dtype={"Name": str}, keep_default_na=False)
        required = {"Name", "Length", "EffectiveLength", "TPM", "NumReads"}
        if not required.issubset(quant.columns):
            raise ValueError(f"Invalid Salmon quant.sf columns: {path}")
        names = quant["Name"]
        if ignore_transcript_version:
            names = names.str.replace(r"\.\d+$", "", regex=True)
        if names.duplicated().any() or names.eq("").any():
            raise ValueError(f"Empty or duplicate transcript IDs: {path}")
        numeric = quant[["Length", "EffectiveLength", "TPM", "NumReads"]].apply(pd.to_numeric)
        if not np.isfinite(numeric.to_numpy()).all() or (numeric < 0).any().any():
            raise ValueError(f"Invalid Salmon numeric values: {path}")
        if numeric["NumReads"].sum() <= 0:
            raise ValueError(f"No quantified fragments: {path}")
        if reference_ids is not None and not names.equals(reference_ids):
            raise ValueError("Salmon transcript IDs/order differ; use one reference and quantifier run convention")
        reference_ids = names
        missing = set(names) - set(mapping["transcript_id"])
        if missing:
            raise ValueError(f"tx2gene missing {len(missing)} quantified transcript IDs; e.g. {sorted(missing)[:5]}")
    print(f"Salmon: {len(sf_files)} samples -> {sample_names}")

    txi = tximport(
        [str(f) for f in sf_files],
        data_type="salmon",
        transcript_gene_map=mapping,
        counts_from_abundance="length_scaled_tpm",
        ignore_transcript_version=ignore_transcript_version,
        ignore_after_bar=False,
        output_type="anndata",
        return_data=True,
    )
    # AnnData: obs=samples, var=genes, X=samples x genes. Transpose to genes x samples.
    counts = txi.to_df().T
    counts.columns = sample_names
    counts.index.name = "gene_id"
    counts = _validate_counts(counts, estimated=True)
    counts.attrs["provenance"] = {
        "source": "salmon", "counts_from_abundance": "length_scaled_tpm",
        "assay": "full_length_bulk", "rounding": "nearest_integer_ties_to_even",
        "ignore_transcript_version": ignore_transcript_version,
        "pytximport_version": version("pytximport"), "tx2gene": _file_record(tx2gene),
        "inputs": [_file_record(f) for f in sf_files],
    }
    return counts


def build_from_star(quant_dir: Path, strandedness: str) -> pd.DataFrame:
    """Combine STAR *.ReadsPerGene.out.tab files into a gene x sample matrix."""
    col = STAR_STRAND_COL[strandedness]
    tabs = sorted(quant_dir.glob("*ReadsPerGene.out.tab"))
    if not tabs:
        sys.exit(f"No *ReadsPerGene.out.tab found under {quant_dir}")
    print(f"STAR: {len(tabs)} samples, strandedness={strandedness} (column {col})")

    series = {}
    reference_genes = None
    for tab in tabs:
        # First 4 rows are summary stats (N_unmapped, N_multimapping, ...).
        df = pd.read_csv(tab, sep="\t", header=None, dtype={0: str}, keep_default_na=False)
        if df.shape[1] != 4 or df.iloc[:4, 0].tolist() != ["N_unmapped", "N_multimapping", "N_noFeature", "N_ambiguous"]:
            raise ValueError(f"Invalid STAR GeneCounts header/layout: {tab}")
        df = df.iloc[4:]
        sample = _clean_sample_name(tab.name)
        if sample in series:
            raise ValueError(f"Duplicate sample ID after filename normalization: {sample}")
        s = pd.Series(df[col].values, index=df[0].values)
        _validate_counts(s.to_frame(sample))
        if reference_genes is not None and set(s.index) != reference_genes:
            raise ValueError("STAR gene sets differ; check annotation/reference instead of filling missing genes with zero")
        reference_genes = set(s.index)
        series[sample] = s

    counts = _validate_counts(pd.DataFrame(series))
    counts.index.name = "gene_id"
    counts.attrs["provenance"] = {"source": "star", "strandedness": strandedness,
                                  "rounding": "none", "inputs": [_file_record(f) for f in tabs]}
    return counts


def build_from_featurecounts(counts_file: Path) -> pd.DataFrame:
    """Parse a combined featureCounts matrix into a gene x sample matrix."""
    if not counts_file.is_file():
        sys.exit(f"featureCounts file not found: {counts_file}")
    # featureCounts prepends a '#' command line; real header is the next row.
    validate_header(counts_file, delimiter="\t", comment="#")
    df = pd.read_csv(counts_file, sep="\t", comment="#", dtype={"Geneid": str}, keep_default_na=False)
    # Layout: Geneid, Chr, Start, End, Strand, Length, <bam1>, <bam2>, ...
    meta_cols = ["Geneid", "Chr", "Start", "End", "Strand", "Length"]
    if not set(meta_cols).issubset(df.columns):
        raise ValueError("featureCounts file is missing required annotation columns")
    sample_cols = [c for c in df.columns if c not in meta_cols]
    if not sample_cols:
        sys.exit("No sample/count columns found in featureCounts file")
    counts = df.set_index("Geneid")[sample_cols]
    counts.columns = [_clean_sample_name(c) for c in counts.columns]
    counts = _validate_counts(counts)
    counts.index.name = "gene_id"
    counts.attrs["provenance"] = {"source": "featurecounts", "rounding": "none",
                                  "inputs": [_file_record(counts_file)]}
    print(f"featureCounts: {len(sample_cols)} samples -> {list(counts.columns)}")
    return counts


def write_outputs(counts: pd.DataFrame, output_dir: Path) -> None:
    provenance = counts.attrs.get("provenance", {"source": "unspecified"})
    counts = _validate_counts(counts)
    if (counts.sum(axis=0) <= 0).any():
        raise ValueError("A sample has zero total counts; resolve it before DE")

    # Drop all-zero genes (uninformative; pydeseq2 filters further).
    n_before = counts.shape[0]
    counts = counts[counts.sum(axis=1) > 0]
    dropped = n_before - counts.shape[0]

    output_dir.mkdir(parents=True, exist_ok=True)
    counts_path = output_dir / "counts.csv"
    counts.to_csv(counts_path)

    meta = pd.DataFrame(
        {"condition": ["CHANGE_ME"] * counts.shape[1], "batch": [""] * counts.shape[1]},
        index=pd.Index(counts.columns, name="sample"),
    )
    meta_path = output_dir / "metadata_template.csv"
    meta.to_csv(meta_path)
    provenance.update({"orientation": "genes_by_samples", "samples": list(counts.columns),
                       "all_zero_genes_removed": dropped, "pandas_version": pd.__version__})
    (output_dir / "counts_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    print(f"\n  genes:   {counts.shape[0]} (dropped {dropped} all-zero)")
    print(f"  samples: {counts.shape[1]}")
    print(f"  wrote {counts_path}  (genes x samples, integer)")
    print(f"  wrote {meta_path}  (fill in 'condition'/'batch', then run the pydeseq2 skill)")


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
    p.add_argument("--strandedness", choices=list(STAR_STRAND_COL),
                   help="Verified library strandedness (required for STAR; no default).")
    p.add_argument("--ignore-transcript-version", action="store_true",
                   help="Strip terminal .N versions in Salmon IDs and map, after checking reference provenance.")
    p.add_argument("--counts-file", type=Path,
                   help="Combined featureCounts matrix (featurecounts).")
    p.add_argument("--output-dir", type=Path, default=Path("counts"),
                   help="Where to write counts.csv + metadata_template.csv (default: counts/).")
    args = p.parse_args()

    if args.source == "salmon":
        if not args.quant_dir:
            sys.exit("--quant-dir is required for --from salmon")
        counts = build_from_salmon(args.quant_dir, args.tx2gene, args.ignore_transcript_version)
    elif args.source == "star":
        if not args.quant_dir:
            sys.exit("--quant-dir is required for --from star")
        if not args.strandedness:
            sys.exit("--strandedness is required for --from star; infer it before selecting counts")
        counts = build_from_star(args.quant_dir, args.strandedness)
    else:
        if not args.counts_file:
            sys.exit("--counts-file is required for --from featurecounts")
        counts = build_from_featurecounts(args.counts_file)

    write_outputs(counts, args.output_dir)


if __name__ == "__main__":
    main()
