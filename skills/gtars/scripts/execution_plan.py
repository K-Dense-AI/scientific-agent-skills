#!/usr/bin/env python3
"""Build a bounded local Gtars overlap/coverage execution plan."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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


TOOL = "gtars-execution-plan"
GTARS_CLI_VERSION = "0.10.0"
GTARS_PYTHON_VERSION = "0.10.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate local inputs and emit a fixed Gtars 0.10 execution plan. "
            "The helper never imports gtars or runs a subprocess."
        )
    )
    parser.add_argument(
        "--operation",
        required=True,
        choices=("overlap", "count", "coverage", "consensus", "fragment-score"),
    )
    parser.add_argument("--assembly", required=True)
    parser.add_argument("--query", help="Query BED or fragment file.")
    parser.add_argument("--universe", help="Universe/consensus BED file.")
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Consensus input BED; repeat at least twice.",
    )
    parser.add_argument("--chrom-sizes", help="Local chromosome-sizes file.")
    parser.add_argument("--output", help="Planned local output or output prefix.")
    parser.add_argument("--backend", choices=("bits", "ailist"), default="bits")
    parser.add_argument(
        "--coverage-format",
        choices=("bw", "wig", "bedgraph", "npy"),
        default="bw",
    )
    parser.add_argument(
        "--coverage-streaming",
        action="store_true",
        help="Plan BED streaming; only wig/bedgraph output is supported.",
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
        "--count-type",
        choices=("start", "end", "core", "all"),
        default="core",
    )
    parser.add_argument(
        "--threads",
        type=int_type(minimum=1, maximum=HARD_MAX_WORKERS, label="threads"),
        default=1,
    )
    parser.add_argument(
        "--min-count",
        type=int_type(minimum=1, maximum=1_000_000, label="min-count"),
        default=1,
    )
    parser.add_argument("--scoring-mode", choices=("atac", "chip"), default="atac")
    parser.add_argument(
        "--barcode",
        action="store_true",
        help="Plan fscoring sparse barcode mode.",
    )
    parser.add_argument(
        "--max-bytes",
        type=int_type(minimum=1, maximum=HARD_MAX_BYTES, label="max-bytes"),
        default=1024**3,
    )
    parser.add_argument(
        "--max-records",
        type=int_type(
            minimum=1,
            maximum=HARD_MAX_RECORDS,
            label="max-records",
        ),
        default=2_000_000,
    )
    add_path_mode_argument(parser)
    return parser


def _require(value: str | None, option: str) -> str:
    if value is None:
        raise SafetyError(f"{option} is required for this operation")
    return value


def _output(raw: str | None) -> Path:
    return local_path(_require(raw, "--output"), must_exist=False)


def build_plan(args: argparse.Namespace) -> tuple[dict, int]:
    assembly = args.assembly.strip()
    if not assembly or len(assembly) > 200:
        raise SafetyError("assembly must contain 1-200 characters")

    chrom_sizes = None
    chrom_order = None
    chrom_report = None
    if args.chrom_sizes:
        chrom_path = local_path(args.chrom_sizes, kind="file")
        chrom_sizes, chrom_order = load_chrom_sizes(
            chrom_path,
            max_bytes=min(args.max_bytes, 128 * 1024**2),
            max_records=min(args.max_records, 1_000_000),
        )
        digest, size = sha256_file(
            chrom_path,
            max_bytes=min(args.max_bytes, 128 * 1024**2),
        )
        chrom_report = {
            "path": display_path(chrom_path, 1, args.path_mode),
            "sha256": digest,
            "size_bytes": size,
            "contig_count": len(chrom_sizes),
        }

    inputs: list[dict] = []
    errors: dict[str, int] = {}
    next_index = 2

    def add_bed(raw: str, role: str, *, sorted_required: bool = False) -> Path:
        nonlocal next_index
        path = local_path(raw, kind="file")
        summary = inspect_bed(
            path,
            max_bytes=args.max_bytes,
            max_records=args.max_records,
            chrom_sizes=chrom_sizes,
            chrom_order=chrom_order,
        )
        for code, count in summary["errors"].items():
            errors[f"{role}:{code}"] = count
        if summary["records"] == 0:
            errors[f"{role}:no_data_records"] = 1
        if args.operation == "overlap" and summary["skipped_records"]:
            errors[f"{role}:cli_overlap_requires_header_free_bed"] = summary[
                "skipped_records"
            ]
        if args.operation == "fragment-score" and role == "consensus" and summary["duplicate_intervals"]:
            errors["consensus:duplicate_intervals"] = summary["duplicate_intervals"]
        if sorted_required and summary["out_of_order_records"]:
            errors[f"{role}:sorting_required"] = summary["out_of_order_records"]
        inputs.append(
            {
                "role": role,
                "path": display_path(path, next_index, args.path_mode),
                "sha256": summary["sha256"],
                "size_bytes": summary["size_bytes"],
                "records": summary["records"],
                "minimum_columns": summary["minimum_columns"],
                "out_of_order_records": summary["out_of_order_records"],
            }
        )
        next_index += 1
        return path

    operation = args.operation
    plan: dict[str, object]
    output_report = None

    if operation in {"overlap", "count"}:
        add_bed(_require(args.query, "--query"), "query")
        add_bed(_require(args.universe, "--universe"), "universe")
        if operation == "overlap":
            plan = {
                "interface": "cli",
                "argv_template": [
                    "gtars",
                    "overlaprs",
                    "--query",
                    "<query-bed>",
                    "--universe",
                    "<universe-bed>",
                    "--backend",
                    args.backend,
                ],
                "stdout": (
                    "one BED3 universe-hit row per overlap; query IDs and counts "
                    "are not emitted"
                ),
            }
        else:
            plan = {
                "interface": "python",
                "imports": ["from gtars.models import RegionSet"],
                "call": "query.count_overlaps(universe)",
                "return": "one integer per query region",
            }
    elif operation == "coverage":
        if chrom_sizes is None:
            raise SafetyError("--chrom-sizes is required for coverage")
        add_bed(_require(args.query, "--query"), "coverage_input", sorted_required=True)
        out = _output(args.output)
        output_report = {
            "path": display_path(out, next_index, args.path_mode),
            "already_exists": out.exists(),
        }
        if out.exists():
            errors["output_already_exists"] = 1
        collisions = prefix_collision_count(out)
        if collisions:
            errors["output_prefix_collisions"] = collisions
        if args.coverage_streaming and args.coverage_format not in {"wig", "bedgraph"}:
            raise SafetyError(
                "streaming coverage supports only wig or bedgraph, not bw/npy"
            )
        argv = [
            "gtars",
            "uniwig",
            "--file",
            "<coverage-input>",
            "--filetype",
            "bed",
            "--chromref",
            "<chrom-sizes>",
            "--smoothsize",
            str(args.smooth_size),
            "--stepsize",
            str(args.step_size),
            "--fileheader",
            "<output-prefix>",
            "--outputtype",
            args.coverage_format,
            "--counttype",
            args.count_type,
        ]
        if args.coverage_streaming:
            argv.append("--streaming")
        else:
            argv.extend(["--threads", str(args.threads)])
        plan = {
            "interface": "cli",
            "argv_template": argv,
            "note": (
                "batch mode is required for bigWig; run coverage_preflight.py "
                "before approval"
            ),
        }
    elif operation == "consensus":
        if len(args.input) < 2:
            raise SafetyError("consensus requires at least two --input BED files")
        if args.min_count > len(args.input):
            raise SafetyError("--min-count cannot exceed the number of input sets")
        for index, raw in enumerate(args.input, start=1):
            add_bed(raw, f"consensus_{index}")
        out = _output(args.output)
        output_report = {
            "path": display_path(out, next_index, args.path_mode),
            "already_exists": out.exists(),
        }
        if out.exists():
            errors["output_already_exists"] = 1
        plan = {
            "interface": "cli",
            "argv_template": [
                "gtars",
                "consensus",
                "--beds",
                *[f"<bed-{index}>" for index in range(1, len(args.input) + 1)],
                "--min-count",
                str(args.min_count),
                "--output",
                "<output-bed>",
            ],
            "semantics": (
                "reduce the union (including adjacent intervals), then count "
                "input sets having any overlap with each union interval"
            ),
        }
    else:
        if not args.barcode and args.scoring_mode == "atac":
            # gtars-scoring 0.5.2 in the CLI 0.10.0 lockfile constructs its
            # right-cut query with end < start. Do not green-light those counts.
            errors["upstream_atac_right_cut_interval_invalid"] = 1
        fragment = add_bed(_require(args.query, "--query"), "fragments")
        add_bed(_require(args.universe, "--universe"), "consensus")
        fragment_summary = next(item for item in inputs if item["role"] == "fragments")
        if (fragment_summary["minimum_columns"] or 0) < 5:
            errors["fragments:fewer_than_five_columns"] = 1
        out = _output(args.output)
        output_report = {
            "path": display_path(out, next_index, args.path_mode),
            "already_exists": out.exists(),
        }
        if out.exists():
            errors["output_already_exists"] = 1
        argv = [
            "gtars",
            "fscoring",
            "<fragment-file>",
            "<consensus-bed>",
            "--output",
            "<output-or-prefix>",
        ]
        if args.barcode:
            collisions = prefix_collision_count(out)
            if collisions:
                errors["output_prefix_collisions"] = collisions
            argv.append("--barcode")
        else:
            argv.extend(["--mode", args.scoring_mode])
        plan = {
            "interface": "cli",
            "argv_template": argv,
            "fragment_input_is_single_local_file": fragment.is_file(),
        }

    report = {
        "ok": not errors,
        "ready_to_execute": not errors,
        "tool": TOOL,
        "contract": {
            "assembly": assembly,
            "coordinate_system": "0-based-half-open",
            "gtars_cli_version": GTARS_CLI_VERSION,
            "gtars_python_version": GTARS_PYTHON_VERSION,
            "commands_executed": False,
            "packages_imported": False,
            "network_used": False,
            "files_written": False,
            "symlinks_allowed": False,
        },
        "operation": operation,
        "chromosome_sizes": chrom_report,
        "inputs": inputs,
        "output": output_report,
        "errors": errors,
        "execution_plan": plan,
        "approval_gate": [
            "review checksums, assembly, contigs, sorting, and output collision",
            "set CPU, RAM, disk, file-count, and wall-time limits",
            "run only the exact pinned interface after explicit approval",
        ],
    }
    return report, 0 if not errors else 2


def main() -> int:
    args = build_parser().parse_args()
    try:
        report, status = build_plan(args)
        print_json(report)
        return status
    except (OSError, SafetyError, UnicodeError) as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
