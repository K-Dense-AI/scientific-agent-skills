#!/usr/bin/env python3
"""Generate disclosure-controlled tables from bounded aggregate cohort summaries."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from typing import Any

from _common import (
    InputError,
    IssueLog,
    load_json_object,
    nonnegative_int,
    require_list,
    require_nonempty_text,
    write_text,
)

MAX_GROUPS = 12
MAX_ROWS = 200


def _format_count(count: int, denominator: int) -> str:
    percentage = 100.0 * (count / denominator) if denominator else 0.0
    return f"{count}/{denominator} ({percentage:.1f}%)"


def _build_table(
    document: dict[str, Any], minimum: int
) -> tuple[IssueLog, list[str], list[list[str]], list[str]]:
    log = IssueLog()
    notes: list[str] = []
    headers: list[str] = ["Characteristic"]
    output_rows: list[list[str]] = []

    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        raise InputError("metadata must be an object")
    for field in ("table_id", "title", "purpose", "population", "data_cut_date"):
        require_nonempty_text(metadata.get(field), f"metadata.{field}")
    if not isinstance(metadata.get("data_level"), str) or metadata.get("data_level") not in {"aggregate", "synthetic"}:
        log.errors.append("metadata.data_level must be aggregate or synthetic")
    if metadata.get("raw_rows_supplied") is not False:
        log.errors.append("metadata.raw_rows_supplied must be false")
    if metadata.get("patient_care_use") is not False:
        log.errors.append("metadata.patient_care_use must be false")
    require_nonempty_text(
        metadata.get("disclosure_policy"), "metadata.disclosure_policy"
    )
    require_nonempty_text(
        metadata.get("human_review"), "metadata.human_review"
    )

    review = document.get("human_review")
    if not isinstance(review, dict):
        raise InputError("human_review must be an object")
    if review.get("required") is not True:
        log.errors.append("human_review.required must be true")
    roles = require_list(review.get("roles"), "human_review.roles", maximum=20)
    if not roles:
        log.errors.append("At least one human-review role is required")
    for index, role in enumerate(roles):
        require_nonempty_text(role, f"human_review.roles[{index}]")
    if review.get("completed") is not True:
        log.warnings.append("Human review is not recorded as complete")

    governance = document.get("governance")
    if not isinstance(governance, dict):
        raise InputError("governance must be an object")
    for field in (
        "version",
        "owner",
        "change_summary",
        "auditability",
        "monitoring",
    ):
        require_nonempty_text(governance.get(field), f"governance.{field}")

    if not log.ok:
        return log, headers, output_rows, notes

    groups = require_list(document.get("groups"), "groups", maximum=MAX_GROUPS)
    if not groups:
        raise InputError("At least one group is required")
    group_map: dict[str, dict[str, Any]] = {}
    for index, group in enumerate(groups):
        field = f"groups[{index}]"
        if not isinstance(group, dict):
            raise InputError(f"{field} must be an object")
        identifier = require_nonempty_text(
            group.get("id"), f"{field}.id", max_length=50
        )
        label = require_nonempty_text(
            group.get("label"), f"{field}.label", max_length=120
        )
        n = nonnegative_int(group.get("n"), f"{field}.n")
        if n == 0:
            raise InputError(f"{field}.n must be positive")
        if identifier in group_map:
            raise InputError(f"Duplicate group id: {identifier}")
        group_map[identifier] = {"label": label, "n": n}
        headers.append(f"{label} (n={n if n >= minimum else 'SUPP'})")

    rows = require_list(document.get("rows"), "rows", maximum=MAX_ROWS)
    if not rows:
        raise InputError("At least one aggregate table row is required")
    for row_index, row in enumerate(rows):
        field = f"rows[{row_index}]"
        if not isinstance(row, dict):
            raise InputError(f"{field} must be an object")
        if "p_value" in row or "statistical_test" in row:
            raise InputError(
                f"{field} contains inferential fields; this helper creates descriptive tables only"
            )
        label = require_nonempty_text(row.get("label"), f"{field}.label", max_length=200)
        level = row.get("level")
        if level is not None:
            label = f"  {require_nonempty_text(level, f'{field}.level', max_length=120)}"
        row_type = require_nonempty_text(
            row.get("type"), f"{field}.type", max_length=30
        )
        if row_type not in {"categorical", "continuous", "header"}:
            raise InputError(f"{field}.type is unsupported")
        values = row.get("values")
        if row_type == "header":
            output_rows.append([label] + [""] * len(group_map))
            continue
        if not isinstance(values, dict):
            raise InputError(f"{field}.values must be an object")
        if set(values) != set(group_map):
            raise InputError(f"{field}.values must contain exactly all group ids")

        cells: dict[str, str] = {}
        primary_suppressed: set[str] = set()
        eligible_counts: dict[str, int] = {}
        for group_id, group in group_map.items():
            value = values[group_id]
            cell_field = f"{field}.values.{group_id}"
            if not isinstance(value, dict):
                raise InputError(f"{cell_field} must be an object")
            group_n = group["n"]
            if row_type == "categorical":
                count = nonnegative_int(value.get("count"), f"{cell_field}.count")
                denominator = nonnegative_int(
                    value.get("denominator"), f"{cell_field}.denominator"
                )
                missing = nonnegative_int(
                    value.get("missing", group_n - denominator),
                    f"{cell_field}.missing",
                )
                if denominator == 0 or count > denominator:
                    raise InputError(f"{cell_field} has inconsistent counts")
                if denominator + missing != group_n:
                    raise InputError(
                        f"{cell_field} denominator plus missing must equal group n"
                    )
                if (
                    group_n < minimum
                    or 0 < count < minimum
                    or 0 < denominator - count < minimum
                    or 0 < missing < minimum
                ):
                    cells[group_id] = "SUPP"
                    primary_suppressed.add(group_id)
                else:
                    cells[group_id] = _format_count(count, denominator)
                    eligible_counts[group_id] = count
            else:
                summarized_n = nonnegative_int(value.get("n"), f"{cell_field}.n")
                missing = nonnegative_int(
                    value.get("missing", group_n - summarized_n),
                    f"{cell_field}.missing",
                )
                if summarized_n + missing != group_n:
                    raise InputError(
                        f"{cell_field} n plus missing must equal group n"
                    )
                summary = require_nonempty_text(
                    value.get("summary"), f"{cell_field}.summary", max_length=120
                )
                if group_n < minimum or summarized_n < minimum or 0 < missing < minimum:
                    cells[group_id] = "SUPP"
                    primary_suppressed.add(group_id)
                else:
                    cells[group_id] = f"{summary}; n={summarized_n}"

        if (
            row_type == "categorical"
            and len(primary_suppressed) == 1
            and eligible_counts
        ):
            complementary = min(eligible_counts, key=eligible_counts.get)
            cells[complementary] = "SUPP-C"
            notes.append(
                f"Complementary suppression applied to row {row_index + 1}."
            )
        output_rows.append([label] + [cells[group_id] for group_id in group_map])

    notes.extend(
        [
            f"Cells use a minimum threshold of {minimum}. SUPP is primary suppression; SUPP-C is complementary suppression.",
            "Thresholding is an operational disclosure control, not a HIPAA or privacy determination.",
            "Descriptive aggregate table only; no patient-specific or clinical recommendation output.",
            "Not for patient care or live clinical use.",
        ]
    )
    if log.ok:
        log.info.append("Disclosure-controlled aggregate table generated")
    return log, headers, output_rows, notes


def _to_markdown(
    title: str, headers: list[str], rows: list[list[str]], notes: list[str]
) -> str:
    lines = [
        f"# {title}",
        "",
        "**Research aggregate only — not for patient care or live clinical use.**",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    lines.extend(["", "## Disclosure notes"])
    lines.extend(f"- {note}" for note in notes)
    return "\n".join(lines) + "\n"


def _to_csv(headers: list[str], rows: list[list[str]], notes: list[str]) -> str:
    def safe_cell(value: str) -> str:
        # Treat labels/summaries as text when opened by a spreadsheet program.
        if value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow([safe_cell(value) for value in headers])
    writer.writerows([safe_cell(value) for value in row] for row in rows)
    writer.writerow([])
    writer.writerow(["Disclosure notes"])
    for note in notes:
        writer.writerow([note])
    return stream.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a bounded descriptive cohort table from local aggregate JSON "
            "with primary and complementary disclosure suppression."
        )
    )
    parser.add_argument("input", help="Local aggregate JSON")
    parser.add_argument("-o", "--output", help="Optional .md or .csv output")
    parser.add_argument(
        "--min-cell-size",
        type=int,
        default=11,
        help="Operational suppression threshold (default: 11; not a legal standard)",
    )
    args = parser.parse_args()
    if not 2 <= args.min_cell_size <= 1_000:
        parser.error("--min-cell-size must be between 2 and 1000")

    try:
        document = load_json_object(args.input)
        log, headers, rows, notes = _build_table(document, args.min_cell_size)
        if log.errors:
            for error in log.errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        title = require_nonempty_text(document["metadata"].get("title"), "metadata.title")
        if args.output:
            if args.output.lower().endswith(".csv"):
                text = _to_csv(headers, rows, notes)
                write_text(args.output, text, {".csv"})
            elif args.output.lower().endswith(".md"):
                text = _to_markdown(title, headers, rows, notes)
                write_text(args.output, text, {".md"})
            else:
                raise InputError("Output must end in .md or .csv")
        else:
            print(_to_markdown(title, headers, rows, notes), end="")
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
