#!/usr/bin/env python3
"""Validate one local BED file and emit a non-mutating normalization plan."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

from _common import (
    HARD_MAX_BYTES,
    HARD_MAX_RECORDS,
    MAX_COORDINATE,
    SafetyError,
    add_path_mode_argument,
    display_path,
    fail_json,
    int_type,
    iter_text_lines,
    load_chrom_sizes,
    local_path,
    print_json,
    sha256_file,
)


TOOL = "bed-validator"
_DECIMAL = re.compile(r"^-?[0-9]+$")
_VALID_STRANDS = {"+", "-", "."}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a local BED file as 0-based half-open intervals and emit "
            "a bounded normalization plan. The input is never rewritten."
        )
    )
    parser.add_argument("--input", required=True, help="Local BED or BED.GZ file.")
    parser.add_argument(
        "--assembly",
        required=True,
        help="Declared assembly/accession recorded in the report.",
    )
    parser.add_argument(
        "--chrom-sizes",
        help="Optional local two-column chromosome-sizes file for contig/bounds checks.",
    )
    parser.add_argument(
        "--max-bytes",
        type=int_type(minimum=1, maximum=HARD_MAX_BYTES, label="max-bytes"),
        default=512 * 1024**2,
        help="Maximum compressed and expanded input bytes (default: 512 MiB).",
    )
    parser.add_argument(
        "--max-records",
        type=int_type(minimum=1, maximum=HARD_MAX_RECORDS, label="max-records"),
        default=1_000_000,
        help="Maximum text records, including headers (default: 1,000,000).",
    )
    parser.add_argument(
        "--max-examples",
        type=int_type(minimum=0, maximum=100, label="max-examples"),
        default=10,
        help="Maximum redacted issue examples (default: 10).",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Do not treat a BED with zero data records as an error.",
    )
    add_path_mode_argument(parser)
    return parser


def _record_issue(
    counter: Counter[str],
    examples: list[dict[str, int | str]],
    code: str,
    line_number: int,
    maximum: int,
) -> None:
    counter[code] += 1
    if len(examples) < maximum:
        examples.append({"code": code, "line": line_number})


def validate(args: argparse.Namespace) -> tuple[dict, int]:
    if not args.assembly.strip() or len(args.assembly) > 200:
        raise SafetyError("assembly must be a nonempty value of at most 200 characters")

    bed_path = local_path(args.input, kind="file")
    chrom_sizes: dict[str, int] | None = None
    chrom_order: dict[str, int] | None = None
    chrom_sizes_digest: str | None = None
    if args.chrom_sizes:
        chrom_path = local_path(args.chrom_sizes, kind="file")
        sizes, order = load_chrom_sizes(
            chrom_path,
            max_bytes=min(args.max_bytes, 128 * 1024**2),
            max_records=min(args.max_records, 1_000_000),
        )
        chrom_sizes = sizes
        chrom_order = {chrom: index for index, chrom in enumerate(order)}
        chrom_sizes_digest, _ = sha256_file(
            chrom_path,
            max_bytes=min(args.max_bytes, 128 * 1024**2),
        )

    errors: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    examples: list[dict[str, int | str]] = []
    records = 0
    skipped = 0
    min_columns: int | None = None
    max_columns = 0
    contigs: set[str] = set()
    seen: set[tuple[str, int, int]] = set()
    duplicate_count = 0
    previous_sort_key: tuple[int | str, int, int] | None = None
    unsorted_count = 0
    strand_rows = 0

    for line_number, line in iter_text_lines(
        bed_path,
        max_bytes=args.max_bytes,
        max_records=args.max_records,
    ):
        if not line:
            skipped += 1
            warnings["blank_line"] += 1
            continue
        if line.startswith("#") or line.startswith("track") or line.startswith("browser"):
            skipped += 1
            continue

        fields = line.split("\t")
        if len(fields) < 3:
            _record_issue(
                errors,
                examples,
                "fewer_than_three_columns",
                line_number,
                args.max_examples,
            )
            continue
        records += 1
        min_columns = len(fields) if min_columns is None else min(min_columns, len(fields))
        max_columns = max(max_columns, len(fields))

        chrom = fields[0]
        if not chrom or any(character.isspace() or ord(character) < 32 for character in chrom):
            _record_issue(
                errors,
                examples,
                "invalid_contig",
                line_number,
                args.max_examples,
            )
            continue

        start_text, end_text = fields[1], fields[2]
        if not _DECIMAL.fullmatch(start_text) or not _DECIMAL.fullmatch(end_text):
            _record_issue(
                errors,
                examples,
                "non_decimal_coordinate",
                line_number,
                args.max_examples,
            )
            continue
        start, end = int(start_text), int(end_text)
        if start < 0 or end < 0:
            _record_issue(
                errors,
                examples,
                "negative_coordinate",
                line_number,
                args.max_examples,
            )
            continue
        if start > MAX_COORDINATE or end > MAX_COORDINATE:
            _record_issue(
                errors,
                examples,
                "coordinate_integer_overflow",
                line_number,
                args.max_examples,
            )
            continue
        if end == start:
            _record_issue(
                errors,
                examples,
                "zero_length_interval",
                line_number,
                args.max_examples,
            )
            continue
        if end < start:
            _record_issue(
                errors,
                examples,
                "end_before_start",
                line_number,
                args.max_examples,
            )
            continue

        if chrom_sizes is not None:
            if chrom not in chrom_sizes:
                _record_issue(
                    errors,
                    examples,
                    "unknown_contig",
                    line_number,
                    args.max_examples,
                )
                continue
            if end > chrom_sizes[chrom]:
                _record_issue(
                    errors,
                    examples,
                    "end_beyond_contig",
                    line_number,
                    args.max_examples,
                )
                continue

        if len(fields) >= 6:
            strand_rows += 1
            if fields[5] not in _VALID_STRANDS:
                _record_issue(
                    errors,
                    examples,
                    "invalid_bed6_strand",
                    line_number,
                    args.max_examples,
                )

        contigs.add(chrom)
        key = (chrom, start, end)
        if key in seen:
            duplicate_count += 1
        else:
            seen.add(key)

        if chrom_order is None:
            sort_key: tuple[int | str, int, int] = (chrom, start, end)
        else:
            sort_key = (chrom_order[chrom], start, end)
        if previous_sort_key is not None and sort_key < previous_sort_key:
            unsorted_count += 1
        previous_sort_key = sort_key

    # Sweep in coordinate order without rewriting the input. Reuse the unique
    # intervals already retained for duplicate detection; every duplicate also
    # contributes one overlap observation, as it does in a sorted BED.
    overlap_count = duplicate_count
    max_end_by_contig: dict[str, int] = {}
    for chrom, start, end in sorted(seen):
        prior_end = max_end_by_contig.get(chrom)
        if prior_end is not None and start < prior_end:
            overlap_count += 1
        max_end_by_contig[chrom] = max(end, prior_end or end)

    if records == 0 and not args.allow_empty:
        errors["no_data_records"] += 1
    if chrom_sizes is None:
        warnings["bounds_not_checked_without_chrom_sizes"] += 1
    if unsorted_count:
        warnings["out_of_order_records"] = unsorted_count
    if duplicate_count:
        warnings["duplicate_intervals"] = duplicate_count
    if overlap_count:
        warnings["overlapping_intervals"] = overlap_count

    digest, size = sha256_file(bed_path, max_bytes=args.max_bytes)
    actions: list[dict[str, str | int]] = []
    if errors:
        actions.append(
            {
                "action": "reject_or_quarantine_invalid_rows",
                "count": sum(errors.values()),
            }
        )
    if unsorted_count:
        actions.append(
            {
                "action": "stable_sort",
                "detail": (
                    "use chromosome-sizes order, then numeric start/end"
                    if chrom_order is not None
                    else "supply chromosome sizes before choosing contig order"
                ),
            }
        )
    if duplicate_count:
        actions.append(
            {
                "action": "decide_duplicate_policy",
                "count": duplicate_count,
            }
        )
    if chrom_sizes is None:
        actions.append(
            {
                "action": "supply_chromosome_sizes",
                "detail": "required before overflow/contig normalization",
            }
        )
    actions.append(
        {
            "action": "preserve_coordinate_semantics",
            "detail": "BED 0-based half-open; no implicit liftover or chr renaming",
        }
    )

    report = {
        "ok": not errors,
        "tool": TOOL,
        "contract": {
            "assembly": args.assembly,
            "coordinate_system": "0-based-half-open",
            "input_mutated": False,
            "network_used": False,
        },
        "input": {
            "path": display_path(bed_path, 1, args.path_mode),
            "sha256": digest,
            "size_bytes": size,
        },
        "chromosome_sizes_sha256": chrom_sizes_digest,
        "summary": {
            "records": records,
            "skipped_header_or_blank_lines": skipped,
            "contig_count": len(contigs),
            "minimum_columns": min_columns,
            "maximum_columns": max_columns if records else None,
            "bed6_or_wider_rows": strand_rows,
            "duplicate_intervals": duplicate_count,
            "overlap_observations": overlap_count,
            "out_of_order_records": unsorted_count,
        },
        "errors": dict(sorted(errors.items())),
        "warnings": dict(sorted(warnings.items())),
        "issue_examples": examples,
        "normalization_plan": actions,
    }
    return report, 0 if not errors else 2


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        report, exit_code = validate(args)
        print_json(report)
        return exit_code
    except (OSError, SafetyError, UnicodeError) as exc:
        return fail_json(TOOL, exc)


if __name__ == "__main__":
    sys.exit(main())
