#!/usr/bin/env python3
"""Preflight local Gtars uniwig coverage and bigWig generation."""

from __future__ import annotations

import argparse
import math
import sys

from _common import (
    HARD_MAX_BYTES,
    HARD_MAX_RECORDS,
    HARD_MAX_WORKERS,
    SafetyError,
    add_path_mode_argument,
    display_path,
    fail_json,
    inspect_bed,
    int_type,
    load_chrom_sizes,
    local_path,
    print_json,
    prefix_collision_count,
    sha256_file,
)


TOOL = "gtars-coverage-preflight"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check a sorted local BED/narrowPeak input, chromosome sizes, bounds, "
            "and output budget for gtars uniwig 0.10.0. Nothing is generated."
        )
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--input-type", choices=("bed", "narrowpeak"), default="bed")
    parser.add_argument("--chrom-sizes", required=True)
    parser.add_argument("--assembly", required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument(
        "--output-type",
        choices=("bw", "wig", "bedgraph", "npy"),
        default="bw",
    )
    parser.add_argument(
        "--count-type",
        choices=("start", "end", "core", "all"),
        default="core",
    )
    parser.add_argument(
        "--smooth-size",
        type=int_type(minimum=1, maximum=10_000_000, label="smooth-size"),
        default=5,
    )
    parser.add_argument(
        "--step-size",
        type=int_type(minimum=1, maximum=10_000_000, label="step-size"),
        default=1,
    )
    parser.add_argument(
        "--threads",
        type=int_type(minimum=1, maximum=HARD_MAX_WORKERS, label="threads"),
        default=1,
    )
    parser.add_argument(
        "--zoom",
        type=int_type(minimum=0, maximum=10_000, label="zoom"),
        default=1,
    )
    parser.add_argument(
        "--streaming",
        action="store_true",
        help="Use BED streaming; only wig/bedgraph output is supported upstream.",
    )
    parser.add_argument(
        "--dense",
        type=int_type(minimum=-1, maximum=MAX_DENSE_GAP, label="dense"),
        default=100,
        help="Streaming gap fill: 0 sparse, -1 fully dense, N fills gaps <=N.",
    )
    parser.add_argument(
        "--max-bytes",
        type=int_type(minimum=1, maximum=HARD_MAX_BYTES, label="max-bytes"),
        default=2 * 1024**3,
    )
    parser.add_argument(
        "--max-records",
        type=int_type(
            minimum=1,
            maximum=HARD_MAX_RECORDS,
            label="max-records",
        ),
        default=5_000_000,
    )
    parser.add_argument(
        "--max-estimated-bytes",
        type=int_type(
            minimum=1,
            maximum=HARD_MAX_BYTES,
            label="max-estimated-bytes",
        ),
        default=4 * 1024**3,
        help="Planning cap for dense uncompressed coverage values.",
    )
    add_path_mode_argument(parser)
    return parser


MAX_DENSE_GAP = 10_000_000


def preflight(args: argparse.Namespace) -> tuple[dict, int]:
    assembly = args.assembly.strip()
    if not assembly or len(assembly) > 200:
        raise SafetyError("assembly must contain 1-200 characters")
    input_path = local_path(args.input, kind="file")
    chrom_path = local_path(args.chrom_sizes, kind="file")
    output_prefix = local_path(args.output_prefix, must_exist=False)

    chrom_sizes, chrom_order = load_chrom_sizes(
        chrom_path,
        max_bytes=min(args.max_bytes, 128 * 1024**2),
        max_records=min(args.max_records, 1_000_000),
    )
    chrom_digest, chrom_bytes = sha256_file(
        chrom_path,
        max_bytes=min(args.max_bytes, 128 * 1024**2),
    )
    bed = inspect_bed(
        input_path,
        max_bytes=args.max_bytes,
        max_records=args.max_records,
        chrom_sizes=chrom_sizes,
        chrom_order=chrom_order,
    )
    errors: dict[str, int] = dict(bed["errors"])
    warnings: dict[str, int] = {}
    if bed["records"] == 0:
        errors["no_data_records"] = 1
    if bed["out_of_order_records"]:
        errors["sorting_required"] = bed["out_of_order_records"]
    if args.input_type == "narrowpeak" and (bed["minimum_columns"] or 0) < 10:
        errors["narrowpeak_requires_ten_columns"] = 1
    if output_prefix.exists():
        errors["output_prefix_already_exists"] = 1
    collisions = prefix_collision_count(output_prefix)
    if collisions:
        errors["output_prefix_collisions"] = collisions
    if args.streaming and args.output_type not in {"wig", "bedgraph"}:
        errors["streaming_output_type_unsupported"] = 1
    if args.streaming and args.input_type != "bed":
        errors["streaming_requires_bed_input"] = 1

    count_outputs = 3 if args.count_type == "all" else 1
    genome_span = sum(chrom_sizes.values())
    estimated_values = sum(
        math.ceil(length / args.step_size) for length in chrom_sizes.values()
    ) * count_outputs
    estimated_uncompressed_bytes = estimated_values * 8
    if estimated_uncompressed_bytes > args.max_estimated_bytes:
        errors["estimated_dense_coverage_exceeds_budget"] = 1
    if args.threads > 1:
        warnings["parallel_memory_may_scale_with_threads"] = args.threads
    if args.output_type == "bw":
        warnings["bigwig_size_is_data_dependent_estimate_is_not_file_size"] = 1
    if args.streaming and args.dense == -1:
        warnings["fully_dense_streaming_requested"] = 1

    argv = [
        "gtars",
        "uniwig",
        "--file",
        "<input>",
        "--filetype",
        args.input_type,
        "--chromref",
        "<chrom-sizes>",
        "--smoothsize",
        str(args.smooth_size),
        "--stepsize",
        str(args.step_size),
        "--fileheader",
        "<output-prefix>",
        "--outputtype",
        args.output_type,
        "--counttype",
        args.count_type,
    ]
    if args.streaming:
        argv.extend(["--streaming", "--dense", str(args.dense)])
    else:
        argv.extend(["--threads", str(args.threads), "--zoom", str(args.zoom)])

    report = {
        "ok": not errors,
        "ready_to_execute": not errors,
        "tool": TOOL,
        "contract": {
            "assembly": assembly,
            "coordinate_system": "0-based-half-open",
            "gtars_cli_version": "0.10.0",
            "commands_executed": False,
            "files_written": False,
            "network_used": False,
            "symlinks_allowed": False,
        },
        "input": {
            "path": display_path(input_path, 1, args.path_mode),
            "sha256": bed["sha256"],
            "size_bytes": bed["size_bytes"],
            "records": bed["records"],
            "minimum_columns": bed["minimum_columns"],
            "out_of_order_records": bed["out_of_order_records"],
        },
        "chromosome_sizes": {
            "path": display_path(chrom_path, 2, args.path_mode),
            "sha256": chrom_digest,
            "size_bytes": chrom_bytes,
            "contig_count": len(chrom_sizes),
            "total_span": genome_span,
        },
        "output": {
            "prefix": display_path(output_prefix, 3, args.path_mode),
            "type": args.output_type,
            "count_type": args.count_type,
        },
        "resource_estimate": {
            "step_size": args.step_size,
            "count_outputs": count_outputs,
            "dense_value_upper_bound": estimated_values,
            "uncompressed_bytes_proxy": estimated_uncompressed_bytes,
            "budget_bytes": args.max_estimated_bytes,
            "not_a_bigwig_size_prediction": True,
        },
        "errors": dict(sorted(errors.items())),
        "warnings": dict(sorted(warnings.items())),
        "argv_template": argv,
        "approval_gate": [
            "review the sorted/bounds report and assembly checksum",
            "pilot one bounded contig or small synthetic BED first",
            "set CPU, RAM, disk, and wall-time limits before running",
            "inspect the resulting bigWig header and chromosome dictionary",
        ],
    }
    return report, 0 if not errors else 2


def main() -> int:
    args = build_parser().parse_args()
    try:
        report, status = preflight(args)
        print_json(report)
        return status
    except (OSError, SafetyError, UnicodeError) as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
