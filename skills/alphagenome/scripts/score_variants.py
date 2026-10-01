#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["alphagenome>=0.9.0"]
# ///
"""Score variants on demand with the AlphaGenome model API (human or mouse).

Use this when a variant is not in the Atlas (indels, mouse, non-reference
REF alleles, a haplotype background) or when you need a scorer configuration
the Atlas did not precompute. For hg38 SNVs, ``atlas_query.py`` is faster and
has a larger quota.

Each variant is scored inside a window centred on it (default 1 Mb, the
model's full context) with the recommended scorers, and the result is the
official tidy long table: one row per variant x scorer x track (x gene).

Examples:
  python score_variants.py --variant chr22:36201698:A>C -o scores.tsv
  python score_variants.py --input variants.vcf --scorers RNA_SEQ SPLICE_SITE_USAGE \\
      --ontology UBERON:0001157 --min-abs-quantile 0.99 -o colon.tsv
  python score_variants.py --organism mouse --variant chr7:45000000:A>G --sequence-length 500KB
  python score_variants.py --list-scorers
  python score_variants.py --list-tracks --output-type RNA_SEQ --query liver -o tracks.tsv
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Any

import _common as common

#: Supported input windows. Longer context is better; 1 Mb is the default.
SEQUENCE_LENGTHS: dict[str, int] = {
    "16KB": 2**14,
    "100KB": 2**17,
    "500KB": 2**19,
    "1MB": 2**20,
}

ORGANISMS = ("human", "mouse")
MAX_SCORERS_PER_REQUEST = 20


def parse_sequence_length(text: str) -> int:
    key = text.strip().upper().replace(" ", "")
    if key in SEQUENCE_LENGTHS:
        return SEQUENCE_LENGTHS[key]
    if key.isdigit() and int(key) in SEQUENCE_LENGTHS.values():
        return int(key)
    raise ValueError(f"sequence length must be one of {', '.join(SEQUENCE_LENGTHS)} (got {text!r})")


def select_scorers(names: Sequence[str] | None, organism: str, include_active: bool = False) -> list[Any]:
    """Pick recommended scorer configurations by name, validated for the organism.

    With no names, every recommended scorer is used except the ``*_ACTIVE``
    variants (absolute activity of the allele, not the REF-ALT difference),
    which are only useful when explicitly asked for.
    """
    from alphagenome.models import dna_client, variant_scorers  # noqa: PLC0415

    recommended = variant_scorers.RECOMMENDED_VARIANT_SCORERS
    organism_enum = dna_client.Organism.HOMO_SAPIENS if organism == "human" else dna_client.Organism.MUS_MUSCULUS
    if names:
        unknown = [name for name in names if name not in recommended]
        if unknown:
            raise ValueError(f"unknown scorer(s) {unknown}; choose from {sorted(recommended)}")
        chosen = list(dict.fromkeys(names))
    else:
        chosen = [name for name in recommended if include_active or not name.endswith("_ACTIVE")]
    selected = []
    for name in chosen:
        scorer = recommended[name]
        supported = variant_scorers.SUPPORTED_ORGANISMS[scorer.base_variant_scorer]
        if organism_enum.to_proto() not in supported:
            common.warn(f"scorer {name} is not available for {organism}; skipped")
            continue
        selected.append(scorer)
    if len(selected) > MAX_SCORERS_PER_REQUEST:
        raise ValueError(f"at most {MAX_SCORERS_PER_REQUEST} scorers per request; {len(selected)} selected")
    return selected


def make_model(args: argparse.Namespace):
    api_key = common.load_api_key(args.api_key_env)
    common.require_alphagenome()
    import grpc  # noqa: PLC0415
    from alphagenome.models import dna_client  # noqa: PLC0415

    try:
        return dna_client.create(api_key, timeout=args.timeout)
    except grpc.FutureTimeoutError as error:  # pragma: no cover - network
        raise SystemExit(
            f"could not reach the AlphaGenome service within {args.timeout}s "
            "(gdmscience.googleapis.com:443); check network access and proxies"
        ) from error


def organism_enum(name: str):
    from alphagenome.models import dna_client  # noqa: PLC0415

    return dna_client.Organism.HOMO_SAPIENS if name == "human" else dna_client.Organism.MUS_MUSCULUS


def list_tracks(model, args: argparse.Namespace) -> int:
    metadata = model.output_metadata(organism_enum(args.organism)).concatenate()
    frame = metadata
    if args.output_type:
        wanted = {name.upper() for name in args.output_type}
        column = "output_type" if "output_type" in frame.columns else None
        if column:
            frame = frame[frame[column].astype(str).str.upper().str.replace("OUTPUTTYPE.", "", regex=False).isin(wanted)]
    if args.query:
        needle = args.query.lower()
        mask = frame.astype(str).apply(lambda column: column.str.lower().str.contains(needle, regex=False)).any(axis=1)
        frame = frame[mask]
    rows = frame.to_dict("records")
    if not args.output and len(rows) > 200 and not args.force_stdout:
        raise SystemExit(f"{len(rows)} tracks match; narrow with --output-type/--query or write them with -o FILE")
    common.write_rows(rows, args.output, common.format_from_output(args.output, args.format))
    return 0


def list_scorers() -> int:
    from alphagenome.models import variant_scorers  # noqa: PLC0415

    rows = []
    for name, scorer in variant_scorers.RECOMMENDED_VARIANT_SCORERS.items():
        row: dict[str, Any] = {"name": name, "scorer": type(scorer).__name__}
        for attribute in ("requested_output", "width", "aggregation_type"):
            value = getattr(scorer, attribute, None)
            if value is not None:
                row[attribute] = getattr(value, "name", value)
        rows.append(row)
    common.write_rows(rows, None, "tsv")
    return 0


def score(model, args: argparse.Namespace) -> int:
    from alphagenome.models import variant_scorers  # noqa: PLC0415

    specs, warnings = common.collect_variants(args.variant, args.input)
    for message in warnings:
        common.warn(message)
    if not specs:
        raise SystemExit("no variants given; use --variant and/or --input")

    length = parse_sequence_length(args.sequence_length)
    scorers = select_scorers(args.scorers, args.organism, include_active=args.include_active)
    if not scorers:
        raise SystemExit("no scorers left after organism filtering")

    from alphagenome.data import genome  # noqa: PLC0415

    variants = [
        genome.Variant(spec.chromosome, spec.position, spec.ref, spec.alt, name=spec.name or str(spec)) for spec in specs
    ]
    intervals = [variant.reference_interval.resize(length) for variant in variants]
    results = model.score_variants(
        intervals,
        variants,
        scorers,
        organism=organism_enum(args.organism),
        progress_bar=False,
        max_workers=args.workers,
    )
    frame = variant_scorers.tidy_scores(results, match_gene_strand=True)
    if frame is None or frame.empty:
        raise SystemExit("the model returned no scores")

    if args.ontology and "ontology_curie" in frame.columns:
        frame = frame[frame["ontology_curie"].isin(set(args.ontology))]
    if args.biosample and "biosample_name" in frame.columns:
        frame = frame[frame["biosample_name"].astype(str).str.contains(args.biosample, case=False, regex=False)]
    if args.gene and "gene_name" in frame.columns:
        frame = frame[frame["gene_name"].isin(set(args.gene)) | frame["gene_name"].isna()]
    if args.min_abs_quantile is not None and "quantile_score" in frame.columns:
        frame = frame[frame["quantile_score"].abs() >= args.min_abs_quantile]

    frame = frame.sort_values("raw_score", key=lambda column: column.abs(), ascending=False)
    rows = frame.to_dict("records")
    if not args.output and len(rows) > 200 and not args.force_stdout:
        raise SystemExit(f"{len(rows)} rows; write them with -o FILE (or pass --force-stdout)")
    common.write_rows(rows, args.output, common.format_from_output(args.output, args.format))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="score_variants.py",
        description="Score variants on demand with the AlphaGenome model (recommended scorers, tidy output).",
        epilog=__doc__.split("Examples:", 1)[-1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--variant", nargs="+", metavar="CHR:POS:REF>ALT", help="one or more variants (1-based)")
    parser.add_argument("--input", metavar="FILE", help="VCF, or TSV/CSV with CHROM/POS/REF/ALT or a 'variant' column")
    parser.add_argument("--scorers", nargs="+", metavar="NAME", help="recommended scorer names (default: all non-ACTIVE); see --list-scorers")
    parser.add_argument("--include-active", action="store_true", help="also run the *_ACTIVE scorers when --scorers is omitted")
    parser.add_argument("--sequence-length", default="1MB", help="16KB, 100KB, 500KB, or 1MB (default 1MB)")
    parser.add_argument("--organism", choices=ORGANISMS, default="human", help="human (hg38) or mouse (mm10)")
    parser.add_argument("--ontology", nargs="+", metavar="CURIE", help="keep tracks with these ontology CURIEs (post-hoc filter)")
    parser.add_argument("--biosample", metavar="TEXT", help="keep tracks whose biosample name contains this text")
    parser.add_argument("--gene", nargs="+", metavar="SYMBOL", help="keep gene-centric rows for these symbols")
    parser.add_argument("--min-abs-quantile", type=float, help="keep rows with |quantile_score| >= this (e.g. 0.99)")
    parser.add_argument("--workers", type=int, default=5, help="parallel requests (default 5)")
    parser.add_argument("--list-scorers", action="store_true", help="print the recommended scorer configurations and exit")
    parser.add_argument("--list-tracks", action="store_true", help="print the model's track metadata (ontology CURIEs, biosamples) and exit")
    parser.add_argument("--output-type", nargs="+", metavar="TYPE", help="with --list-tracks: restrict to output types, e.g. RNA_SEQ DNASE")
    parser.add_argument("--query", metavar="TEXT", help="with --list-tracks: case-insensitive substring filter")
    parser.add_argument("-o", "--output", help="write here instead of stdout (extension picks the format)")
    parser.add_argument("--format", choices=("tsv", "csv", "json", "parquet"), help="override the output format")
    parser.add_argument("--api-key-env", metavar="NAME", help="environment variable holding the key (default: ALPHAGENOME_API_KEY, then ALPHA_GENOME_API_KEY)")
    parser.add_argument("--timeout", type=float, default=30.0, help="seconds to wait for the gRPC channel (default 30)")
    parser.add_argument("--force-stdout", action="store_true", help="print large tables to stdout anyway")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_scorers:
        common.require_alphagenome()
        return list_scorers()
    model = make_model(args)
    if args.list_tracks:
        return list_tracks(model, args)
    return score(model, args)


if __name__ == "__main__":
    sys.exit(main())
