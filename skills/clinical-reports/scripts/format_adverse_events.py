#!/usr/bin/env python3
"""Format bounded aggregate adverse-event counts into a review-only Markdown table."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

from _common import (  # noqa: E402
    MAX_CSV_BYTES,
    MAX_CSV_ROWS,
    ValidationError,
    load_json_object,
    local_input_path,
    local_output_path,
    require_bool,
    require_data_class,
    require_exact_keys,
    require_string,
)

TOOL = "format_adverse_events"
REQUIRED_COLUMNS = (
    "analysis_set",
    "treatment_group",
    "meddra_version",
    "system_organ_class",
    "preferred_term",
    "subjects_affected",
    "event_count",
    "denominator",
)
FORBIDDEN_HEADER_FRAGMENTS = {
    "patient",
    "subject_id",
    "participant",
    "case_id",
    "initial",
    "name",
    "email",
    "phone",
    "address",
    "narrative",
    "verbatim",
    "onset",
    "date",
    "mrn",
}
VERSION_RE = re.compile(r"^\d{1,2}\.\d$")
METADATA_FIELDS = {
    "schema_version",
    "artifact_kind",
    "draft_status",
    "safety_notice",
    "data_classification",
    "authorized_purpose",
    "authorization_verified",
    "local_only_handling_confirmed",
    "analysis_metadata",
    "input_csv",
    "required_columns",
    "prohibited_content",
    "provenance_manifest",
    "review",
}
ANALYSIS_METADATA_FIELDS = {
    "protocol_reference",
    "sap_reference",
    "data_cut_reference",
    "analysis_set",
    "counting_rule",
    "threshold_rule",
    "meddra_version",
    "meddra_language",
    "coding_source_reference",
}


@dataclass(frozen=True)
class AggregateRow:
    analysis_set: str
    treatment_group: str
    meddra_version: str
    system_organ_class: str
    preferred_term: str
    subjects_affected: int
    event_count: int
    denominator: int


def validate_aggregate_metadata(
    data: dict[str, object],
    *,
    input_name: str,
) -> dict[str, object]:
    """Require an authorized aggregate-only sidecar manifest."""
    require_exact_keys(data, METADATA_FIELDS, "metadata")
    if data.get("schema_version") != "2.0":
        raise ValidationError("metadata schema_version must be 2.0")
    if data.get("artifact_kind") != "clinical_trial_safety_aggregate_draft":
        raise ValidationError(
            "metadata artifact_kind must be clinical_trial_safety_aggregate_draft"
        )
    if (
        data.get("draft_status")
        != "BLOCKED_INCOMPLETE_NOT_AN_INDIVIDUAL_CASE_SAFETY_REPORT"
    ):
        raise ValidationError("metadata must preserve the blocked non-ICSR status")
    require_string(data.get("safety_notice"), "metadata.safety_notice", max_length=1000)
    if require_data_class(data.get("data_classification")) != "aggregate":
        raise ValidationError("AE formatter accepts aggregate data only")
    require_string(data.get("authorized_purpose"), "metadata.authorized_purpose")
    if not require_bool(
        data.get("authorization_verified"),
        "metadata.authorization_verified",
    ):
        raise ValidationError("metadata.authorization_verified must be true")
    if not require_bool(
        data.get("local_only_handling_confirmed"),
        "metadata.local_only_handling_confirmed",
    ):
        raise ValidationError("metadata.local_only_handling_confirmed must be true")
    require_string(data.get("provenance_manifest"), "metadata.provenance_manifest")
    if data.get("input_csv") != input_name:
        raise ValidationError("metadata.input_csv must equal the aggregate CSV filename")
    if data.get("required_columns") != list(REQUIRED_COLUMNS):
        raise ValidationError("metadata.required_columns does not match the formatter schema")
    prohibited = data.get("prohibited_content")
    if not isinstance(prohibited, list) or not prohibited:
        raise ValidationError("metadata.prohibited_content must be non-empty")

    analysis = require_exact_keys(
        data.get("analysis_metadata"),
        ANALYSIS_METADATA_FIELDS,
        "metadata.analysis_metadata",
    )
    for field in ANALYSIS_METADATA_FIELDS:
        require_string(
            analysis.get(field),
            f"metadata.analysis_metadata.{field}",
            max_length=500,
        )
    if not VERSION_RE.fullmatch(str(analysis["meddra_version"])):
        raise ValidationError("metadata MedDRA version must look like 29.0")

    review = require_exact_keys(
        data.get("review"),
        {
            "safety_coding_review",
            "statistical_review",
            "privacy_review",
            "regulatory_review",
            "submission_authorized",
        },
        "metadata.review",
    )
    if review.get("submission_authorized") is not False:
        raise ValidationError("metadata.review.submission_authorized must remain false")
    return data


def load_aggregate_metadata(
    raw_path: str,
    *,
    input_name: str,
) -> dict[str, object]:
    """Load a bounded aggregate metadata sidecar."""
    _, data = load_json_object(raw_path)
    return validate_aggregate_metadata(data, input_name=input_name)


def _label(value: str | None, field: str) -> str:
    if value is None:
        raise ValidationError(f"{field} is required")
    text = value.strip()
    if (
        not 1 <= len(text) <= 200
        or not text[0].isalnum()
        or any(char in "|`<>\r\n" or ord(char) < 32 for char in text)
    ):
        raise ValidationError(
            f"{field} must be a bounded label without markup or line breaks"
        )
    return text


def _count(value: str | None, field: str) -> int:
    if value is None or not re.fullmatch(r"\d{1,9}", value.strip()):
        raise ValidationError(f"{field} must be a non-negative integer")
    return int(value)


def load_aggregate_csv(raw_path: str) -> list[AggregateRow]:
    """Load and validate aggregate-only AE rows."""
    path = local_input_path(
        raw_path,
        suffixes={".csv"},
        max_bytes=MAX_CSV_BYTES,
    )
    try:
        path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("CSV input must be UTF-8") from exc
    handle = path.open("r", encoding="utf-8-sig", newline="")

    rows: list[AggregateRow] = []
    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValidationError("CSV header is required")
        normalized_headers = [header.strip() for header in reader.fieldnames]
        if len(normalized_headers) != len(set(normalized_headers)):
            raise ValidationError("duplicate CSV columns are not allowed")
        if normalized_headers != reader.fieldnames:
            raise ValidationError("CSV column names must not contain surrounding whitespace")
        lowered = {header.lower() for header in normalized_headers}
        for header in lowered:
            if any(fragment in header for fragment in FORBIDDEN_HEADER_FRAGMENTS):
                raise ValidationError(f"row-level or sensitive column is prohibited: {header}")
        if set(normalized_headers) != set(REQUIRED_COLUMNS):
            raise ValidationError(
                f"CSV columns must be exactly: {list(REQUIRED_COLUMNS)}"
            )

        for line_number, raw in enumerate(reader, start=2):
            if len(rows) >= MAX_CSV_ROWS:
                raise ValidationError(f"CSV exceeds {MAX_CSV_ROWS} data rows")
            if None in raw:
                raise ValidationError(f"row {line_number} contains extra columns")
            row = AggregateRow(
                analysis_set=_label(raw.get("analysis_set"), f"row {line_number} analysis_set"),
                treatment_group=_label(
                    raw.get("treatment_group"),
                    f"row {line_number} treatment_group",
                ),
                meddra_version=_label(
                    raw.get("meddra_version"),
                    f"row {line_number} meddra_version",
                ),
                system_organ_class=_label(
                    raw.get("system_organ_class"),
                    f"row {line_number} system_organ_class",
                ),
                preferred_term=_label(
                    raw.get("preferred_term"),
                    f"row {line_number} preferred_term",
                ),
                subjects_affected=_count(
                    raw.get("subjects_affected"),
                    f"row {line_number} subjects_affected",
                ),
                event_count=_count(
                    raw.get("event_count"),
                    f"row {line_number} event_count",
                ),
                denominator=_count(
                    raw.get("denominator"),
                    f"row {line_number} denominator",
                ),
            )
            if not VERSION_RE.fullmatch(row.meddra_version):
                raise ValidationError(
                    f"row {line_number} MedDRA version must look like 29.0"
                )
            if row.denominator == 0:
                raise ValidationError(f"row {line_number} denominator must be greater than zero")
            if row.subjects_affected > row.denominator:
                raise ValidationError(
                    f"row {line_number} subjects_affected exceeds denominator"
                )
            if row.event_count < row.subjects_affected:
                raise ValidationError(
                    f"row {line_number} event_count is less than subjects_affected"
                )
            rows.append(row)

    if not rows:
        raise ValidationError("CSV must contain at least one aggregate data row")

    group_metadata: dict[tuple[str, str], tuple[int, str]] = {}
    row_keys: set[tuple[str, str, str, str]] = set()
    for row in rows:
        group = (row.analysis_set, row.treatment_group)
        metadata = (row.denominator, row.meddra_version)
        if group in group_metadata and group_metadata[group] != metadata:
            raise ValidationError(
                f"inconsistent denominator or MedDRA version for group {group}"
            )
        group_metadata[group] = metadata
        row_key = (
            row.analysis_set,
            row.treatment_group,
            row.system_organ_class,
            row.preferred_term,
        )
        if row_key in row_keys:
            raise ValidationError(f"duplicate aggregate row: {row_key}")
        row_keys.add(row_key)
    return rows


def render_markdown(
    rows: list[AggregateRow],
    *,
    metadata: dict[str, object],
    expected_meddra_version: str | None = None,
) -> str:
    """Render rows without inferring missing cells or statistical comparisons."""
    versions = sorted({row.meddra_version for row in rows})
    if len(versions) != 1:
        raise ValidationError("one table may contain exactly one MedDRA version")
    analysis_metadata = metadata["analysis_metadata"]
    if not isinstance(analysis_metadata, dict):
        raise ValidationError("metadata.analysis_metadata must be an object")
    metadata_version = str(analysis_metadata["meddra_version"])
    if versions != [metadata_version]:
        raise ValidationError(
            "CSV MedDRA version does not match metadata.analysis_metadata.meddra_version"
        )
    if expected_meddra_version is not None:
        if not VERSION_RE.fullmatch(expected_meddra_version):
            raise ValidationError("--expected-meddra-version must look like 29.0")
        if versions != [expected_meddra_version]:
            raise ValidationError(
                f"input MedDRA versions {versions} do not match expected "
                f"{expected_meddra_version}"
            )

    analysis_sets = sorted({row.analysis_set for row in rows})
    if len(analysis_sets) != 1:
        raise ValidationError(
            "one output table may contain exactly one analysis_set"
        )
    if analysis_sets[0] != analysis_metadata["analysis_set"]:
        raise ValidationError(
            "CSV analysis_set does not match metadata.analysis_metadata.analysis_set"
        )
    groups = sorted({row.treatment_group for row in rows})
    denominators = {
        group: next(row.denominator for row in rows if row.treatment_group == group)
        for group in groups
    }
    lookup = {
        (row.system_organ_class, row.preferred_term, row.treatment_group): row
        for row in rows
    }
    terms = sorted({(row.system_organ_class, row.preferred_term) for row in rows})

    headers = ["System organ class", "Preferred term"]
    for group in groups:
        headers.extend(
            [
                f"{group}: subjects n/N (%)",
                f"{group}: events",
            ]
        )
    lines = [
        "# Draft aggregate adverse-event table",
        "",
        "> DRAFT — aggregate display only. Not an ICSR, reportability decision, "
        "clinical interpretation, filing, or submission. Qualified safety and "
        "statistical review is required.",
        "",
        f"- Analysis set: {analysis_sets[0]}",
        f"- MedDRA version(s), as supplied and not terminology-validated: {', '.join(versions)}",
        f"- MedDRA language, as supplied: {analysis_metadata['meddra_language']}",
        f"- Counting rule, as supplied: {analysis_metadata['counting_rule']}",
        f"- Threshold rule, as supplied: {analysis_metadata['threshold_rule']}",
        "- Missing group/term cells are shown as an em dash and are not assumed to be zero.",
        "- Subjects and events are distinct; event counts may exceed subject counts.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for soc, term in terms:
        cells = [soc, term]
        for group in groups:
            row = lookup.get((soc, term, group))
            if row is None:
                cells.extend(["—", "—"])
                continue
            percent = row.subjects_affected / row.denominator * 100
            cells.extend(
                [
                    f"{row.subjects_affected}/{row.denominator} ({percent:.1f}%)",
                    str(row.event_count),
                ]
            )
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            "Denominators by treatment group: "
            + "; ".join(f"{group} N={denominators[group]}" for group in groups)
            + ".",
            "",
            "No MedDRA semantic validation, deduplication, inference, causal assessment, "
            "or between-group testing was performed.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Format aggregate-only AE CSV rows as review-only Markdown. "
            "Rejects row-level identifiers and performs no safety assessment."
        )
    )
    parser.add_argument("input_file", help="Local aggregate CSV")
    parser.add_argument(
        "--metadata",
        required=True,
        help="Authorized aggregate safety metadata sidecar (.json)",
    )
    parser.add_argument("-o", "--output", help="Optional local Markdown output")
    parser.add_argument("--expected-meddra-version")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = load_aggregate_csv(args.input_file)
        input_name = Path(args.input_file).name
        metadata = load_aggregate_metadata(
            args.metadata,
            input_name=input_name,
        )
        rendered = render_markdown(
            rows,
            metadata=metadata,
            expected_meddra_version=args.expected_meddra_version,
        )
        if args.output:
            output = local_output_path(
                args.output,
                suffixes={".md"},
                overwrite=args.overwrite,
            )
            output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, ValidationError, csv.Error) as exc:
        print(f"{TOOL}: BLOCKED_INVALID_INPUT: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
