#!/usr/bin/env python3
"""Stream a local SAM/BAM/CRAM file and write aggregate QC counts as JSON.

Counts are alignment-record counts, not unique templates. A whole-file scan
uses fetch(until_eof=True) and needs no index. --region is a 1-based inclusive
samtools region string and requires an index. CRAM requires --reference.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator, Optional

import pysam


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="local SAM/BAM/CRAM file")
    parser.add_argument(
        "--reference",
        type=Path,
        help="local indexed reference FASTA; required for CRAM",
    )
    parser.add_argument(
        "--index",
        type=Path,
        help="explicit local BAI/CSI/CRAI index",
    )
    parser.add_argument(
        "--region",
        help="1-based inclusive samtools region, for example chr1:1-1000000",
    )
    parser.add_argument(
        "--threads",
        type=positive_int,
        default=1,
        help="HTSlib decompression threads",
    )
    parser.add_argument(
        "--max-records",
        type=nonnegative_int,
        default=0,
        help="stop after this many records; 0 scans the complete selection",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write JSON to a new file instead of stdout; refuses overwrite",
    )
    return parser


def require_local_file(path: Path, label: str) -> Path:
    resolved = path.expanduser()
    if not resolved.exists():
        raise FileNotFoundError(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"{label} is not a regular file: {resolved}")
    return resolved


def alignment_mode(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".sam"):
        return "r"
    if name.endswith(".cram"):
        return "rc"
    if name.endswith(".bam"):
        return "rb"
    raise ValueError("input suffix must be .sam, .bam, or .cram")


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return numerator / denominator if denominator else None


def average(total: int, count: int) -> Optional[float]:
    return total / count if count else None


def selected_reads(
    alignments: pysam.AlignmentFile,
    region: Optional[str],
) -> Iterator[pysam.AlignedSegment]:
    if region is None:
        return alignments.fetch(until_eof=True)
    return alignments.fetch(region=region)


def empty_counts() -> dict[str, int]:
    return {
        "total_records": 0,
        "primary_records": 0,
        "mapped_records": 0,
        "unmapped_records": 0,
        "secondary_records": 0,
        "supplementary_records": 0,
        "duplicate_records": 0,
        "qc_fail_records": 0,
        "paired_records": 0,
        "proper_pair_records": 0,
        "read1_records": 0,
        "read2_records": 0,
        "reverse_records": 0,
        "mate_unmapped_records": 0,
        "cigar_missing_records": 0,
        "sequence_missing_records": 0,
        "mapq_255_records": 0,
    }


def inspect_alignments(args: argparse.Namespace) -> dict[str, Any]:
    path = require_local_file(args.input, "input")
    reference = (
        require_local_file(args.reference, "reference")
        if args.reference is not None
        else None
    )
    index = (
        require_local_file(args.index, "index")
        if args.index is not None
        else None
    )
    mode = alignment_mode(path)

    if mode == "rc" and reference is None:
        raise ValueError("CRAM QC requires --reference")

    kwargs: dict[str, Any] = {
        "threads": args.threads,
        "require_index": args.region is not None,
    }
    if reference is not None:
        kwargs["reference_filename"] = str(reference)
    if index is not None:
        kwargs["index_filename"] = str(index)

    counts = empty_counts()
    query_length_sum = 0
    query_length_count = 0
    aligned_query_bases = 0
    mapq_sum = 0
    mapq_count = 0
    record_limit_reached = False

    with pysam.AlignmentFile(str(path), mode, **kwargs) as alignments:
        header = alignments.header.to_dict()
        for read in selected_reads(alignments, args.region):
            if args.max_records and counts["total_records"] >= args.max_records:
                record_limit_reached = True
                break

            counts["total_records"] += 1

            is_primary = not read.is_secondary and not read.is_supplementary
            if is_primary:
                counts["primary_records"] += 1
            if read.is_unmapped:
                counts["unmapped_records"] += 1
            else:
                counts["mapped_records"] += 1
                if read.mapping_quality == 255:
                    counts["mapq_255_records"] += 1
                else:
                    mapq_sum += int(read.mapping_quality)
                    mapq_count += 1
            if read.is_secondary:
                counts["secondary_records"] += 1
            if read.is_supplementary:
                counts["supplementary_records"] += 1
            if read.is_duplicate:
                counts["duplicate_records"] += 1
            if read.is_qcfail:
                counts["qc_fail_records"] += 1
            if read.is_paired:
                counts["paired_records"] += 1
            if read.is_proper_pair:
                counts["proper_pair_records"] += 1
            if read.is_read1:
                counts["read1_records"] += 1
            if read.is_read2:
                counts["read2_records"] += 1
            if read.is_reverse:
                counts["reverse_records"] += 1
            if read.mate_is_unmapped:
                counts["mate_unmapped_records"] += 1
            if read.cigartuples is None:
                counts["cigar_missing_records"] += 1
            if read.query_sequence is None:
                counts["sequence_missing_records"] += 1

            if read.query_length is not None:
                query_length_sum += int(read.query_length)
                query_length_count += 1
            if read.query_alignment_length is not None:
                aligned_query_bases += int(read.query_alignment_length)

        try:
            has_index = bool(alignments.has_index())
        except (AttributeError, OSError, ValueError):
            has_index = False

        report = {
            "schema_version": "1.0",
            "pysam_version": pysam.__version__,
            "samtools_version": getattr(
                pysam, "__samtools_version__", None
            ),
            "file_name": path.name,
            "format": (
                "CRAM"
                if alignments.is_cram
                else "BAM"
                if alignments.is_bam
                else "SAM"
            ),
            "sort_order": header.get("HD", {}).get("SO"),
            "has_index": has_index,
            "selection": {
                "region": args.region,
                "region_coordinate_system": (
                    "1-based inclusive samtools string"
                    if args.region is not None
                    else None
                ),
                "whole_file_order": args.region is None,
                "max_records": args.max_records,
                "record_limit_reached": record_limit_reached,
            },
            "semantics": (
                "Counts are alignment records, not unique query names, "
                "templates, or fragments. MAPQ 255 is reported as unavailable "
                "and excluded from mean_mapping_quality."
            ),
            "counts": counts,
            "derived": {
                "mapping_rate_all_records": ratio(
                    counts["mapped_records"],
                    counts["total_records"],
                ),
                "duplicate_rate_all_records": ratio(
                    counts["duplicate_records"],
                    counts["total_records"],
                ),
                "proper_pair_rate_paired_records": ratio(
                    counts["proper_pair_records"],
                    counts["paired_records"],
                ),
                "mean_query_length": average(
                    query_length_sum,
                    query_length_count,
                ),
                "mean_mapping_quality": average(mapq_sum, mapq_count),
                "aligned_query_bases": aligned_query_bases,
            },
        }
    return report


def write_report(report: dict[str, Any], output: Optional[Path]) -> None:
    text = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    )
    if output is None:
        sys.stdout.write(text + "\n")
        return

    destination = output.expanduser()
    with destination.open("x", encoding="utf-8") as handle:
        handle.write(text + "\n")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.output is not None:
        try:
            if args.output.expanduser().resolve() == args.input.expanduser().resolve():
                parser.error("--output must not overwrite the input file")
        except OSError:
            pass

    try:
        report = inspect_alignments(args)
        write_report(report, args.output)
    except (
        FileExistsError,
        FileNotFoundError,
        IndexError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        print(f"alignment_qc: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
