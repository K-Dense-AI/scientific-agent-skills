#!/usr/bin/env python3
"""Filter a local SAM/BAM/CRAM into a new alignment file.

The script preserves record order and the input header; it does not sort.
Whole-file iteration includes unplaced unmapped records and needs no index.
--region is a 1-based inclusive samtools region and requires an input index.
CRAM input or output requires --reference. Existing outputs are never replaced.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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
    parser.add_argument("input", type=Path, help="local SAM/BAM/CRAM input")
    parser.add_argument("output", type=Path, help="new SAM/BAM/CRAM output")
    parser.add_argument(
        "--reference",
        type=Path,
        help="local indexed reference FASTA; required for CRAM",
    )
    parser.add_argument(
        "--input-index",
        type=Path,
        help="explicit local BAI/CSI/CRAI input index",
    )
    parser.add_argument(
        "--region",
        help="1-based inclusive samtools region, for example chr1:1-1000000",
    )
    parser.add_argument(
        "--min-mapq",
        type=nonnegative_int,
        default=0,
        help="minimum mapping quality; MAPQ 255 passes this numeric threshold",
    )
    parser.add_argument(
        "--exclude-unmapped",
        action="store_true",
        help="exclude unmapped records",
    )
    parser.add_argument(
        "--exclude-secondary",
        action="store_true",
        help="exclude secondary alignments",
    )
    parser.add_argument(
        "--exclude-supplementary",
        action="store_true",
        help="exclude supplementary alignments",
    )
    parser.add_argument(
        "--exclude-duplicates",
        action="store_true",
        help="exclude records marked duplicate",
    )
    parser.add_argument(
        "--exclude-qcfail",
        action="store_true",
        help="exclude records marked QC fail",
    )
    parser.add_argument(
        "--proper-pairs-only",
        action="store_true",
        help="keep only records marked as proper paired alignments",
    )
    parser.add_argument(
        "--threads",
        type=positive_int,
        default=1,
        help="HTSlib compression/decompression threads",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="index output; requires coordinate sort order and BAM/CRAM",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        help="write JSON summary to a new file instead of stdout",
    )
    return parser


def require_local_file(path: Path, label: str) -> Path:
    resolved = path.expanduser()
    if not resolved.exists():
        raise FileNotFoundError(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"{label} is not a regular file: {resolved}")
    return resolved


def alignment_mode(path: Path, *, writing: bool) -> str:
    name = path.name.lower()
    if name.endswith(".sam"):
        return "w" if writing else "r"
    if name.endswith(".bam"):
        return "wb" if writing else "rb"
    if name.endswith(".cram"):
        return "wc" if writing else "rc"
    raise ValueError("alignment suffix must be .sam, .bam, or .cram")


def selected_reads(
    alignments: pysam.AlignmentFile,
    region: Optional[str],
) -> Iterator[pysam.AlignedSegment]:
    if region is None:
        return alignments.fetch(until_eof=True)
    return alignments.fetch(region=region)


def exclusion_reasons(
    read: pysam.AlignedSegment,
    args: argparse.Namespace,
) -> list[str]:
    reasons = []
    if args.exclude_unmapped and read.is_unmapped:
        reasons.append("unmapped")
    if args.exclude_secondary and read.is_secondary:
        reasons.append("secondary")
    if args.exclude_supplementary and read.is_supplementary:
        reasons.append("supplementary")
    if args.exclude_duplicates and read.is_duplicate:
        reasons.append("duplicate")
    if args.exclude_qcfail and read.is_qcfail:
        reasons.append("qc_fail")
    if args.proper_pairs_only and not read.is_proper_pair:
        reasons.append("not_proper_pair")
    if read.mapping_quality < args.min_mapq:
        reasons.append("mapq_below_threshold")
    return reasons


def validate_destinations(
    input_path: Path,
    output_path: Path,
    summary_path: Optional[Path],
) -> None:
    if not output_path.parent.exists():
        raise FileNotFoundError(
            f"output parent does not exist: {output_path.parent}"
        )
    if output_path.exists():
        raise FileExistsError(f"output already exists: {output_path}")
    if input_path.resolve() == output_path.resolve():
        raise ValueError("output must not be the input file")

    if summary_path is not None:
        if not summary_path.parent.exists():
            raise FileNotFoundError(
                f"summary parent does not exist: {summary_path.parent}"
            )
        if summary_path.exists():
            raise FileExistsError(
                f"summary output already exists: {summary_path}"
            )
        if summary_path.resolve() in {
            input_path.resolve(),
            output_path.resolve(),
        }:
            raise ValueError("summary path must differ from input and output")


def filter_file(args: argparse.Namespace) -> dict[str, Any]:
    input_path = require_local_file(args.input, "input")
    output_path = args.output.expanduser()
    summary_path = (
        args.summary.expanduser() if args.summary is not None else None
    )
    validate_destinations(input_path, output_path, summary_path)

    reference = (
        require_local_file(args.reference, "reference")
        if args.reference is not None
        else None
    )
    input_index = (
        require_local_file(args.input_index, "input index")
        if args.input_index is not None
        else None
    )
    input_mode = alignment_mode(input_path, writing=False)
    output_mode = alignment_mode(output_path, writing=True)

    if (input_mode == "rc" or output_mode == "wc") and reference is None:
        raise ValueError("CRAM input or output requires --reference")
    if args.index and output_mode == "w":
        raise ValueError("SAM output cannot be indexed")

    input_kwargs: dict[str, Any] = {
        "threads": args.threads,
        "require_index": args.region is not None,
    }
    if reference is not None:
        input_kwargs["reference_filename"] = str(reference)
    if input_index is not None:
        input_kwargs["index_filename"] = str(input_index)

    output_kwargs: dict[str, Any] = {"threads": args.threads}
    if reference is not None:
        output_kwargs["reference_filename"] = str(reference)

    reason_counts: Counter[str] = Counter()
    selected = 0
    written = 0
    excluded = 0
    sort_order: Optional[str] = None

    try:
        with pysam.AlignmentFile(
            str(input_path),
            input_mode,
            **input_kwargs,
        ) as source:
            sort_order = source.header.to_dict().get("HD", {}).get("SO")
            if args.index and sort_order != "coordinate":
                raise ValueError(
                    "--index requires input header sort order 'coordinate'; "
                    "this script preserves order but does not sort"
                )

            with pysam.AlignmentFile(
                str(output_path),
                output_mode,
                template=source,
                **output_kwargs,
            ) as destination:
                for read in selected_reads(source, args.region):
                    selected += 1
                    reasons = exclusion_reasons(read, args)
                    if reasons:
                        excluded += 1
                        reason_counts.update(reasons)
                        continue
                    destination.write(read)
                    written += 1
    except Exception:
        if output_path.exists():
            output_path.unlink()
        raise

    if args.index:
        pysam.samtools.index(
            "-@",
            str(args.threads),
            str(output_path),
            catch_stdout=False,
        )

    return {
        "schema_version": "1.0",
        "pysam_version": pysam.__version__,
        "samtools_version": getattr(pysam, "__samtools_version__", None),
        "input_file_name": input_path.name,
        "output_file_name": output_path.name,
        "input_mode": input_mode,
        "output_mode": output_mode,
        "sort_order_preserved": sort_order,
        "selection": {
            "region": args.region,
            "region_coordinate_system": (
                "1-based inclusive samtools string"
                if args.region is not None
                else None
            ),
        },
        "filters": {
            "min_mapq": args.min_mapq,
            "exclude_unmapped": args.exclude_unmapped,
            "exclude_secondary": args.exclude_secondary,
            "exclude_supplementary": args.exclude_supplementary,
            "exclude_duplicates": args.exclude_duplicates,
            "exclude_qcfail": args.exclude_qcfail,
            "proper_pairs_only": args.proper_pairs_only,
        },
        "counts": {
            "selected_records": selected,
            "written_records": written,
            "excluded_records": excluded,
            "exclusion_reasons": dict(sorted(reason_counts.items())),
        },
        "indexed_output": args.index,
        "semantics": (
            "Exclusion reason counts can exceed excluded_records because one "
            "record can fail multiple filters. Counts are alignment records."
        ),
    }


def write_summary(
    report: dict[str, Any],
    output: Optional[Path],
) -> None:
    text = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    )
    if output is None:
        sys.stdout.write(text + "\n")
        return
    with output.expanduser().open("x", encoding="utf-8") as handle:
        handle.write(text + "\n")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = filter_file(args)
        write_summary(report, args.summary)
    except (
        FileExistsError,
        FileNotFoundError,
        IndexError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
        pysam.SamtoolsError,
    ) as error:
        print(f"filter_alignments: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
